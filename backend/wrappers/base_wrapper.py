"""Base agent wrapper class for Dope Dash event streaming.

This module provides the abstract base class that all agent wrappers
must implement, ensuring consistent behavior across different agent types.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
from pydantic import BaseModel

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.session import Session, SessionStatus, AgentType
from app.services.agent_factory import BaseAgentWrapper as BaseWrapperInterface
from db.connection import db_manager, get_db_session


logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_WEBSOCKET_URL = "http://localhost:8005"


class EventIngestRequest(BaseModel):
    """Request schema for event ingestion."""

    session_id: uuid.UUID
    event_type: str
    data: dict = {}


class BaseAgentWrapper(BaseWrapperInterface, ABC):
    """Abstract base class for agent wrappers.

    All agent wrappers must implement this interface to ensure
    consistent behavior across different agent types.

    This class provides common functionality for:
    - Session management (create, update, end)
    - Event emission to the WebSocket server
    - Heartbeat tracking
    - Agent metadata handling
    """

    def __init__(
        self,
        project_dir: Path,
        websocket_url: str = DEFAULT_WEBSOCKET_URL,
        pid: int | None = None,
        working_dir: str | None = None,
        command: str | None = None,
        tmux_session: str | None = None,
    ) -> None:
        """Initialize the base wrapper.

        Args:
            project_dir: Path to the project directory
            websocket_url: URL of the WebSocket server for event ingestion
            pid: Process ID of the agent (optional)
            working_dir: Working directory of the agent (optional)
            command: Command line used to start the agent (optional)
            tmux_session: Tmux session name (optional)
        """
        self.project_dir = project_dir.resolve()
        self.websocket_url = websocket_url.rstrip("/")
        self.project_name = self.project_dir.name

        # Agent metadata
        self._pid = pid
        self._working_dir = working_dir or str(self.project_dir)
        self._command = command
        self._tmux_session = tmux_session

        # Session management
        self._session_id: uuid.UUID | None = None
        self._running = False
        self._http_session: aiohttp.ClientSession | None = None

        logger.info(
            f"{self.agent_type.value} wrapper initialized for project: {self.project_name} "
            f"at {self.project_dir}"
        )

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the agent type for this wrapper."""
        ...

    async def start(self) -> None:
        """Start the wrapper event monitoring loop."""
        if self._running:
            logger.warning(f"{self.agent_type.value} wrapper already running")
            return

        self._running = True
        self._http_session = aiohttp.ClientSession()

        logger.info(f"Starting {self.agent_type.value} wrapper...")

        # Initialize database
        db_manager.init_db()

        try:
            # Create session
            await self._create_session()

            # Start agent-specific monitoring
            await self._monitoring_loop()

        except asyncio.CancelledError:
            logger.info(f"{self.agent_type.value} wrapper monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in {self.agent_type.value} wrapper: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the wrapper and cleanup resources."""
        if not self._running:
            return

        logger.info(f"Stopping {self.agent_type.value} wrapper...")
        self._running = False

        # End session
        if self._session_id:
            await self._end_session(SessionStatus.COMPLETED)

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        logger.info(f"{self.agent_type.value} wrapper stopped")

    @property
    def is_running(self) -> bool:
        """Check if the wrapper is running."""
        return self._running

    @abstractmethod
    async def _monitoring_loop(self) -> None:
        """Agent-specific monitoring loop.

        This method should implement the agent-specific monitoring logic,
        such as watching files, polling processes, or listening for events.
        """
        ...

    async def _create_session(self) -> None:
        """Create a new session in the database."""
        async with get_db_session() as db_session:
            db_session_obj = Session(
                agent_type=self.agent_type,
                project_name=self.project_name,
                status=SessionStatus.RUNNING,
                metadata={
                    "wrapper": self.__class__.__name__,
                    "project_dir": str(self.project_dir),
                },
                started_at=datetime.now(timezone.utc),
                # Agent runtime metadata
                pid=self._pid,
                working_dir=self._working_dir,
                command=self._command,
                tmux_session=self._tmux_session,
            )
            db_session.add(db_session_obj)
            await db_session.flush()
            await db_session.refresh(db_session_obj)

            self._session_id = db_session_obj.id

            logger.info(f"Created new {self.agent_type.value} session: {db_session_obj.id}")

            # Emit session start event
            await self._emit_event(
                "session_start",
                {
                    "project_name": self.project_name,
                    "agent_type": self.agent_type.value,
                },
            )

    async def _end_session(self, status: SessionStatus) -> None:
        """End the current session.

        Args:
            status: Final status of the session
        """
        if not self._session_id:
            return

        async with get_db_session() as db_session:
            from sqlalchemy import select

            result = await db_session.execute(
                select(Session).where(Session.id == self._session_id)
            )
            db_session_obj = result.scalar_one_or_none()

            if db_session_obj:
                db_session_obj.status = status
                db_session_obj.ended_at = datetime.now(timezone.utc)
                await db_session.commit()

        logger.info(f"{self.agent_type.value} session {self._session_id} ended with status: {status}")

    async def _emit_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Emit an event to the WebSocket server.

        Args:
            event_type: Type of event to emit
            data: Event data payload
        """
        if not self._session_id:
            logger.warning("No session info, skipping event emission")
            return

        event = EventIngestRequest(
            session_id=self._session_id,
            event_type=event_type,
            data=data,
        )

        # Send to WebSocket server
        success = await self._send_to_websocket(event)

        if not success:
            logger.debug(f"WebSocket unavailable, event {event_type} queued for polling")

    async def _send_to_websocket(self, event: EventIngestRequest) -> bool:
        """Send event to WebSocket server via HTTP POST.

        Args:
            event: Event to send

        Returns:
            True if successful, False otherwise
        """
        if not self._http_session:
            return False

        url = f"{self.websocket_url}/api/events"

        try:
            async with self._http_session.post(
                url,
                json=event.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    logger.debug(f"Event {event.event_type} sent successfully")
                    return True
                else:
                    logger.warning(f"WebSocket server returned status {response.status}")
                    return False

        except (aiohttp.ClientError, asyncio.TimeoutError):
            logger.debug(f"Failed to send event to WebSocket server")
            return False

    async def _update_heartbeat(self) -> None:
        """Update the heartbeat timestamp for the current session."""
        if not self._session_id:
            return

        async with get_db_session() as db_session:
            from sqlalchemy import select

            result = await db_session.execute(
                select(Session).where(Session.id == self._session_id)
            )
            db_session_obj = result.scalar_one_or_none()

            if db_session_obj:
                db_session_obj.last_heartbeat = datetime.now(timezone.utc)
                await db_session.commit()

    async def send_control(
        self,
        control: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Send a control command to the agent.

        This method handles control commands like pause, resume, stop, skip, retry, restart.
        It emits control events that can be picked up by the agent's monitoring loop.

        Args:
            control: Control command (pause, resume, stop, skip, retry, restart)
            metadata: Optional metadata for the control command

        Returns:
            True if control was sent successfully, False otherwise
        """
        if not self._running or not self._session_id:
            logger.warning(f"Cannot send control to {self.agent_type.value} wrapper: not running or no session")
            return False

        # Emit control event
        await self._emit_event(
            "control_command",
            {
                "control": control,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Sent {control} control to {self.agent_type.value} wrapper for {self.project_name}")
        return True
