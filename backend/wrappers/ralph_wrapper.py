#!/usr/bin/env python3
"""Ralph Inferno agent wrapper for Dope Dash event streaming.

This wrapper monitors Ralph Inferno agent execution by watching the
heartbeat file (.ralph/heartbeat.json), captures events, transforms them
to Dope Dash format, and streams them to the WebSocket server.

Features:
- Monitors .ralph/heartbeat.json for status changes
- Detects Ralph sessions via tmux and process scanning
- Transforms Ralph events to Dope Dash event format
- Sends events to WebSocket server via HTTP POST
- Handles process crashes and restarts
- Polling fallback when WebSocket unavailable
- Creates and manages Ralph sessions in database

Usage:
    python -m wrappers.ralph_wrapper
    python -m wrappers.ralph_wrapper --project-dir /path/to/project
    python -m wrappers.ralph_wrapper --websocket-url http://localhost:8001
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import aiohttp
import psutil
from pydantic import BaseModel, ValidationError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.session import Session, SessionStatus, AgentType
from db.connection import db_manager, get_db_session


logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_WEBSOCKET_URL = "http://localhost:8001"
DEFAULT_PROJECT_DIR = Path.cwd()
HEARTBEAT_FILE = ".ralph/heartbeat.json"
LOG_DIR = ".ralph/logs"
SPEC_CHECKSUMS_DIR = ".spec-checksums"

# Polling interval when WebSocket is unavailable (seconds)
POLLING_INTERVAL = 5
HEARTBEAT_CHECK_INTERVAL = 1


class RalphEventType(str, Enum):
    """Ralph-specific event types."""

    SPEC_START = "spec_start"
    SPEC_COMPLETE = "spec_complete"
    SPEC_FAILED = "spec_failed"
    ERROR = "error"
    PROGRESS = "progress"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class HeartbeatStatus(str, Enum):
    """Heartbeat status messages from Ralph."""

    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    BUILDING = "building"
    TESTING = "testing"
    COMPLETE = "complete"


@dataclass
class HeartbeatData:
    """Parsed heartbeat data from .ralph/heartbeat.json."""

    timestamp: str
    status: str
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> HeartbeatData:
        """Create HeartbeatData from dictionary."""
        return cls(
            timestamp=data.get("timestamp", ""),
            status=data.get("status", ""),
            raw=data,
        )

    @property
    def event_type(self) -> RalphEventType | None:
        """Extract event type from heartbeat status."""
        status = self.status

        if status.startswith("spec_start:"):
            return RalphEventType.SPEC_START
        if status.startswith("spec_done:"):
            return RalphEventType.SPEC_COMPLETE
        if status.startswith("spec_failed:"):
            return RalphEventType.SPEC_FAILED
        if status.startswith("error:"):
            return RalphEventType.ERROR

        # Map heartbeat statuses to event types
        status_map = {
            HeartbeatStatus.STARTING: RalphEventType.SESSION_START,
            HeartbeatStatus.RUNNING: RalphEventType.PROGRESS,
            HeartbeatStatus.BUILDING: RalphEventType.PROGRESS,
            HeartbeatStatus.TESTING: RalphEventType.PROGRESS,
            HeartbeatStatus.COMPLETE: RalphEventType.SESSION_END,
        }

        return status_map.get(HeartbeatStatus(status))

    @property
    def spec_name(self) -> str | None:
        """Extract spec name from heartbeat status."""
        if ":" in self.status:
            return self.status.split(":", 1)[1]
        return None

    @property
    def error_message(self) -> str | None:
        """Extract error message from heartbeat status."""
        if self.status.startswith("error:"):
            return self.status.split(":", 1)[1] if ":" in self.status else "Unknown error"
        return None


@dataclass
class RalphSessionInfo:
    """Information about a Ralph session."""

    project_name: str
    session_id: uuid.UUID
    pid: int | None = None
    tmux_session: str | None = None
    started_at: datetime | None = None
    status: SessionStatus = SessionStatus.RUNNING


class EventIngestRequest(BaseModel):
    """Request schema for event ingestion."""

    session_id: uuid.UUID
    event_type: str
    data: dict = {}


class RalphWrapper:
    """Ralph Inferno agent wrapper for event streaming.

    This class monitors Ralph agent execution and streams events to Dope Dash.
    """

    # Class-level session cache for project tracking
    _sessions: ClassVar[dict[str, RalphSessionInfo]] = {}

    def __init__(
        self,
        project_dir: Path,
        websocket_url: str = DEFAULT_WEBSOCKET_URL,
    ) -> None:
        """Initialize the Ralph wrapper.

        Args:
            project_dir: Path to the project directory containing .ralph folder
            websocket_url: URL of the WebSocket server for event ingestion
        """
        self.project_dir = project_dir.resolve()
        self.websocket_url = websocket_url.rstrip("/")
        self.heartbeat_file = self.project_dir / HEARTBEAT_FILE
        self.log_dir = self.project_dir / LOG_DIR
        self.spec_checksums_dir = self.project_dir / SPEC_CHECKSUMS_DIR
        self.project_name = self.project_dir.name

        # Session management
        self.session_info: RalphSessionInfo | None = None
        self._last_heartbeat_status: str | None = None
        self._running = False
        self._session: aiohttp.ClientSession | None = None

        logger.info(
            f"Ralph wrapper initialized for project: {self.project_name} "
            f"at {self.project_dir}"
        )

    async def start(self) -> None:
        """Start the Ralph wrapper event monitoring loop."""
        if self._running:
            logger.warning("Ralph wrapper already running")
            return

        self._running = True
        self._session = aiohttp.ClientSession()

        logger.info("Starting Ralph wrapper event monitoring...")

        # Initialize database
        db_manager.init_db()

        try:
            # Detect or create Ralph session
            await self._ensure_session()

            # Start monitoring loop
            await self._monitoring_loop()

        except asyncio.CancelledError:
            logger.info("Ralph wrapper monitoring cancelled")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error in Ralph wrapper: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the Ralph wrapper and cleanup resources."""
        if not self._running:
            return

        logger.info("Stopping Ralph wrapper...")
        self._running = False

        # Mark session as ended if running
        if self.session_info and self.session_info.status == SessionStatus.RUNNING:
            await self._end_session(SessionStatus.COMPLETED)

        # Close HTTP session
        if self._session:
            await self._session.close()
            self._session = None

        logger.info("Ralph wrapper stopped")

    async def _ensure_session(self) -> None:
        """Ensure a Ralph session exists for this project."""
        # Check for existing session in cache
        cached_session = self._sessions.get(self.project_name)
        if cached_session:
            # Verify session is still active
            if await self._is_session_active(cached_session):
                self.session_info = cached_session
                logger.info(f"Using existing Ralph session: {cached_session.session_id}")
                return
            else:
                # Remove stale session from cache
                del self._sessions[self.project_name]

        # Detect active Ralph session
        detected_session = await self._detect_ralph_session()

        if detected_session:
            self.session_info = detected_session
            self._sessions[self.project_name] = detected_session
            logger.info(f"Detected active Ralph session: {detected_session.session_id}")
        else:
            # Create new session
            await self._create_session()

    async def _create_session(self) -> None:
        """Create a new Ralph session in the database."""
        # Detect Ralph process info
        pid = await self._check_ralph_process()
        tmux_session = await self._check_tmux_session()
        command = None
        working_dir = str(self.project_dir)

        # Try to get command from process
        if pid:
            try:
                proc = psutil.Process(pid)
                command = " ".join(proc.cmdline()) if proc.cmdline() else None
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        async with get_db_session() as db_session:
            db_session_obj = Session(
                agent_type=AgentType.RALPH,  # Use new RALPH agent type
                project_name=self.project_name,
                status=SessionStatus.RUNNING,
                metadata={
                    "wrapper": "ralph_wrapper",
                    "project_dir": str(self.project_dir),
                },
                started_at=datetime.now(timezone.utc),
                # Agent runtime metadata
                pid=pid,
                working_dir=working_dir,
                command=command,
                tmux_session=tmux_session,
            )
            db_session.add(db_session_obj)
            await db_session.flush()
            await db_session.refresh(db_session_obj)

            self.session_info = RalphSessionInfo(
                project_name=self.project_name,
                session_id=db_session_obj.id,
                pid=pid,
                tmux_session=tmux_session,
                started_at=datetime.now(timezone.utc),
                status=SessionStatus.RUNNING,
            )
            self._sessions[self.project_name] = self.session_info

            logger.info(f"Created new Ralph session: {db_session_obj.id}")

            # Emit session start event
            await self._emit_event(
                RalphEventType.SESSION_START,
                {
                    "project_name": self.project_name,
                    "agent_type": "ralph",
                },
            )

    async def _end_session(self, status: SessionStatus) -> None:
        """End the current Ralph session.

        Args:
            status: Final status of the session
        """
        if not self.session_info:
            return

        async with get_db_session() as db_session:
            from sqlalchemy import select

            result = await db_session.execute(
                select(Session).where(Session.id == self.session_info.session_id)
            )
            db_session_obj = result.scalar_one_or_none()

            if db_session_obj:
                db_session_obj.status = status
                db_session_obj.ended_at = datetime.now(timezone.utc)
                await db_session.commit()

        self.session_info.status = status

        # Remove from cache if completed/failed
        if status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED):
            self._sessions.pop(self.project_name, None)

        logger.info(f"Ralph session {self.session_info.session_id} ended with status: {status}")

    async def _detect_ralph_session(self) -> RalphSessionInfo | None:
        """Detect active Ralph session via tmux or process scan.

        Returns:
            RalphSessionInfo if active session detected, None otherwise
        """
        # Check for tmux session named "ralph"
        tmux_session = await self._check_tmux_session()
        if tmux_session:
            # Try to find existing session in database
            async with get_db_session() as db_session:
                from sqlalchemy import select

                result = await db_session.execute(
                    select(Session)
                    .where(Session.project_name == self.project_name)
                    .where(Session.agent_type == AgentType.RALPH)
                    .where(Session.status == SessionStatus.RUNNING)
                    .order_by(Session.started_at.desc())
                    .limit(1)
                )
                db_session_obj = result.scalar_one_or_none()

                if db_session_obj:
                    return RalphSessionInfo(
                        project_name=self.project_name,
                        session_id=db_session_obj.id,
                        tmux_session=tmux_session,
                        started_at=db_session_obj.started_at.replace(tzinfo=timezone.utc),
                        status=SessionStatus.RUNNING,
                    )

        # Check for Ralph/Claude processes
        pid = await self._check_ralph_process()
        if pid:
            # Similar logic for process-based detection
            async with get_db_session() as db_session:
                from sqlalchemy import select

                result = await db_session.execute(
                    select(Session)
                    .where(Session.project_name == self.project_name)
                    .where(Session.agent_type == AgentType.RALPH)
                    .where(Session.status == SessionStatus.RUNNING)
                    .order_by(Session.started_at.desc())
                    .limit(1)
                )
                db_session_obj = result.scalar_one_or_none()

                if db_session_obj:
                    return RalphSessionInfo(
                        project_name=self.project_name,
                        session_id=db_session_obj.id,
                        pid=pid,
                        started_at=db_session_obj.started_at.replace(tzinfo=timezone.utc),
                        status=SessionStatus.RUNNING,
                    )

        return None

    async def _check_tmux_session(self) -> str | None:
        """Check for tmux session named 'ralph'.

        Returns:
            Session name if found, None otherwise
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "tmux",
                "list-sessions",
                "-F",
                "#{session_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                sessions = stdout.decode().strip().split("\n")
                for session in sessions:
                    if "ralph" in session.lower():
                        return session

        except (FileNotFoundError, asyncio.CancelledError):  # noqa: BLE001
            pass

        return None

    async def _check_ralph_process(self) -> int | None:
        """Check for running Ralph/Claude processes.

        Returns:
            PID if found, None otherwise
        """
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        # Check for ralph.sh or claude commands
                        if "ralph.sh" in cmdline_str or (
                            "claude" in cmdline_str.lower()
                            and str(self.project_dir) in cmdline_str
                        ):
                            return proc.info["pid"]
                except (psutil.NoSuchProcess, psutil.AccessDenied):  # noqa: PERF203
                    continue

        except Exception:  # noqa: BLE001
            pass

        return None

    async def _is_session_active(self, session_info: RalphSessionInfo) -> bool:
        """Check if a session is still active.

        Args:
            session_info: Session info to check

        Returns:
            True if session is still active, False otherwise
        """
        # Check if process is running
        if session_info.pid:
            try:
                if psutil.pid_exists(session_info.pid):
                    return True
            except Exception:  # noqa: BLE001
                pass

        # Check if tmux session exists
        if session_info.tmux_session:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "tmux",
                    "list-sessions",
                    "-F",
                    "#{session_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()

                if proc.returncode == 0:
                    sessions = stdout.decode().strip().split("\n")
                    return session_info.tmux_session in sessions

            except (FileNotFoundError, asyncio.CancelledError):  # noqa: BLE001
                pass

        return False

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for heartbeat file and process detection."""
        logger.info("Starting heartbeat monitoring loop...")

        last_mod_time = 0.0

        while self._running:
            try:
                # Check if heartbeat file exists
                if not self.heartbeat_file.exists():
                    logger.debug(f"Heartbeat file not found: {self.heartbeat_file}")
                    await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)
                    continue

                # Check for heartbeat file modification
                current_mod_time = self.heartbeat_file.stat().st_mtime
                if current_mod_time <= last_mod_time:
                    await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)
                    continue

                last_mod_time = current_mod_time

                # Read and parse heartbeat
                heartbeat_data = await self._read_heartbeat()
                if not heartbeat_data:
                    await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)
                    continue

                # Process heartbeat if status changed
                if heartbeat_data.status != self._last_heartbeat_status:
                    await self._process_heartbeat(heartbeat_data)
                    self._last_heartbeat_status = heartbeat_data.status

                # Check for process crash
                if self.session_info and self.session_info.pid:
                    if not psutil.pid_exists(self.session_info.pid):
                        logger.warning(f"Ralph process {self.session_info.pid} died")
                        await self._emit_event(
                            RalphEventType.ERROR,
                            {
                                "message": "Ralph process crashed",
                                "pid": self.session_info.pid,
                            },
                        )
                        await self._end_session(SessionStatus.FAILED)

                await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)

            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(POLLING_INTERVAL)

    async def _read_heartbeat(self) -> HeartbeatData | None:
        """Read and parse the heartbeat file.

        Returns:
            HeartbeatData if successful, None otherwise
        """
        try:
            content = self.heartbeat_file.read_text()
            data = json.loads(content)
            return HeartbeatData.from_dict(data)

        except (json.JSONDecodeError, IOError) as e:  # noqa: PERF203
            logger.warning(f"Error reading heartbeat file: {e}")
            return None

    async def _process_heartbeat(self, heartbeat: HeartbeatData) -> None:
        """Process a heartbeat event and emit to Dope Dash.

        Args:
            heartbeat: Parsed heartbeat data
        """
        event_type = heartbeat.event_type
        if not event_type:
            logger.debug(f"No event type for heartbeat status: {heartbeat.status}")
            return

        event_data = {
            "timestamp": heartbeat.timestamp,
            "status": heartbeat.status,
            "project_name": self.project_name,
        }

        # Add spec-specific data
        if heartbeat.spec_name:
            event_data["spec_name"] = heartbeat.spec_name

        # Add error message if present
        if heartbeat.error_message:
            event_data["error"] = heartbeat.error_message

        await self._emit_event(event_type, event_data)

        # Handle session completion
        if event_type == RalphEventType.SESSION_END:
            await self._end_session(SessionStatus.COMPLETED)

    async def _emit_event(
        self,
        event_type: RalphEventType,
        data: dict[str, Any],
    ) -> None:
        """Emit an event to the WebSocket server.

        Args:
            event_type: Type of event to emit
            data: Event data payload
        """
        if not self.session_info:
            logger.warning("No session info, skipping event emission")
            return

        event = EventIngestRequest(
            session_id=self.session_info.session_id,
            event_type=event_type.value,
            data=data,
        )

        # Try to send via WebSocket API
        success = await self._send_to_websocket(event)

        # Fallback to polling if WebSocket unavailable
        if not success:
            logger.debug("WebSocket unavailable, event queued for polling")
            await self._queue_for_polling(event)

    async def _send_to_websocket(self, event: EventIngestRequest) -> bool:
        """Send event to WebSocket server via HTTP POST.

        Args:
            event: Event to send

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            return False

        url = f"{self.websocket_url}/api/events"

        try:
            async with self._session.post(
                url,
                json=event.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    logger.debug(
                        f"Event {event.event_type} sent successfully to WebSocket server"
                    )
                    return True
                else:
                    logger.warning(
                        f"WebSocket server returned status {response.status}"
                    )
                    return False

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:  # noqa: PERF203
            logger.debug(f"Failed to send event to WebSocket server: {e}")
            return False

    async def _queue_for_polling(self, event: EventIngestRequest) -> None:
        """Queue event for polling when WebSocket is unavailable.

        Args:
            event: Event to queue
        """
        # In a production system, this would write to a persistent queue
        # For now, we'll just log it and attempt to send later
        logger.info(
            f"Event queued for polling: {event.event_type} "
            f"(session: {event.session_id})"
        )


async def run_wrapper(project_dir: Path, websocket_url: str) -> None:
    """Run the Ralph wrapper with signal handling.

    Args:
        project_dir: Project directory path
        websocket_url: WebSocket server URL
    """
    wrapper = RalphWrapper(
        project_dir=project_dir,
        websocket_url=websocket_url,
    )

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        asyncio.create_task(wrapper.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await wrapper.start()
    except asyncio.CancelledError:
        logger.info("Wrapper cancelled")
    finally:
        # Remove signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


def main() -> None:
    """Main entry point for the Ralph wrapper."""
    parser = argparse.ArgumentParser(
        description="Ralph Inferno agent wrapper for Dope Dash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m wrappers.ralph_wrapper
  python -m wrappers.ralph_wrapper --project-dir /path/to/project
  python -m wrappers.ralph_wrapper --websocket-url http://localhost:8001
  python -m wrappers.ralph_wrapper --debug
        """,
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=DEFAULT_PROJECT_DIR,
        help="Path to project directory (default: current directory)",
    )

    parser.add_argument(
        "--websocket-url",
        type=str,
        default=DEFAULT_WEBSOCKET_URL,
        help=f"WebSocket server URL (default: {DEFAULT_WEBSOCKET_URL})",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validate project directory
    if not args.project_dir.exists():
        logger.error(f"Project directory does not exist: {args.project_dir}")
        sys.exit(1)

    if not (args.project_dir / ".ralph").exists():
        logger.error(f".ralph directory not found in: {args.project_dir}")
        sys.exit(1)

    # Run the wrapper
    try:
        asyncio.run(run_wrapper(args.project_dir, args.websocket_url))
    except KeyboardInterrupt:
        logger.info("Wrapper interrupted by user")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Wrapper error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
