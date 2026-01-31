"""Terminal agent wrapper for Dope Dash event streaming.

This wrapper monitors terminal session activity by tracking tmux sessions,
capturing shell command execution, parsing shell history, and streaming
events to the Dope Dash dashboard.

Features:
- Tracks tmux sessions as terminal sessions
- Parses command execution events from shell history
- Transforms terminal events to unified event format
- Detects terminal sessions via tmux and process scanning
- Sends events to WebSocket server via HTTP POST
- Handles process crashes and restarts
- Polling fallback when WebSocket unavailable
- Adds terminal metadata (shell type, working directory)
- Creates and manages terminal sessions in database

Usage:
    python -m wrappers.terminal_wrapper
    python -m wrappers.terminal_wrapper --project-dir /path/to/project
    python -m wrappers.terminal_wrapper --tmux-session mysession
    python -m wrappers.terminal_wrapper --shell bash
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
import psutil
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.session import Session, SessionStatus, AgentType
from app.models.unified_events import (
    UnifiedEventFactory,
    UnifiedEventType,
    TaskEvent,
    ErrorEvent,
    CommandEvent,
    StateChangeEvent,
)
from db.connection import db_manager, get_db_session


logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_WEBSOCKET_URL = "http://localhost:8001"
DEFAULT_PROJECT_DIR = Path.cwd()

# Terminal-specific paths
BASH_HISTORY = Path.home() / ".bash_history"
ZSH_HISTORY = Path.home() / ".zsh_history"
FISH_HISTORY = Path.home() / ".local/state/fish/history"

# Polling intervals (seconds)
POLLING_INTERVAL = 5
HEARTBEAT_CHECK_INTERVAL = 2
HISTORY_CHECK_INTERVAL = 3


class TerminalEventType(str, Enum):
    """Terminal-specific event types parsed from shell activity."""

    # Command events
    COMMAND_START = "command_start"
    COMMAND_COMPLETE = "command_complete"
    COMMAND_ERROR = "command_error"

    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    HEARTBEAT = "heartbeat"

    # Tmux events
    TMUX_SESSION_CREATE = "tmux_session_create"
    TMUX_SESSION_ATTACH = "tmux_session_attach"
    TMUX_SESSION_DETACH = "tmux_session_detach"
    TMUX_SESSION_KILL = "tmux_session_kill"

    # Shell events
    SHELL_START = "shell_start"
    SHELL_EXIT = "shell_exit"

    # Directory events
    DIRECTORY_CHANGE = "directory_change"

    # Error events
    ERROR = "error"
    WARNING = "warning"


class ShellType(str, Enum):
    """Types of shells that can be tracked."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    SH = "sh"
    UNKNOWN = "unknown"


@dataclass
class TerminalEvent:
    """Parsed terminal event from shell activity."""

    event_type: TerminalEventType
    timestamp: str
    raw: dict = field(default_factory=dict)

    # Command-specific fields
    command: str | None = None
    args: list[str] | None = None
    exit_code: int | None = None
    duration: float | None = None
    working_dir: str | None = None
    shell_type: ShellType = ShellType.UNKNOWN

    # Tmux-specific fields
    tmux_session: str | None = None
    tmux_window: int | None = None
    tmux_pane: int | None = None

    # Error-specific fields
    error_message: str | None = None
    error_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> TerminalEvent:
        """Create TerminalEvent from dictionary."""
        return cls(
            event_type=TerminalEventType(data.get("event_type", "unknown")),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            raw=data,
            command=data.get("command"),
            args=data.get("args"),
            exit_code=data.get("exit_code"),
            duration=data.get("duration"),
            working_dir=data.get("working_dir"),
            shell_type=ShellType(data.get("shell_type", "unknown")),
            tmux_session=data.get("tmux_session"),
            tmux_window=data.get("tmux_window"),
            tmux_pane=data.get("tmux_pane"),
            error_message=data.get("error_message"),
            error_type=data.get("error_type"),
        )


@dataclass
class TerminalSessionInfo:
    """Information about a terminal session."""

    project_name: str
    session_id: uuid.UUID
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    started_at: datetime | None = None
    status: SessionStatus = SessionStatus.RUNNING
    shell_type: ShellType = ShellType.UNKNOWN
    tmux_session: str | None = None


class EventIngestRequest(BaseModel):
    """Request schema for event ingestion."""

    session_id: uuid.UUID
    event_type: str
    data: dict = {}


class TerminalWrapper:
    """Terminal session wrapper for event streaming.

    This class monitors terminal session activity and streams events to Dope Dash.
    """

    def __init__(
        self,
        project_dir: Path,
        websocket_url: str = DEFAULT_WEBSOCKET_URL,
        pid: int | None = None,
        working_dir: str | None = None,
        command: str | None = None,
        tmux_session: str | None = None,
        shell_type: ShellType = ShellType.UNKNOWN,
    ) -> None:
        """Initialize the Terminal wrapper.

        Args:
            project_dir: Path to the project directory
            websocket_url: URL of the WebSocket server for event ingestion
            pid: Process ID of the terminal session (optional)
            working_dir: Working directory of the terminal (optional)
            command: Command line used to start the terminal (optional)
            tmux_session: Tmux session name (optional)
            shell_type: Shell type being tracked (optional)
        """
        self.project_dir = project_dir.resolve()
        self.websocket_url = websocket_url.rstrip("/")
        self.project_name = self.project_dir.name

        # Agent metadata
        self._pid = pid
        self._working_dir = working_dir or str(self.project_dir)
        self._command = command
        self._tmux_session = tmux_session
        self._shell_type = shell_type

        # Session management
        self.session_info: TerminalSessionInfo | None = None
        self._running = False
        self._http_session: aiohttp.ClientSession | None = None

        # Event queue
        self._event_queue: asyncio.Queue[TerminalEvent] = asyncio.Queue()

        # Polling fallback
        self._queued_events: list[EventIngestRequest] = []

        # History file tracking
        self._history_file_positions: dict[Path, int] = {}
        self._command_history: dict[str, list[dict]] = {}  # Track running commands

        logger.info(
            f"Terminal wrapper initialized for project: {self.project_name} "
            f"at {self.project_dir}"
        )

    async def start(self) -> None:
        """Start the Terminal wrapper event monitoring loop."""
        if self._running:
            logger.warning("Terminal wrapper already running")
            return

        self._running = True
        self._http_session = aiohttp.ClientSession()

        logger.info("Starting Terminal wrapper event monitoring...")

        # Initialize database
        db_manager.init_db()

        try:
            # Detect or create terminal session
            await self._ensure_session()

            # Start monitoring loop
            await self._monitoring_loop()

        except asyncio.CancelledError:
            logger.info("Terminal wrapper monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in Terminal wrapper: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the Terminal wrapper and cleanup resources."""
        if not self._running:
            return

        logger.info("Stopping Terminal wrapper...")
        self._running = False

        # End session
        if self.session_info and self.session_info.status == SessionStatus.RUNNING:
            await self._end_session(SessionStatus.COMPLETED)

        # Flush queued events
        if self._queued_events:
            logger.info(f"Flushing {len(self._queued_events)} queued events")
            for event in self._queued_events:
                await self._send_to_websocket(event)

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        logger.info("Terminal wrapper stopped")

    async def _ensure_session(self) -> None:
        """Ensure a terminal session exists for this project."""
        # Detect active terminal session
        detected_session = await self._detect_terminal_session()

        if detected_session:
            self.session_info = detected_session
            logger.info(f"Detected active terminal session: {detected_session.session_id}")
        else:
            # Create new session
            await self._create_session()

    async def _create_session(self) -> None:
        """Create a new terminal session in the database."""
        # Detect terminal process info
        pid = await self._detect_terminal_process()
        command = self._command
        working_dir = self._working_dir

        # Try to get command from process
        if pid and not command:
            try:
                proc = psutil.Process(pid)
                command = " ".join(proc.cmdline()) if proc.cmdline() else None
                working_dir = proc.cwd() if proc.cwd() else working_dir
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Detect shell type if not provided
        if self._shell_type == ShellType.UNKNOWN:
            self._shell_type = await self._detect_shell_type(pid) if pid else ShellType.BASH

        async with get_db_session() as db_session:
            db_session_obj = Session(
                agent_type=AgentType.TERMINAL,
                project_name=self.project_name,
                status=SessionStatus.RUNNING,
                metadata={
                    "wrapper": "terminal_wrapper",
                    "project_dir": str(self.project_dir),
                    "shell_type": self._shell_type.value,
                },
                started_at=datetime.now(timezone.utc),
                pid=pid,
                working_dir=working_dir,
                command=command,
                tmux_session=self._tmux_session,
            )
            db_session.add(db_session_obj)
            await db_session.flush()
            await db_session.refresh(db_session_obj)

            self.session_info = TerminalSessionInfo(
                project_name=self.project_name,
                session_id=db_session_obj.id,
                pid=pid,
                working_dir=working_dir,
                command=command,
                started_at=datetime.now(timezone.utc),
                status=SessionStatus.RUNNING,
                shell_type=self._shell_type,
                tmux_session=self._tmux_session,
            )

            logger.info(f"Created new terminal session: {db_session_obj.id}")

            # Emit session start event
            await self._emit_event(
                *UnifiedEventFactory.session_start(
                    project_name=self.project_name,
                    agent_type="terminal",
                    metadata={
                        "shell_type": self._shell_type.value,
                        "tmux_session": self._tmux_session,
                    },
                )
            )

    async def _detect_shell_type(self, pid: int | None) -> ShellType:
        """Detect the shell type from process or environment.

        Args:
            pid: Process ID to check

        Returns:
            Detected shell type
        """
        # Check from SHELL environment variable
        shell_path = os.environ.get("SHELL", "")
        if "bash" in shell_path:
            return ShellType.BASH
        elif "zsh" in shell_path:
            return ShellType.ZSH
        elif "fish" in shell_path:
            return ShellType.FISH

        # Check from process if pid provided
        if pid:
            try:
                proc = psutil.Process(pid)
                cmdline = proc.cmdline()
                if cmdline:
                    cmd_name = Path(cmdline[0]).name
                    if "bash" in cmd_name:
                        return ShellType.BASH
                    elif "zsh" in cmd_name:
                        return ShellType.ZSH
                    elif "fish" in cmd_name:
                        return ShellType.FISH
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return ShellType.BASH  # Default to bash

    async def _end_session(self, status: SessionStatus) -> None:
        """End the current terminal session.

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

        logger.info(f"Terminal session {self.session_info.session_id} ended with status: {status}")

    async def _detect_terminal_session(self) -> TerminalSessionInfo | None:
        """Detect active terminal session via tmux or process scan.

        Returns:
            TerminalSessionInfo if active session detected, None otherwise
        """
        # First check for tmux session if specified
        if self._tmux_session:
            tmux_exists = await self._check_tmux_session(self._tmux_session)
            if tmux_exists:
                # Try to find existing session in database
                async with get_db_session() as db_session:
                    from sqlalchemy import select

                    result = await db_session.execute(
                        select(Session)
                        .where(Session.project_name == self.project_name)
                        .where(Session.agent_type == AgentType.TERMINAL)
                        .where(Session.tmux_session == self._tmux_session)
                        .where(Session.status == SessionStatus.RUNNING)
                        .order_by(Session.started_at.desc())
                        .limit(1)
                    )
                    db_session_obj = result.scalar_one_or_none()

                    if db_session_obj:
                        return TerminalSessionInfo(
                            project_name=self.project_name,
                            session_id=db_session_obj.id,
                            pid=db_session_obj.pid,
                            working_dir=db_session_obj.working_dir,
                            command=db_session_obj.command,
                            started_at=db_session_obj.started_at.replace(tzinfo=timezone.utc),
                            status=SessionStatus.RUNNING,
                            shell_type=self._shell_type,
                            tmux_session=self._tmux_session,
                        )

        # Check for any terminal process
        pid = await self._detect_terminal_process()
        if pid:
            # Try to find existing session in database
            async with get_db_session() as db_session:
                from sqlalchemy import select

                result = await db_session.execute(
                    select(Session)
                    .where(Session.project_name == self.project_name)
                    .where(Session.agent_type == AgentType.TERMINAL)
                    .where(Session.status == SessionStatus.RUNNING)
                    .order_by(Session.started_at.desc())
                    .limit(1)
                )
                db_session_obj = result.scalar_one_or_none()

                if db_session_obj:
                    try:
                        proc = psutil.Process(pid)
                        command = " ".join(proc.cmdline()) if proc.cmdline() else None
                        working_dir = proc.cwd() if proc.cwd() else None
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        command = None
                        working_dir = None

                    return TerminalSessionInfo(
                        project_name=self.project_name,
                        session_id=db_session_obj.id,
                        pid=pid,
                        working_dir=working_dir,
                        command=command,
                        started_at=db_session_obj.started_at.replace(tzinfo=timezone.utc),
                        status=SessionStatus.RUNNING,
                        shell_type=self._shell_type,
                        tmux_session=self._tmux_session,
                    )

        return None

    async def _check_tmux_session(self, session_name: str) -> bool:
        """Check if a tmux session exists.

        Args:
            session_name: Name of the tmux session

        Returns:
            True if session exists, False otherwise
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "tmux",
                "has-session",
                "-t",
                session_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    async def _detect_terminal_process(self) -> int | None:
        """Detect running terminal/shell processes.

        Returns:
            PID if found, None otherwise
        """
        try:
            # Get current process's parent (shell)
            current_proc = psutil.Process()
            parent = current_proc.parent()

            # Check if parent is a shell
            if parent and await self._is_shell_process(parent):
                return parent.pid

            # Check for tmux sessions
            tmux_sessions = await self._list_tmux_sessions()
            if tmux_sessions and self._tmux_session in tmux_sessions:
                # Find a process in the tmux session
                for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
                    try:
                        cwd = proc.info.get("cwd", "")
                        if str(self.project_dir) in cwd or cwd == str(self.project_dir):
                            if await self._is_shell_process(proc):
                                return proc.info["pid"]
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

        except Exception:
            pass

        return None

    async def _is_shell_process(self, proc: psutil.Process) -> bool:
        """Check if a process is a shell.

        Args:
            proc: Process to check

        Returns:
            True if process is a shell, False otherwise
        """
        try:
            name = proc.name().lower()
            cmdline = " ".join(proc.cmdline()).lower() if proc.cmdline() else ""

            return any(
                shell in name or shell in cmdline
                for shell in ["bash", "zsh", "fish", "sh"]
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    async def _list_tmux_sessions(self) -> list[str]:
        """List all active tmux sessions.

        Returns:
            List of tmux session names
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
                return [s for s in sessions if s]

        except (FileNotFoundError, OSError):
            pass

        return []

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for terminal activity."""
        logger.info("Starting Terminal monitoring loop...")

        # Start event processor
        event_processor = asyncio.create_task(self._event_processor())

        # Initialize history file positions
        await self._init_history_tracking()

        while self._running:
            try:
                # Update heartbeat
                await self._update_heartbeat()

                # Check for process crash
                if self.session_info and self.session_info.pid:
                    if not psutil.pid_exists(self.session_info.pid):
                        logger.warning(f"Terminal process {self.session_info.pid} ended")
                        await self._emit_event(
                            *UnifiedEventFactory.state_change(
                                StateChangeEvent(
                                    old_state="running",
                                    new_state="stopped",
                                    reason="Process ended",
                                )
                            )
                        )
                        break

                # Poll for new commands
                await self._poll_for_commands()

                # Check tmux session status
                if self._tmux_session:
                    tmux_exists = await self._check_tmux_session(self._tmux_session)
                    if not tmux_exists:
                        logger.info(f"Tmux session {self._tmux_session} ended")
                        await self._emit_event(
                            UnifiedEventType.TMUX_SESSION_KILL.value,
                            {"tmux_session": self._tmux_session},
                        )
                        break

                await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(POLLING_INTERVAL)

        # Cleanup event processor
        event_processor.cancel()
        try:
            await event_processor
        except asyncio.CancelledError:
            pass

    async def _init_history_tracking(self) -> None:
        """Initialize history file position tracking."""
        history_files = [
            (BASH_HISTORY, ShellType.BASH),
            (ZSH_HISTORY, ShellType.ZSH),
            (FISH_HISTORY, ShellType.FISH),
        ]

        for history_path, shell_type in history_files:
            if history_path.exists():
                # Start reading from end of file
                self._history_file_positions[history_path] = history_path.stat().st_size
                logger.debug(f"Tracking history file: {history_path}")

    async def _poll_for_commands(self) -> None:
        """Poll shell history files for new commands."""
        history_files = [
            (BASH_HISTORY, ShellType.BASH),
            (ZSH_HISTORY, ShellType.ZSH),
            (FISH_HISTORY, ShellType.FISH),
        ]

        for history_path, shell_type in history_files:
            if not history_path.exists():
                continue

            try:
                # Get last position
                pos = self._history_file_positions.get(history_path, 0)

                # Read new content
                with open(history_path, "rb") as f:
                    f.seek(pos)
                    new_content = f.read()
                    self._history_file_positions[history_path] = f.tell()

                if new_content:
                    await self._parse_history_content(
                        new_content.decode(errors="ignore"),
                        history_path,
                        shell_type,
                    )

            except (IOError, OSError):
                pass

    async def _parse_history_content(
        self,
        content: str,
        source: Path,
        shell_type: ShellType,
    ) -> None:
        """Parse shell history content for command events.

        Args:
            content: History content to parse
            source: Source file path
            shell_type: Type of shell
        """
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip comments
            if line.startswith("#"):
                continue

            # Parse based on shell type
            if shell_type == ShellType.ZSH:
                # zsh history format: : timestamp:duration;command
                match = re.match(r":\s*(\d+):(\d+);(.+)", line)
                if match:
                    timestamp, duration, command = match.groups()
                    event = TerminalEvent(
                        event_type=TerminalEventType.COMMAND_COMPLETE,
                        timestamp=datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat(),
                        command=command,
                        args=self._parse_command_args(command),
                        duration=float(duration),
                        shell_type=shell_type,
                        raw={"line": line, "source": str(source)},
                    )
                    await self._event_queue.put(event)
                    continue

            elif shell_type == ShellType.FISH:
                # fish history is JSON-like
                try:
                    data = json.loads(line)
                    if "cmd" in data:
                        event = TerminalEvent(
                            event_type=TerminalEventType.COMMAND_COMPLETE,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            command=data["cmd"],
                            args=self._parse_command_args(data["cmd"]),
                            shell_type=shell_type,
                            raw={"source": str(source), "data": data},
                        )
                        await self._event_queue.put(event)
                        continue
                except json.JSONDecodeError:
                    pass

            # Default/bash format - just the command
            event = TerminalEvent(
                event_type=TerminalEventType.COMMAND_COMPLETE,
                timestamp=datetime.now(timezone.utc).isoformat(),
                command=line,
                args=self._parse_command_args(line),
                shell_type=shell_type,
                raw={"line": line, "source": str(source)},
            )
            await self._event_queue.put(event)

    def _parse_command_args(self, command: str) -> list[str]:
        """Parse command arguments from command string.

        Args:
            command: Command string to parse

        Returns:
            List of arguments
        """
        # Simple shell-like argument parsing
        import shlex
        try:
            parts = shlex.split(command)
            return parts[1:] if len(parts) > 1 else []
        except ValueError:
            return []

    async def _event_processor(self) -> None:
        """Process events from the queue and send to WebSocket."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0,
                )

                # Transform to unified event
                unified_event = self._transform_event(event)

                # Emit event
                await self._emit_event(*unified_event)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)

    def _transform_event(
        self, event: TerminalEvent
    ) -> tuple[str, dict[str, Any]]:
        """Transform terminal event to unified event format.

        Args:
            event: Terminal event to transform

        Returns:
            Tuple of (event_type, data)
        """
        # Command events
        if event.event_type == TerminalEventType.COMMAND_START:
            task_event = TaskEvent(
                task_id=f"cmd_{uuid.uuid4().hex[:8]}",
                task_type="command_execution",
                task_name=f"Execute: {event.command}",
                metadata={
                    "command": event.command,
                    "args": event.args,
                    "working_dir": event.working_dir,
                    "shell_type": event.shell_type.value,
                    "tmux_session": event.tmux_session,
                },
            )
            return UnifiedEventFactory.task_start(task_event)

        if event.event_type == TerminalEventType.COMMAND_COMPLETE:
            command_event = CommandEvent(
                command=event.command or "",
                args=event.args or [],
                exit_code=event.exit_code,
                duration=event.duration,
            )
            return UnifiedEventFactory.command(command_event)

        if event.event_type == TerminalEventType.COMMAND_ERROR:
            error_event = ErrorEvent(
                message=event.error_message or "Command failed",
                error_type=event.error_type or "CommandError",
            )
            return UnifiedEventFactory.error(error_event)

        # Tmux events
        if event.event_type == TerminalEventType.TMUX_SESSION_CREATE:
            task_event = TaskEvent(
                task_id=f"tmux_{event.tmux_session}",
                task_type="tmux_session",
                task_name=f"Tmux session: {event.tmux_session}",
                metadata={"tmux_session": event.tmux_session},
            )
            return UnifiedEventFactory.task_start(task_event)

        if event.event_type == TerminalEventType.TMUX_SESSION_KILL:
            return UnifiedEventFactory.task_complete(
                task_id=f"tmux_{event.tmux_session}",
                result={"status": "ended"},
            )

        # Error events
        if event.event_type == TerminalEventType.ERROR:
            error_event = ErrorEvent(
                message=event.error_message or "Unknown error",
                error_type=event.error_type or "TerminalError",
            )
            return UnifiedEventFactory.error(error_event)

        # Warning events
        if event.event_type == TerminalEventType.WARNING:
            return (
                UnifiedEventType.WARNING.value,
                {"message": event.error_message or "Warning"},
            )

        # Default: pass through as-is
        return event.event_type.value, event.raw

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
        if not self.session_info:
            logger.warning("No session info, skipping event emission")
            return

        event = EventIngestRequest(
            session_id=self.session_info.session_id,
            event_type=event_type,
            data=data,
        )

        # Try to send via WebSocket API
        success = await self._send_to_websocket(event)

        # Fallback to polling if WebSocket unavailable
        if not success:
            logger.debug("WebSocket unavailable, event queued for polling")
            self._queued_events.append(event)

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
        if not self.session_info:
            return

        async with get_db_session() as db_session:
            from sqlalchemy import select

            result = await db_session.execute(
                select(Session).where(Session.id == self.session_info.session_id)
            )
            db_session_obj = result.scalar_one_or_none()

            if db_session_obj:
                db_session_obj.last_heartbeat = datetime.now(timezone.utc)
                await db_session.commit()


async def run_wrapper(
    project_dir: Path,
    websocket_url: str,
    pid: int | None = None,
    working_dir: str | None = None,
    command: str | None = None,
    tmux_session: str | None = None,
    shell_type: ShellType = ShellType.UNKNOWN,
) -> None:
    """Run the Terminal wrapper with signal handling.

    Args:
        project_dir: Project directory path
        websocket_url: WebSocket server URL
        pid: Process ID of terminal session
        working_dir: Working directory
        command: Command line
        tmux_session: Tmux session name
        shell_type: Shell type to track
    """
    wrapper = TerminalWrapper(
        project_dir=project_dir,
        websocket_url=websocket_url,
        pid=pid,
        working_dir=working_dir,
        command=command,
        tmux_session=tmux_session,
        shell_type=shell_type,
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
    """Main entry point for the Terminal wrapper."""
    parser = argparse.ArgumentParser(
        description="Terminal agent wrapper for Dope Dash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m wrappers.terminal_wrapper
  python -m wrappers.terminal_wrapper --project-dir /path/to/project
  python -m wrappers.terminal_wrapper --tmux-session mysession
  python -m wrappers.terminal_wrapper --shell zsh
  python -m wrappers.terminal_wrapper --debug
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
        "--pid",
        type=int,
        default=None,
        help="Process ID of terminal session (optional, auto-detected if not provided)",
    )

    parser.add_argument(
        "--working-dir",
        type=str,
        default=None,
        help="Working directory of terminal session (optional)",
    )

    parser.add_argument(
        "--command",
        type=str,
        default=None,
        help="Command line used to start terminal (optional)",
    )

    parser.add_argument(
        "--tmux-session",
        type=str,
        default=None,
        help="Tmux session name to track (optional)",
    )

    parser.add_argument(
        "--shell",
        type=str,
        choices=["bash", "zsh", "fish", "sh", "unknown"],
        default="unknown",
        help="Shell type to track (default: auto-detect)",
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

    # Convert shell argument to enum
    shell_type = ShellType(args.shell)

    # Run the wrapper
    try:
        asyncio.run(
            run_wrapper(
                args.project_dir,
                args.websocket_url,
                args.pid,
                args.working_dir,
                args.command,
                args.tmux_session,
                shell_type,
            )
        )
    except KeyboardInterrupt:
        logger.info("Wrapper interrupted by user")
    except Exception as e:
        logger.error(f"Wrapper error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
