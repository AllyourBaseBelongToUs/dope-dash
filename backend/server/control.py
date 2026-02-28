"""Control API server for sending commands to agents.

This module provides a FastAPI application for sending control commands
(pause, resume, skip, stop) to active agent sessions.

Commands are queued per session and can be delivered via:
- Unix socket (for agents listening on socket paths)
- Stored for agents to poll (offline/polling mode)

Authentication is performed via X-Session-Token header.
"""
import asyncio
import json
import logging
import os
import platform
import socket
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

import sys
from pathlib import Path as PathLib

# Add parent directory to path for imports
sys.path.insert(0, str(PathLib(__file__).parent.parent))

from app.core.config import settings
from app.db import get_db_session
from sqlalchemy import select

# Service configuration
SERVICE_NAME = "control_api"
SERVICE_PORT = 8010


logger = logging.getLogger(__name__)


# Command types
class CommandType(str, Enum):
    """Types of control commands that can be sent to agents."""

    PAUSE = "pause"
    RESUME = "resume"
    SKIP = "skip"
    STOP = "stop"


# Command status tracking
class CommandStatus(str, Enum):
    """Status of a command in the queue."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Request/Response schemas
class CommandRequest(BaseModel):
    """Request schema for sending a command to an agent."""

    command: CommandType = Field(
        ...,
        description="The command type to send (pause, resume, skip, stop)",
    )
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for command execution in seconds (max 300)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata to attach to the command",
    )


class CommandResponse(BaseModel):
    """Response schema for command submission."""

    command_id: str = Field(..., description="Unique identifier for the command")
    session_id: str = Field(..., description="The target session ID")
    command: CommandType = Field(..., description="The command type")
    status: CommandStatus = Field(..., description="Initial command status")
    created_at: str = Field(..., description="ISO timestamp of command creation")
    timeout_at: str = Field(..., description="ISO timestamp when command will timeout")


class SessionStatusResponse(BaseModel):
    """Response schema for session status queries."""

    session_id: str = Field(..., description="The session ID")
    is_online: bool = Field(..., description="Whether the agent is online")
    pending_commands: int = Field(..., description="Number of pending commands")
    last_command: CommandResponse | None = Field(None, description="Last command sent")


class AcknowledgmentRequest(BaseModel):
    """Request schema for command acknowledgment from agents."""

    command_id: str = Field(..., description="The command ID being acknowledged")
    result: str | None = Field(None, description="Optional result message")
    error: str | None = Field(None, description="Error message if command failed")


# In-memory command queue storage
class CommandQueue:
    """Manages command queues for agent sessions.

    Features:
    - Per-session command queues
    - Command status tracking
    - Timeout handling
    - Persistent storage for offline agents
    """

    def __init__(self, socket_dir: str | None = None) -> None:
        """Initialize the command queue.

        Args:
            socket_dir: Directory for Unix socket files. If None, uses OS-appropriate temp directory.
        """
        self._queues: dict[uuid.UUID, list[dict[str, Any]]] = {}
        self._commands: dict[str, dict[str, Any]] = {}

        # Use OS-appropriate temp directory if not specified
        if socket_dir is None:
            if platform.system() == "Windows":
                # Windows: use temp directory
                socket_dir = os.path.join(tempfile.gettempdir(), "dopedash-control")
            else:
                # Unix-like: use /tmp
                socket_dir = "/tmp/dopedash-control"

        self._socket_dir = Path(socket_dir)
        self._socket_dir.mkdir(parents=True, exist_ok=True)
        self._online_sessions: set[uuid.UUID] = set()

    async def enqueue(
        self,
        session_id: uuid.UUID,
        command: CommandType,
        timeout_seconds: int,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Enqueue a command for a session.

        Args:
            session_id: The target session ID.
            command: The command type.
            timeout_seconds: Command timeout in seconds.
            metadata: Optional command metadata.

        Returns:
            The created command record.
        """
        command_id = str(uuid.uuid4())
        now = datetime.utcnow()

        command_record = {
            "id": command_id,
            "session_id": str(session_id),
            "command": command.value,
            "status": CommandStatus.PENDING.value,
            "created_at": now.isoformat(),
            "timeout_at": (now + __import__("datetime").timedelta(seconds=timeout_seconds)).isoformat(),
            "timeout_seconds": timeout_seconds,
            "metadata": metadata,
            "result": None,
            "error": None,
        }

        # Store command
        self._commands[command_id] = command_record

        # Add to session queue
        if session_id not in self._queues:
            self._queues[session_id] = []
        self._queues[session_id].append(command_record)

        # Persist to file for offline agents
        await self._persist_command(session_id, command_record)

        return command_record

    async def get_pending(self, session_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get all pending commands for a session.

        Args:
            session_id: The session ID.

        Returns:
            List of pending command records.
        """
        return self._queues.get(session_id, [])

    async def acknowledge(
        self,
        command_id: str,
        result: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        """Mark a command as acknowledged/completed.

        Args:
            command_id: The command ID.
            result: Optional result message.
            error: Optional error message.

        Returns:
            The updated command record, or None if not found.
        """
        command = self._commands.get(command_id)
        if not command:
            return None

        # Update status
        if error:
            command["status"] = CommandStatus.FAILED.value
            command["error"] = error
        else:
            command["status"] = CommandStatus.COMPLETED.value
            command["result"] = result

        command["acknowledged_at"] = datetime.utcnow().isoformat()

        # Remove from queue
        session_id = uuid.UUID(command["session_id"])
        if session_id in self._queues:
            self._queues[session_id] = [
                c for c in self._queues[session_id] if c["id"] != command_id
            ]

        # Update persistent storage
        await self._update_persistent_command(session_id, command_id, command)

        return command

    async def get_command(self, command_id: str) -> dict[str, Any] | None:
        """Get a command by ID.

        Args:
            command_id: The command ID.

        Returns:
            The command record, or None if not found.
        """
        return self._commands.get(command_id)

    def set_online(self, session_id: uuid.UUID, online: bool = True) -> None:
        """Mark a session as online or offline.

        Args:
            session_id: The session ID.
            online: Whether the session is online.
        """
        if online:
            self._online_sessions.add(session_id)
        else:
            self._online_sessions.discard(session_id)

    def is_online(self, session_id: uuid.UUID) -> bool:
        """Check if a session is online.

        Args:
            session_id: The session ID.

        Returns:
            True if the session is online.
        """
        return session_id in self._online_sessions

    def get_queue_file_path(self, session_id: uuid.UUID) -> Path:
        """Get the file path for a session's command queue.

        Args:
            session_id: The session ID.

        Returns:
            Path to the queue file.
        """
        return self._socket_dir / f"queue_{session_id}.json"

    async def _persist_command(self, session_id: uuid.UUID, command: dict[str, Any]) -> None:
        """Persist a command to the session's queue file.

        Args:
            session_id: The session ID.
            command: The command record.
        """
        queue_file = self.get_queue_file_path(session_id)

        try:
            # Read existing queue
            if queue_file.exists():
                with open(queue_file, "r") as f:
                    queue_data = json.load(f)
            else:
                queue_data = {"session_id": str(session_id), "commands": []}

            # Add new command
            queue_data["commands"].append(command)
            queue_data["updated_at"] = datetime.utcnow().isoformat()

            # Write back
            with open(queue_file, "w") as f:
                json.dump(queue_data, f, indent=2)

            logger.debug(f"Persisted command {command['id']} to {queue_file}")

        except Exception as e:
            logger.error(f"Error persisting command to {queue_file}: {e}")

    async def _update_persistent_command(
        self, session_id: uuid.UUID, command_id: str, command: dict[str, Any]
    ) -> None:
        """Update a command in the persistent storage.

        Args:
            session_id: The session ID.
            command_id: The command ID.
            command: The updated command record.
        """
        queue_file = self.get_queue_file_path(session_id)

        try:
            if not queue_file.exists():
                return

            with open(queue_file, "r") as f:
                queue_data = json.load(f)

            # Update the command
            for i, cmd in enumerate(queue_data.get("commands", [])):
                if cmd["id"] == command_id:
                    queue_data["commands"][i] = command
                    break

            queue_data["updated_at"] = datetime.utcnow().isoformat()

            # Write back
            with open(queue_file, "w") as f:
                json.dump(queue_data, f, indent=2)

            logger.debug(f"Updated command {command_id} in {queue_file}")

        except Exception as e:
            logger.error(f"Error updating command in {queue_file}: {e}")

    def get_session_stats(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Get statistics for a session.

        Args:
            session_id: The session ID.

        Returns:
            Dictionary with session statistics.
        """
        queue = self._queues.get(session_id, [])
        last_command = queue[-1] if queue else None

        return {
            "session_id": str(session_id),
            "is_online": session_id in self._online_sessions,
            "pending_commands": len(queue),
            "last_command": last_command,
        }


# Global command queue instance
command_queue = CommandQueue()


# Authentication helper
async def verify_session_token(
    session_id: uuid.UUID,
    x_session_token: str | None = None,
) -> bool:
    """Verify session token authentication.

    Validates that:
    1. The session exists in the database
    2. The session is not soft-deleted
    3. A valid token is provided (matches session ID for MVP)

    In production, this should validate against a proper session store
    with cryptographic tokens.

    Args:
        session_id: The session ID.
        x_session_token: The X-Session-Token header value.

    Returns:
        True if authenticated, False otherwise.
    """
    # For MVP: token must match session ID format and session must exist
    if not x_session_token or len(x_session_token) == 0:
        return False

    try:
        async with get_db_session() as db_session:
            from app.models.session import Session as SessionModel

            # Query session from database
            result = await db_session.execute(
                select(SessionModel).where(
                    SessionModel.id == session_id,
                    SessionModel.deleted_at.is_(None)  # Not soft-deleted
                )
            )
            session = result.scalar_one_or_none()

            # Session must exist and not be deleted
            if not session:
                logger.warning(f"Authentication failed: session {session_id} not found or deleted")
                return False

            # For MVP: token must match session ID (simple validation)
            # In production, use proper cryptographic tokens
            if x_session_token != str(session_id):
                logger.warning(f"Authentication failed: invalid token for session {session_id}")
                return False

            return True

    except Exception as e:
        logger.error(f"Error verifying session token: {e}")
        return False


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan.

    Initializes the command queue system on startup.
    """
    logger.info("Starting Control API server...")
    logger.info(f"Command queue directory: {command_queue._socket_dir}")

    # Load existing queues from disk
    for queue_file in command_queue._socket_dir.glob("queue_*.json"):
        try:
            with open(queue_file, "r") as f:
                queue_data = json.load(f)
                session_id = uuid.UUID(queue_data["session_id"])
                commands = queue_data.get("commands", [])

                # Restore pending commands
                pending = [c for c in commands if c["status"] == CommandStatus.PENDING.value]
                if pending:
                    command_queue._queues[session_id] = pending
                    for cmd in pending:
                        command_queue._commands[cmd["id"]] = cmd
                    logger.info(f"Restored {len(pending)} pending commands for session {session_id}")

        except Exception as e:
            logger.error(f"Error loading queue from {queue_file}: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Control API server...")


# Create FastAPI application
app = FastAPI(
    title="Dope Dash Control API",
    description="REST API for sending control commands to agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with API information.

    Returns:
        Dictionary containing API information and available endpoints.
    """
    return {
        "name": "Dope Dash Control API",
        "version": "0.1.0",
        "status": "running",
        "port": 8010,
        "endpoints": {
            "send_command": "POST /api/control/{session_id}/command",
            "get_status": "GET /api/control/{session_id}/status",
            "poll_commands": "GET /api/control/{session_id}/poll",
            "acknowledge": "POST /api/control/{session_id}/acknowledge",
            "health": "/health",
        },
        "commands": [c.value for c in CommandType],
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        Dictionary containing health status.
    """
    return {
        "status": "healthy",
        "active_sessions": len(command_queue._queues),
        "total_commands": len(command_queue._commands),
        "online_sessions": len(command_queue._online_sessions),
    }


@app.post(
    "/api/control/{session_id}/command",
    response_model=CommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_command(
    session_id: uuid.UUID,
    command_request: CommandRequest,
    x_session_token: str | None = Header(None, alias="X-Session-Token"),
) -> CommandResponse:
    """Send a control command to an agent session.

    This endpoint queues a command for the specified session. The command
    will be delivered when the agent polls or connects via WebSocket.

    Args:
        session_id: The target session UUID.
        command_request: The command details.
        x_session_token: Session authentication token.

    Returns:
        CommandResponse with the command ID and status.

    Raises:
        401: If authentication fails.
        404: If session is not found.
    """
    # Authenticate
    if not await verify_session_token(session_id, x_session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token",
        )

    # Enqueue command
    command_record = await command_queue.enqueue(
        session_id=session_id,
        command=command_request.command,
        timeout_seconds=command_request.timeout_seconds,
        metadata=command_request.metadata,
    )

    logger.info(
        f"Command {command_record['id']} ({command_request.command.value}) "
        f"queued for session {session_id}"
    )

    return CommandResponse(**command_record)


@app.get("/api/control/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: uuid.UUID,
    x_session_token: str | None = Header(None, alias="X-Session-Token"),
) -> SessionStatusResponse:
    """Get the status of a session's command queue.

    Args:
        session_id: The session UUID.
        x_session_token: Session authentication token.

    Returns:
        SessionStatusResponse with queue information.

    Raises:
        401: If authentication fails.
    """
    # Authenticate
    if not await verify_session_token(session_id, x_session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token",
        )

    stats = command_queue.get_session_stats(session_id)

    return SessionStatusResponse(
        session_id=str(session_id),
        is_online=stats["is_online"],
        pending_commands=stats["pending_commands"],
        last_command=CommandResponse(**stats["last_command"]) if stats["last_command"] else None,
    )


@app.get("/api/control/{session_id}/poll")
async def poll_commands(
    session_id: uuid.UUID,
    x_session_token: str | None = Header(None, alias="X-Session-Token"),
) -> dict[str, Any]:
    """Poll for pending commands (for agent-side polling).

    This endpoint is called by agents to check for new commands.
    Returns all pending commands for the session and marks the session as online.

    Args:
        session_id: The session UUID.
        x_session_token: Session authentication token.

    Returns:
        Dictionary with pending commands and session status.

    Raises:
        401: If authentication fails.
    """
    # Authenticate
    if not await verify_session_token(session_id, x_session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token",
        )

    # Mark session as online
    command_queue.set_online(session_id, online=True)

    # Get pending commands
    pending = await command_queue.get_pending(session_id)

    # Mark commands as acknowledged
    for cmd in pending:
        await command_queue.acknowledge(cmd["id"], result="received")

    logger.debug(f"Session {session_id} polled: {len(pending)} commands")

    return {
        "session_id": str(session_id),
        "commands": pending,
        "count": len(pending),
        "polled_at": datetime.utcnow().isoformat(),
    }


@app.post("/api/control/{session_id}/acknowledge")
async def acknowledge_command(
    session_id: uuid.UUID,
    ack: AcknowledgmentRequest,
    x_session_token: str | None = Header(None, alias="X-Session-Token"),
) -> dict[str, Any]:
    """Acknowledge command completion from an agent.

    This endpoint is called by agents to report command completion status.

    Args:
        session_id: The session UUID.
        ack: Acknowledgment details.
        x_session_token: Session authentication token.

    Returns:
        Dictionary with updated command status.

    Raises:
        401: If authentication fails.
        404: If command is not found.
    """
    # Authenticate
    if not await verify_session_token(session_id, x_session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token",
        )

    # Update command status
    command = await command_queue.acknowledge(
        command_id=ack.command_id,
        result=ack.result,
        error=ack.error,
    )

    if command is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command {ack.command_id} not found",
        )

    logger.info(
        f"Command {ack.command_id} acknowledged by session {session_id}: "
        f"{command['status']}"
    )

    return {
        "command_id": ack.command_id,
        "status": command["status"],
        "result": command.get("result"),
        "error": command.get("error"),
        "acknowledged_at": command.get("acknowledged_at"),
    }


@app.websocket("/ws/control/{session_id}")
async def websocket_control(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """WebSocket endpoint for real-time command delivery.

    Agents can connect to this endpoint to receive commands in real-time
    instead of polling.

    Args:
        websocket: The WebSocket connection.
        session_id: The session ID.
    """
    await websocket.accept()

    # Mark session as online
    command_queue.set_online(session_id, online=True)
    logger.info(f"Session {session_id} connected via WebSocket for commands")

    try:
        while True:
            # Wait for messages from agent
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Handle acknowledgments
                if message.get("type") == "acknowledge":
                    ack = AcknowledgmentRequest(**message.get("data", {}))
                    command = await command_queue.acknowledge(
                        command_id=ack.command_id,
                        result=ack.result,
                        error=ack.error,
                    )

                    await websocket.send_json({
                        "type": "ack_response",
                        "data": {
                            "command_id": ack.command_id,
                            "status": command["status"] if command else "not_found",
                        },
                    })

                # Handle heartbeat
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except (json.JSONDecodeError, ValidationError) as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

            # Send any pending commands
            pending = await command_queue.get_pending(session_id)
            if pending:
                await websocket.send_json({
                    "type": "commands",
                    "data": pending,
                })

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        # Mark session as offline
        command_queue.set_online(session_id, online=False)
        logger.info(f"Session {session_id} disconnected from control WebSocket")


def check_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding.

    Args:
        host: Host address to check.
        port: Port number to check.

    Returns:
        True if port is available, False otherwise.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host, port))
            return True
    except OSError as e:
        return False


def main() -> None:
    """Run the Control API server.

    Binds to 0.0.0.0:8010 for external access.
    Port: 8010 (step-5 spacing: 8000, 8005, 8010, 8015, 8020)
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    host = "0.0.0.0"
    port = SERVICE_PORT

    # Check if port is available before starting
    if not check_port_available(host, port):
        error_msg = f"Port {port} is already in use or blocked"
        try:
            from app.utils.port_logger import log_port_error
            log_port_error(
                service_name=SERVICE_NAME,
                port=port,
                error=error_msg,
                additional_info={
                    "host": host,
                    "environment": settings.environment,
                }
            )
        except ImportError:
            pass  # Port logger not available, continue with standard error

        logger.error(f"✗ {error_msg}. Check logs/port_errors.log for details.")
        print(f"\n[ERROR] {error_msg}")
        print(f"[ERROR] Service: {SERVICE_NAME}")
        print(f"[ERROR] Port: {port}")
        print(f"[ERROR] Check what's using the port: netstat -tuln | grep {port}")
        sys.exit(1)

    try:
        uvicorn.run(
            "control:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            reload=settings.environment == "development",
        )
    except Exception as e:
        # Log any startup errors
        try:
            from app.utils.port_logger import log_port_error
            log_port_error(
                service_name=SERVICE_NAME,
                port=port,
                error=e,
                additional_info={
                    "host": host,
                    "environment": settings.environment,
                    "error_stage": "uvicorn_startup",
                }
            )
        except ImportError:
            pass
        raise


if __name__ == "__main__":
    main()
