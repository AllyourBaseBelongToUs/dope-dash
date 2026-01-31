"""WebSocket server for real-time event broadcasting.

This module provides a FastAPI application with WebSocket support for
broadcasting events to connected dashboard clients.
"""
import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.event import Event, EventCreate
from db.connection import db_manager, get_db_session


logger = logging.getLogger(__name__)

# WebSocket message types
MSG_TYPE_EVENT = "event"
MSG_TYPE_PING = "ping"
MSG_TYPE_PONG = "pong"
MSG_TYPE_ERROR = "error"
MSG_TYPE_INFO = "info"


class ConnectionManager:
    """Manages active WebSocket connections.

    Features:
    - Track all connected clients
    - Broadcast messages to all clients
    - Send messages to specific clients
    - Handle connection/disconnection gracefully
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: dict[uuid.UUID, WebSocket] = {}
        self._connection_tasks: dict[uuid.UUID, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, client_id: uuid.UUID) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
            client_id: Unique identifier for the client.
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await self.send_personal(
            {
                "type": MSG_TYPE_INFO,
                "message": "Connected to Dope Dash WebSocket server",
                "client_id": str(client_id),
                "timestamp": datetime.utcnow().isoformat(),
            },
            client_id,
        )

        # Start ping/pong task for this connection
        self._connection_tasks[client_id] = asyncio.create_task(
            self._ping_loop(client_id)
        )

    async def disconnect(self, client_id: uuid.UUID) -> None:
        """Remove a WebSocket connection.

        Args:
            client_id: Unique identifier for the client to disconnect.
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

        # Cancel ping task
        if client_id in self._connection_tasks:
            self._connection_tasks[client_id].cancel()
            try:
                await self._connection_tasks[client_id]
            except asyncio.CancelledError:
                pass
            del self._connection_tasks[client_id]

    async def send_personal(self, message: dict[str, Any], client_id: uuid.UUID) -> bool:
        """Send a message to a specific client.

        Args:
            message: The message to send (will be JSON serialized).
            client_id: Unique identifier for the target client.

        Returns:
            True if message was sent successfully, False otherwise.
        """
        websocket = self.active_connections.get(client_id)
        if websocket is None:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast (will be JSON serialized).
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        disconnected_clients: list[uuid.UUID] = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    async def _ping_loop(self, client_id: uuid.UUID, interval: float = 30.0) -> None:
        """Send periodic ping messages to keep connection alive.

        Args:
            client_id: Unique identifier for the client.
            interval: Seconds between pings (default: 30).
        """
        try:
            while True:
                await asyncio.sleep(interval)
                success = await self.send_personal(
                    {
                        "type": MSG_TYPE_PING,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    client_id,
                )
                if not success:
                    break
        except asyncio.CancelledError:
            # Task was cancelled during disconnect
            raise

    def get_connection_count(self) -> int:
        """Get the number of active connections.

        Returns:
            Number of currently connected clients.
        """
        return len(self.active_connections)

    def get_connection_ids(self) -> list[uuid.UUID]:
        """Get list of all connected client IDs.

        Returns:
            List of client UUIDs.
        """
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()


class EventIngestRequest(BaseModel):
    """Request schema for event ingestion."""

    session_id: uuid.UUID
    event_type: str
    data: dict = {}


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan.

    Initializes database on startup and closes connections on shutdown.
    """
    # Startup
    logger.info("Starting WebSocket server...")
    db_manager.init_db()
    logger.info("Database connection pool initialized")

    yield

    # Shutdown
    logger.info("Shutting down WebSocket server...")
    await db_manager.close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Dope Dash WebSocket Server",
    description="Real-time event broadcasting for Dope Dash dashboard",
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
    """Root endpoint with server information.

    Returns:
        Dictionary containing server status and connection info.
    """
    return {
        "name": "Dope Dash WebSocket Server",
        "version": "0.1.0",
        "status": "running",
        "websocket_url": "ws://localhost:8001/ws",
        "connections": manager.get_connection_count(),
        "endpoints": {
            "websocket": "/ws",
            "ingest": "/api/events",
            "health": "/health",
        },
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        Dictionary containing health status.
    """
    db_healthy = await db_manager.health_check()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "connections": manager.get_connection_count(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time event streaming.

    Clients connect to this endpoint to receive real-time event broadcasts.
    The server sends periodic ping messages and handles pong responses.

    Connection flow:
        1. Client connects via WebSocket
        2. Server assigns a client_id and sends welcome message
        3. Server sends periodic ping messages (every 30s)
        4. Client can respond with pong messages
        5. Server broadcasts events to all connected clients
        6. Client disconnects gracefully or connection is lost

    Message types:
        - event: Real-time event data
        - ping: Server heartbeat (client should respond with pong)
        - pong: Client heartbeat response
        - info: Informational messages
        - error: Error messages
    """
    # Generate unique client ID
    client_id = uuid.uuid4()

    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                # Handle pong response from client
                if msg_type == MSG_TYPE_PONG:
                    logger.debug(f"Received pong from client {client_id}")

                # Echo back other message types for now
                # This can be extended for bidirectional communication
                else:
                    logger.debug(f"Received message from client {client_id}: {msg_type}")

            except json.JSONDecodeError:
                await manager.send_personal(
                    {
                        "type": MSG_TYPE_ERROR,
                        "message": "Invalid JSON format",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    client_id,
                )

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected (WebSocketDisconnect)")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error with client {client_id}: {e}")
    finally:
        await manager.disconnect(client_id)


@app.post("/api/events")
async def ingest_event(
    event: EventIngestRequest,
    x_session_token: str | None = Header(None, alias="X-Session-Token")
) -> dict[str, Any]:
    """Ingest an event and broadcast it to all connected WebSocket clients.

    This endpoint receives events from agents, stores them in PostgreSQL,
    and broadcasts them in real-time to all connected dashboard clients.

    Authentication: Requires X-Session-Token header matching the session ID.

    Args:
        event: The event data to ingest.
        x_session_token: Session token for authentication.

    Returns:
        Dictionary containing the created event with generated ID and timestamp.

    Raises:
        401: If authentication fails.
        500: If event creation fails.
    """
    # Verify session exists and token is valid
    try:
        async with get_db_session() as session:
            from app.models.session import Session as SessionModel

            result = await session.execute(
                select(SessionModel).where(
                    SessionModel.id == event.session_id,
                    SessionModel.deleted_at.is_(None)
                )
            )
            db_session = result.scalar_one_or_none()

            if not db_session:
                raise HTTPException(
                    status_code=401,
                    detail=f"Session {event.session_id} not found or deleted"
                )

            # For MVP: token must match session ID
            if x_session_token != str(event.session_id):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid session token"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

    try:
        async with get_db_session() as session:
            # Create Event model instance
            db_event = Event(
                session_id=event.session_id,
                event_type=event.event_type,
                data=event.data,
            )
            session.add(db_event)
            await session.flush()
            await session.refresh(db_event)

            # Prepare event for broadcast
            event_message = {
                "type": MSG_TYPE_EVENT,
                "id": str(db_event.id),
                "session_id": str(db_event.session_id),
                "event_type": db_event.event_type,
                "data": db_event.data,
                "created_at": db_event.created_at.isoformat() if db_event.created_at else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Broadcast to all connected clients
            await manager.broadcast(event_message)
            logger.info(
                f"Event {db_event.id} (type={db_event.event_type}) "
                f"ingested and broadcasted to {manager.get_connection_count()} clients"
            )

            return {
                "id": str(db_event.id),
                "session_id": str(db_event.session_id),
                "event_type": db_event.event_type,
                "data": db_event.data,
                "created_at": db_event.created_at.isoformat() if db_event.created_at else None,
                "broadcasted_to": manager.get_connection_count(),
            }

    except ValidationError as e:
        logger.error(f"Validation error for event ingestion: {e}")
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error ingesting event: {e}")
        raise


@app.get("/api/events")
async def get_events(
    session_id: uuid.UUID | None = None,
    limit: int = 100,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Get events for polling (WebSocket fallback).

    This endpoint allows clients to poll for events when WebSocket is unavailable.
    Supports filtering by session_id and event_type.

    Args:
        session_id: Optional session UUID to filter events.
        limit: Maximum number of events to return (default: 100).
        event_type: Optional event type to filter by.

    Returns:
        List of event dictionaries matching the filter criteria.
    """
    try:
        async with get_db_session() as session:
            query = select(Event).order_by(Event.created_at.desc()).limit(limit)

            if session_id:
                query = query.where(Event.session_id == session_id)

            if event_type:
                query = query.where(Event.event_type == event_type)

            result = await session.execute(query)
            events = result.scalars().all()

            return [
                {
                    "type": MSG_TYPE_EVENT,
                    "id": str(event.id),
                    "session_id": str(event.session_id),
                    "event_type": event.event_type,
                    "data": event.data,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                for event in events
            ]

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error fetching events: {e}")
        return []


@app.get("/api/connections")
async def get_connections() -> dict[str, Any]:
    """Get information about active WebSocket connections.

    Returns:
        Dictionary containing connection statistics.
    """
    return {
        "active_connections": manager.get_connection_count(),
        "client_ids": [str(cid) for cid in manager.get_connection_ids()],
    }


def main() -> None:
    """Run the WebSocket server.

    Binds to 0.0.0.0:8001 for external access (e.g., from Windows host).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        "websocket:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
