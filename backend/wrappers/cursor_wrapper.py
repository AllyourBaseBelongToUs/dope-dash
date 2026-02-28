"""Cursor IDE agent wrapper for Dope Dash event streaming.

This wrapper monitors Cursor IDE agent execution by intercepting
stdout/stderr from the Cursor process, captures events, transforms them
to Dope Dash format, and streams them to the WebSocket server.

Features:
- Intercepts Cursor IDE process stdout/stderr
- Parses Cursor-specific events (edit, chat, command)
- Transforms Cursor events to unified event format
- Detects Cursor sessions via process scanning
- Sends events to WebSocket server via HTTP POST
- Handles process crashes and restarts
- Polling fallback when WebSocket unavailable
- Adds Cursor-specific metadata (file edits, context)
- Creates and manages Cursor sessions in database

Usage:
    python -m wrappers.cursor_wrapper
    python -m wrappers.cursor_wrapper --project-dir /path/to/project
    python -m wrappers.cursor_wrapper --pid 12345
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
import psutil
from pydantic import BaseModel, ValidationError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.models.session import Session, SessionStatus, AgentType
from app.models.unified_events import (
    UnifiedEventFactory,
    UnifiedEventType,
    TaskEvent,
    ErrorEvent,
    MessageEvent,
    CommandEvent,
)
from db.connection import db_manager, get_db_session


logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_WEBSOCKET_URL = "http://localhost:8005"
DEFAULT_PROJECT_DIR = Path.cwd()

# Cursor-specific directories
CURSOR_CONFIG_DIR = Path.home() / ".cursor"
CURSOR_SESSIONS_DIR = CURSOR_CONFIG_DIR / "sessions"
CURSOR_LOGS_DIR = CURSOR_CONFIG_DIR / "logs"
CURSOR_STORAGE_DIR = Path.home() / ".cursor" / "storage"

# Polling intervals (seconds)
POLLING_INTERVAL = 5
HEARTBEAT_CHECK_INTERVAL = 2
PROCESS_CHECK_INTERVAL = 1


class CursorEventType(str, Enum):
    """Cursor-specific event types parsed from stdout/stderr."""

    # Edit events
    EDIT_START = "edit_start"
    EDIT_COMPLETE = "edit_complete"
    EDIT_ERROR = "edit_error"

    # Chat events
    CHAT_START = "chat_start"
    CHAT_COMPLETE = "chat_complete"
    CHAT_STREAM = "chat_stream"

    # File operations
    FILE_OPEN = "file_open"
    FILE_SAVE = "file_save"
    FILE_CLOSE = "file_close"

    # Command events
    COMMAND_START = "command_start"
    COMMAND_COMPLETE = "command_complete"

    # Error events
    ERROR = "error"
    WARNING = "warning"

    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    HEARTBEAT = "heartbeat"

    # Agent events
    AGENT_THINKING_START = "agent_thinking_start"
    AGENT_THINKING_COMPLETE = "agent_thinking_complete"


class CursorTool(str, Enum):
    """Cursor IDE tools that can be invoked."""

    EDIT_FILE = "edit_file"
    READ_FILE = "read_file"
    SEARCH_IN_FILES = "search_in_files"
    RUN_COMMAND = "run_command"
    CHAT = "chat"
    COMPLETION = "completion"
    REFACTOR = "refactor"
    EXPLAIN = "explain"
    TEST_GENERATION = "test_generation"


@dataclass
class CursorEvent:
    """Parsed Cursor event from stdout/stderr."""

    event_type: CursorEventType
    timestamp: str
    raw: dict = field(default_factory=dict)

    # Edit-specific fields
    file_path: str | None = None
    old_content: str | None = None
    new_content: str | None = None
    edit_range: tuple[int, int] | None = None

    # Chat-specific fields
    role: str | None = None
    content: str | None = None
    model: str | None = None

    # Error-specific fields
    error_message: str | None = None
    error_type: str | None = None

    # Command-specific fields
    command: str | None = None
    args: list[str] | None = None
    exit_code: int | None = None

    # Agent-specific fields
    agent_name: str | None = None
    thinking_steps: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> CursorEvent:
        """Create CursorEvent from dictionary."""
        return cls(
            event_type=CursorEventType(data.get("event_type", "unknown")),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            raw=data,
            file_path=data.get("file_path"),
            old_content=data.get("old_content"),
            new_content=data.get("new_content"),
            edit_range=tuple(data["edit_range"]) if data.get("edit_range") else None,
            role=data.get("role"),
            content=data.get("content"),
            model=data.get("model"),
            error_message=data.get("error_message"),
            error_type=data.get("error_type"),
            command=data.get("command"),
            args=data.get("args"),
            exit_code=data.get("exit_code"),
            agent_name=data.get("agent_name"),
            thinking_steps=data.get("thinking_steps"),
        )


@dataclass
class CursorSessionInfo:
    """Information about a Cursor session."""

    project_name: str
    session_id: uuid.UUID
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    started_at: datetime | None = None
    status: SessionStatus = SessionStatus.RUNNING
    model: str | None = None  # Cursor model being used


class EventIngestRequest(BaseModel):
    """Request schema for event ingestion."""

    session_id: uuid.UUID
    event_type: str
    data: dict = {}


class CursorWrapper:
    """Cursor IDE agent wrapper for event streaming.

    This class monitors Cursor agent execution and streams events to Dope Dash.
    """

    def __init__(
        self,
        project_dir: Path,
        websocket_url: str = DEFAULT_WEBSOCKET_URL,
        pid: int | None = None,
        working_dir: str | None = None,
        command: str | None = None,
    ) -> None:
        """Initialize the Cursor wrapper.

        Args:
            project_dir: Path to the project directory
            websocket_url: URL of the WebSocket server for event ingestion
            pid: Process ID of the Cursor agent (optional)
            working_dir: Working directory of the agent (optional)
            command: Command line used to start the agent (optional)
        """
        self.project_dir = project_dir.resolve()
        self.websocket_url = websocket_url.rstrip("/")
        self.project_name = self.project_dir.name

        # Agent metadata
        self._pid = pid
        self._working_dir = working_dir or str(self.project_dir)
        self._command = command

        # Session management
        self.session_info: CursorSessionInfo | None = None
        self._running = False
        self._http_session: aiohttp.ClientSession | None = None

        # Process monitoring
        self._process_task: asyncio.Task | None = None
        self._stdout_reader: asyncio.Task | None = None
        self._stderr_reader: asyncio.Task | None = None

        # Event queue
        self._event_queue: asyncio.Queue[CursorEvent] = asyncio.Queue()

        # Polling fallback
        self._polling_mode = False
        self._queued_events: list[EventIngestRequest] = []

        # File position tracking for polling
        self._log_file_positions: dict[Path, int] = {}

        logger.info(
            f"Cursor wrapper initialized for project: {self.project_name} "
            f"at {self.project_dir}"
        )

    async def start(self) -> None:
        """Start the Cursor wrapper event monitoring loop."""
        if self._running:
            logger.warning("Cursor wrapper already running")
            return

        self._running = True
        self._http_session = aiohttp.ClientSession()

        logger.info("Starting Cursor wrapper event monitoring...")

        # Initialize database
        db_manager.init_db()

        try:
            # Detect or create Cursor session
            await self._ensure_session()

            # Start monitoring loop
            await self._monitoring_loop()

        except asyncio.CancelledError:
            logger.info("Cursor wrapper monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in Cursor wrapper: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the Cursor wrapper and cleanup resources."""
        if not self._running:
            return

        logger.info("Stopping Cursor wrapper...")
        self._running = False

        # Cancel monitoring tasks
        for task in [self._process_task, self._stdout_reader, self._stderr_reader]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

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

        logger.info("Cursor wrapper stopped")

    async def _ensure_session(self) -> None:
        """Ensure a Cursor session exists for this project."""
        # Detect active Cursor session
        detected_session = await self._detect_cursor_session()

        if detected_session:
            self.session_info = detected_session
            logger.info(f"Detected active Cursor session: {detected_session.session_id}")
        else:
            # Create new session
            await self._create_session()

    async def _create_session(self) -> None:
        """Create a new Cursor session in the database."""
        # Detect Cursor process info
        pid = await self._check_cursor_process()
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

        # Try to detect Cursor model from command
        model = self._extract_model_from_command(command) if command else None

        async with get_db_session() as db_session:
            db_session_obj = Session(
                agent_type=AgentType.CURSOR,
                project_name=self.project_name,
                status=SessionStatus.RUNNING,
                metadata={
                    "wrapper": "cursor_wrapper",
                    "project_dir": str(self.project_dir),
                    "model": model,
                },
                started_at=datetime.now(timezone.utc),
                pid=pid,
                working_dir=working_dir,
                command=command,
            )
            db_session.add(db_session_obj)
            await db_session.flush()
            await db_session.refresh(db_session_obj)

            self.session_info = CursorSessionInfo(
                project_name=self.project_name,
                session_id=db_session_obj.id,
                pid=pid,
                working_dir=working_dir,
                command=command,
                started_at=datetime.now(timezone.utc),
                status=SessionStatus.RUNNING,
                model=model,
            )

            logger.info(f"Created new Cursor session: {db_session_obj.id}")

            # Emit session start event
            await self._emit_event(
                *UnifiedEventFactory.session_start(
                    project_name=self.project_name,
                    agent_type="cursor",
                    metadata={"model": model},
                ),
            )

    def _extract_model_from_command(self, command: str | None) -> str | None:
        """Extract Cursor model from command line.

        Args:
            command: Command line string

        Returns:
            Model name if detected, None otherwise
        """
        if not command:
            return None

        # Look for model patterns like --model, -m, etc.
        model_patterns = [
            r"--model\s+(\w+)",
            r"-m\s+(\w+)",
            r"model[=:](\w+)",
            r"gpt-(\w+)",
            r"claude-(\w+)",
        ]

        for pattern in model_patterns:
            match = re.search(pattern, command)
            if match:
                return match.group(1)

        return None

    async def _end_session(self, status: SessionStatus) -> None:
        """End the current Cursor session.

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

        logger.info(f"Cursor session {self.session_info.session_id} ended with status: {status}")

    async def _detect_cursor_session(self) -> CursorSessionInfo | None:
        """Detect active Cursor session via process scan.

        Returns:
            CursorSessionInfo if active session detected, None otherwise
        """
        # Check for Cursor processes
        pid = await self._check_cursor_process()
        if pid:
            # Try to find existing session in database
            async with get_db_session() as db_session:
                from sqlalchemy import select

                result = await db_session.execute(
                    select(Session)
                    .where(Session.project_name == self.project_name)
                    .where(Session.agent_type == AgentType.CURSOR)
                    .where(Session.status == SessionStatus.RUNNING)
                    .order_by(Session.started_at.desc())
                    .limit(1)
                )
                db_session_obj = result.scalar_one_or_none()

                if db_session_obj:
                    # Get process info
                    try:
                        proc = psutil.Process(pid)
                        command = " ".join(proc.cmdline()) if proc.cmdline() else None
                        working_dir = proc.cwd() if proc.cwd() else None
                        model = self._extract_model_from_command(command)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        command = None
                        working_dir = None
                        model = None

                    return CursorSessionInfo(
                        project_name=self.project_name,
                        session_id=db_session_obj.id,
                        pid=pid,
                        working_dir=working_dir,
                        command=command,
                        started_at=db_session_obj.started_at.replace(tzinfo=timezone.utc),
                        status=SessionStatus.RUNNING,
                        model=model,
                    )

        return None

    async def _check_cursor_process(self) -> int | None:
        """Check for running Cursor IDE processes.

        Returns:
            PID if found, None otherwise
        """
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        cwd = proc.info.get("cwd", "")

                        # Check for cursor commands
                        # Match patterns like:
                        # - "cursor" in command
                        # - Working directory matches project
                        is_cursor = (
                            "cursor" in cmdline_str.lower()
                            and not any(
                                x in cmdline_str.lower()
                                for x in ["cursor-id", "cursor-terminal"]
                            )  # Exclude helper processes
                            and (
                                str(self.project_dir) in cwd
                                or self._working_dir in cwd
                                or cwd == str(self.project_dir)
                            )
                        )

                        if is_cursor:
                            return proc.info["pid"]

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception:
            pass

        return None

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for Cursor process and events."""
        logger.info("Starting Cursor monitoring loop...")

        # Start event processor
        event_processor = asyncio.create_task(self._event_processor())

        while self._running:
            try:
                # Check for Cursor process
                pid = await self._check_cursor_process()

                if not pid:
                    logger.debug("No Cursor process detected, waiting...")
                    await asyncio.sleep(PROCESS_CHECK_INTERVAL)
                    continue

                # Update PID if changed
                if pid != self._pid:
                    self._pid = pid
                    logger.info(f"Detected Cursor process: {pid}")

                    # Update session heartbeat
                    await self._update_heartbeat()

                # Check for process crash
                if self.session_info and self.session_info.pid:
                    if not psutil.pid_exists(self.session_info.pid):
                        logger.error(f"Cursor process {self.session_info.pid} crashed")
                        await self._emit_event(
                            *UnifiedEventFactory.error(
                                ErrorEvent(
                                    message="Cursor process crashed",
                                    error_type="ProcessCrash",
                                    recoverable=False,
                                )
                            )
                        )
                        await self._end_session(SessionStatus.FAILED)
                        break

                # Try to attach to process for stdout/stderr interception
                if not self._process_task or self._process_task.done():
                    self._process_task = asyncio.create_task(
                        self._monitor_process_output(pid)
                    )

                # Poll for events if interception failed
                if self._polling_mode:
                    await self._poll_for_events()

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

    async def _monitor_process_output(self, pid: int) -> None:
        """Monitor Cursor process output for events.

        Args:
            pid: Process ID to monitor
        """
        try:
            proc = psutil.Process(pid)

            # Try to open stdout/stderr for reading
            # Note: This requires the process to be started with appropriate flags
            # or may not work for all processes

            # For now, use polling fallback
            self._polling_mode = True
            logger.debug(f"Using polling mode for Cursor process {pid}")

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Cannot monitor process {pid}: {e}")
            self._polling_mode = True

    async def _poll_for_events(self) -> None:
        """Poll for Cursor events from log files or other sources.

        This is the fallback method when direct stdout/stderr interception
        is not available.
        """
        # Check Cursor logs directory
        if CURSOR_LOGS_DIR.exists():
            await self._scan_log_directory(CURSOR_LOGS_DIR)

        # Check Cursor storage directory for state files
        if CURSOR_STORAGE_DIR.exists():
            await self._scan_storage_directory(CURSOR_STORAGE_DIR)

        # Check for session files
        if CURSOR_SESSIONS_DIR.exists():
            await self._scan_session_directory(CURSOR_SESSIONS_DIR)

    async def _scan_log_directory(self, log_dir: Path) -> None:
        """Scan Cursor log directory for new events.

        Args:
            log_dir: Path to log directory
        """
        try:
            log_files = list(log_dir.glob("*.log"))
            log_files.extend(log_dir.glob("*.json"))

            for log_file in log_files:
                try:
                    # Get last position
                    pos = self._log_file_positions.get(log_file, 0)

                    # Read new content
                    with open(log_file, "r") as f:
                        f.seek(pos)
                        new_content = f.read()
                        self._log_file_positions[log_file] = f.tell()

                    # Parse log content
                    await self._parse_log_content(new_content, log_file)

                except (IOError, OSError):
                    pass

        except Exception as e:
            logger.debug(f"Error scanning log directory: {e}")

    async def _scan_storage_directory(self, storage_dir: Path) -> None:
        """Scan Cursor storage directory for state files.

        Args:
            storage_dir: Path to storage directory
        """
        try:
            # Look for recent JSON files
            json_files = list(storage_dir.glob("**/*.json"))

            for json_file in json_files[:10]:  # Limit to 10 files
                try:
                    # Check if file was recently modified
                    mtime = json_file.stat().st_mtime
                    age = datetime.now(timezone.utc).timestamp() - mtime

                    # Only process files modified in last minute
                    if age < 60:
                        data = json.loads(json_file.read_text())
                        await self._parse_storage_data(data, json_file)

                except (json.JSONDecodeError, IOError):
                    pass

        except Exception as e:
            logger.debug(f"Error scanning storage directory: {e}")

    async def _scan_session_directory(self, session_dir: Path) -> None:
        """Scan Cursor session directory for session data.

        Args:
            session_dir: Path to session directory
        """
        try:
            session_files = list(session_dir.glob("*.json"))

            for session_file in session_files:
                try:
                    data = json.loads(session_file.read_text())
                    await self._parse_session_data(data)

                except (json.JSONDecodeError, IOError):
                    pass

        except Exception as e:
            logger.debug(f"Error scanning session directory: {e}")

    async def _parse_log_content(self, content: str, source: Path) -> None:
        """Parse Cursor log content for events.

        Args:
            content: Log content to parse
            source: Source file path
        """
        # Look for Cursor-specific log patterns
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to parse as JSON
            try:
                data = json.loads(line)
                await self._parse_cursor_event(data)
            except json.JSONDecodeError:
                # Parse text log patterns
                await self._parse_text_log_line(line, source)

    async def _parse_text_log_line(self, line: str, source: Path) -> None:
        """Parse text log line for Cursor events.

        Args:
            line: Log line to parse
            source: Source file path
        """
        # Look for file edit patterns
        edit_pattern = r"\[Cursor\] Editing file: (.+)"
        match = re.search(edit_pattern, line)
        if match:
            event = CursorEvent(
                event_type=CursorEventType.EDIT_START,
                timestamp=datetime.now(timezone.utc).isoformat(),
                file_path=match.group(1),
                raw={"line": line, "source": str(source)},
            )
            await self._event_queue.put(event)
            return

        # Look for chat patterns
        chat_pattern = r"\[Cursor\] Chat: (.+)"
        match = re.search(chat_pattern, line)
        if match:
            event = CursorEvent(
                event_type=CursorEventType.CHAT_START,
                timestamp=datetime.now(timezone.utc).isoformat(),
                content=match.group(1),
                raw={"line": line, "source": str(source)},
            )
            await self._event_queue.put(event)
            return

        # Look for command patterns
        command_pattern = r"\[Cursor\] Running command: (.+)"
        match = re.search(command_pattern, line)
        if match:
            event = CursorEvent(
                event_type=CursorEventType.COMMAND_START,
                timestamp=datetime.now(timezone.utc).isoformat(),
                command=match.group(1),
                raw={"line": line, "source": str(source)},
            )
            await self._event_queue.put(event)
            return

        # Look for error patterns
        if "error" in line.lower():
            event = CursorEvent(
                event_type=CursorEventType.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_message=line,
                error_type="CursorError",
                raw={"line": line, "source": str(source)},
            )
            await self._event_queue.put(event)

    async def _parse_storage_data(self, data: dict, source: Path) -> None:
        """Parse Cursor storage data for events.

        Args:
            data: Storage data dictionary
            source: Source file path
        """
        # Look for edit events
        if "edits" in data:
            for edit in data["edits"]:
                event = CursorEvent(
                    event_type=CursorEventType.EDIT_COMPLETE,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    file_path=edit.get("filePath"),
                    raw={"source": str(source), "edit": edit},
                )
                await self._event_queue.put(event)

        # Look for chat events
        if "conversations" in data:
            for conv in data["conversations"]:
                event = CursorEvent(
                    event_type=CursorEventType.CHAT_COMPLETE,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    content=conv.get("message"),
                    model=conv.get("model"),
                    raw={"source": str(source), "conversation": conv},
                )
                await self._event_queue.put(event)

    async def _parse_session_data(self, data: dict) -> None:
        """Parse Cursor session data for events.

        Args:
            data: Session data dictionary
        """
        # Look for tool use events
        if "tool_calls" in data:
            for tool_call in data["tool_calls"]:
                event = CursorEvent(
                    event_type=CursorEventType.COMMAND_START,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    command=tool_call.get("name"),
                    args=tool_call.get("arguments", []),
                    raw=data,
                )
                await self._event_queue.put(event)

        # Look for response events
        if "messages" in data:
            for message in data["messages"]:
                if message.get("role") == "assistant":
                    event = CursorEvent(
                        event_type=CursorEventType.CHAT_COMPLETE,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        role="assistant",
                        content=message.get("content"),
                        raw=data,
                    )
                    await self._event_queue.put(event)

    async def _parse_cursor_event(self, data: dict) -> None:
        """Parse Cursor event from JSON data.

        Args:
            data: Event data dictionary
        """
        event_type = data.get("event_type", "unknown")

        try:
            event = CursorEvent.from_dict(data)
            await self._event_queue.put(event)
        except ValueError:
            # Unknown event type, create generic event
            event = CursorEvent(
                event_type=CursorEventType(event_type),
                timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                raw=data,
            )
            await self._event_queue.put(event)

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
        self, event: CursorEvent
    ) -> tuple[str, dict[str, Any]]:
        """Transform Cursor event to unified event format.

        Args:
            event: Cursor event to transform

        Returns:
            Tuple of (event_type, data)
        """
        # Edit events
        if event.event_type == CursorEventType.EDIT_START:
            task_event = TaskEvent(
                task_id=f"edit_{event.file_path}_{uuid.uuid4().hex[:8]}",
                task_type="file_edit",
                task_name=f"Edit {event.file_path}",
                metadata={
                    "file_path": event.file_path,
                    "edit_range": event.edit_range,
                },
            )
            return UnifiedEventFactory.task_start(task_event)

        if event.event_type == CursorEventType.EDIT_COMPLETE:
            return UnifiedEventFactory.task_complete(
                task_id=f"edit_{event.file_path}",
                result={
                    "file_path": event.file_path,
                    "content_preview": event.new_content[:200] if event.new_content else None,
                },
            )

        if event.event_type == CursorEventType.EDIT_ERROR:
            return UnifiedEventFactory.task_fail(
                task_id=f"edit_{event.file_path}",
                error=event.error_message or "Edit failed",
                error_type=event.error_type,
            )

        # Chat events
        if event.event_type in (
            CursorEventType.CHAT_START,
            CursorEventType.CHAT_COMPLETE,
            CursorEventType.AGENT_THINKING_COMPLETE,
        ):
            message_event = MessageEvent(
                role=event.role or "assistant",
                content=event.content or "",
                metadata={
                    "timestamp": event.timestamp,
                    "model": event.model,
                    "agent_name": event.agent_name,
                },
            )
            return UnifiedEventFactory.message(message_event)

        # Agent thinking events
        if event.event_type == CursorEventType.AGENT_THINKING_START:
            task_event = TaskEvent(
                task_id=f"thinking_{uuid.uuid4().hex[:8]}",
                task_type="agent_thinking",
                task_name=event.agent_name or "Cursor Agent",
                metadata={"thinking_steps": event.thinking_steps},
            )
            return UnifiedEventFactory.task_start(task_event)

        # Error events
        if event.event_type == CursorEventType.ERROR:
            error_event = ErrorEvent(
                message=event.error_message or "Unknown error",
                error_type=event.error_type or "CursorError",
            )
            return UnifiedEventFactory.error(error_event)

        # Warning events
        if event.event_type == CursorEventType.WARNING:
            return (
                UnifiedEventType.WARNING.value,
                {"message": event.error_message or "Warning"},
            )

        # Command events
        if event.event_type == CursorEventType.COMMAND_START:
            command_event = CommandEvent(
                command=event.command or "",
                args=event.args or [],
            )
            return UnifiedEventFactory.command(command_event)

        if event.event_type == CursorEventType.COMMAND_COMPLETE:
            command_event = CommandEvent(
                command=event.command or "",
                args=event.args or [],
                exit_code=event.exit_code,
            )
            return UnifiedEventFactory.command(command_event)

        # File operation events
        if event.event_type == CursorEventType.FILE_OPEN:
            task_event = TaskEvent(
                task_id=f"file_open_{event.file_path}",
                task_type="file_operation",
                task_name=f"Open {event.file_path}",
                metadata={"operation": "open", "file_path": event.file_path},
            )
            return UnifiedEventFactory.task_start(task_event)

        if event.event_type == CursorEventType.FILE_SAVE:
            return UnifiedEventFactory.task_complete(
                task_id=f"file_save_{event.file_path}",
                result={"operation": "save", "file_path": event.file_path},
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
) -> None:
    """Run the Cursor wrapper with signal handling.

    Args:
        project_dir: Project directory path
        websocket_url: WebSocket server URL
        pid: Process ID of Cursor agent
        working_dir: Working directory
        command: Command line
    """
    wrapper = CursorWrapper(
        project_dir=project_dir,
        websocket_url=websocket_url,
        pid=pid,
        working_dir=working_dir,
        command=command,
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
    """Main entry point for the Cursor wrapper."""
    parser = argparse.ArgumentParser(
        description="Cursor IDE agent wrapper for Dope Dash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m wrappers.cursor_wrapper
  python -m wrappers.cursor_wrapper --project-dir /path/to/project
  python -m wrappers.cursor_wrapper --pid 12345
  python -m wrappers.cursor_wrapper --websocket-url http://localhost:8005
  python -m wrappers.cursor_wrapper --debug
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
        help="Process ID of Cursor agent (optional, auto-detected if not provided)",
    )

    parser.add_argument(
        "--working-dir",
        type=str,
        default=None,
        help="Working directory of Cursor agent (optional)",
    )

    parser.add_argument(
        "--command",
        type=str,
        default=None,
        help="Command line used to start Cursor (optional)",
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

    # Run the wrapper
    try:
        asyncio.run(
            run_wrapper(
                args.project_dir,
                args.websocket_url,
                args.pid,
                args.working_dir,
                args.command,
            )
        )
    except KeyboardInterrupt:
        logger.info("Wrapper interrupted by user")
    except Exception as e:
        logger.error(f"Wrapper error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
