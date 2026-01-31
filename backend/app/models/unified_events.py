"""Unified event schema for multi-agent support.

This module defines the standard event types and schemas that all agents
(Ralph, Claude, Cursor, Terminal) should use for consistent event reporting.

Events are structured with:
- event_type: Standard type identifier
- data: JSON payload with event-specific fields
- agent_metadata: Optional agent-specific context
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class UnifiedEventType(str, Enum):
    """Standard event types for all agents.

    Lifecycle Events:
        SESSION_START: Agent session started
        SESSION_END: Agent session ended
        HEARTBEAT: Agent liveness indicator

    Progress Events:
        TASK_START: A task/spec/operation started
        TASK_COMPLETE: A task/spec/operation completed successfully
        TASK_FAIL: A task/spec/operation failed
        PROGRESS: Generic progress update

    Error Events:
        ERROR: Agent encountered an error
        WARNING: Agent encountered a warning

    Communication Events:
        MESSAGE: Agent sent or received a message
        COMMAND: Agent executed a command

    State Events:
        STATE_CHANGE: Agent state changed (e.g., running, paused)
        CAPABILITY_DISCOVERY: Agent reported its capabilities
    """

    # Lifecycle events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    HEARTBEAT = "heartbeat"

    # Progress events
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    PROGRESS = "progress"

    # Error events
    ERROR = "error"
    WARNING = "warning"

    # Communication events
    MESSAGE = "message"
    COMMAND = "command"

    # State events
    STATE_CHANGE = "state_change"
    CAPABILITY_DISCOVERY = "capability_discovery"


@dataclass
class TaskEvent:
    """Event data for task-related events (start, complete, fail).

    Attributes:
        task_id: Unique identifier for the task
        task_type: Type of task (e.g., "spec", "atom", "iteration")
        task_name: Human-readable task name
        progress: Optional progress percentage (0-100)
        metadata: Optional task-specific metadata
    """

    task_id: str
    task_type: str
    task_name: str
    progress: int | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "task_name": self.task_name,
            "progress": self.progress,
            "metadata": self.metadata or {},
        }


@dataclass
class ErrorEvent:
    """Event data for error and warning events.

    Attributes:
        message: Error message
        error_type: Type/class of error
        stack_trace: Optional stack trace
        context: Additional error context
        recoverable: Whether the error is recoverable
    """

    message: str
    error_type: str
    stack_trace: str | None = None
    context: dict[str, Any] | None = None
    recoverable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "message": self.message,
            "error_type": self.error_type,
            "stack_trace": self.stack_trace,
            "context": self.context or {},
            "recoverable": self.recoverable,
        }


@dataclass
class MessageEvent:
    """Event data for message events.

    Attributes:
        role: Message role (user, assistant, system, error)
        content: Message content
        metadata: Optional message metadata (tokens, model, etc.)
    """

    role: str
    content: str
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata or {},
        }


@dataclass
class CommandEvent:
    """Event data for command execution events.

    Attributes:
        command: Command that was executed
        args: Command arguments
        exit_code: Process exit code (None if still running)
        duration: Execution duration in seconds
        stdout: Standard output (optional, can be large)
        stderr: Standard error (optional, can be large)
    """

    command: str
    args: list[str]
    exit_code: int | None = None
    duration: float | None = None
    stdout: str | None = None
    stderr: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "command": self.command,
            "args": self.args,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass
class StateChangeEvent:
    """Event data for agent state changes.

    Attributes:
        old_state: Previous agent state
        new_state: New agent state
        reason: Reason for state change
    """

    old_state: str
    new_state: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "old_state": self.old_state,
            "new_state": self.new_state,
            "reason": self.reason,
        }


@dataclass
class CapabilityDiscoveryEvent:
    """Event data for agent capability discovery.

    Attributes:
        capabilities: List of agent capabilities
        version: Agent version
        metadata: Additional agent metadata
    """

    capabilities: list[str]
    version: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "capabilities": self.capabilities,
            "version": self.version,
            "metadata": self.metadata or {},
        }


class UnifiedEventFactory:
    """Factory for creating unified events.

    This class provides convenience methods for creating properly
    structured events that conform to the unified event schema.
    """

    @staticmethod
    def session_start(
        project_name: str,
        agent_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a session_start event.

        Args:
            project_name: Name of the project
            agent_type: Type of agent
            metadata: Optional additional metadata

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.SESSION_START.value,
            {
                "project_name": project_name,
                "agent_type": agent_type,
                "metadata": metadata or {},
            },
        )

    @staticmethod
    def session_end(
        status: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a session_end event.

        Args:
            status: Final session status
            reason: Optional reason for ending
            metadata: Optional additional metadata

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.SESSION_END.value,
            {
                "status": status,
                "reason": reason,
                "metadata": metadata or {},
            },
        )

    @staticmethod
    def heartbeat(
        pid: int | None = None,
        memory_usage: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a heartbeat event.

        Args:
            pid: Process ID
            memory_usage: Memory usage in bytes
            metadata: Optional additional metadata

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.HEARTBEAT.value,
            {
                "pid": pid,
                "memory_usage": memory_usage,
                "metadata": metadata or {},
            },
        )

    @staticmethod
    def task_start(event: TaskEvent) -> tuple[str, dict[str, Any]]:
        """Create a task_start event.

        Args:
            event: Task event data

        Returns:
            Tuple of (event_type, data)
        """
        return UnifiedEventType.TASK_START.value, event.to_dict()

    @staticmethod
    def task_complete(
        task_id: str,
        result: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a task_complete event.

        Args:
            task_id: Task identifier
            result: Optional task result

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.TASK_COMPLETE.value,
            {
                "task_id": task_id,
                "result": result or {},
            },
        )

    @staticmethod
    def task_fail(
        task_id: str,
        error: str,
        error_type: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a task_fail event.

        Args:
            task_id: Task identifier
            error: Error message
            error_type: Optional error type

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.TASK_FAIL.value,
            {
                "task_id": task_id,
                "error": error,
                "error_type": error_type,
            },
        )

    @staticmethod
    def progress(
        task_id: str,
        progress: int,
        message: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a progress event.

        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            message: Optional progress message

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.PROGRESS.value,
            {
                "task_id": task_id,
                "progress": progress,
                "message": message,
            },
        )

    @staticmethod
    def error(event: ErrorEvent) -> tuple[str, dict[str, Any]]:
        """Create an error event.

        Args:
            event: Error event data

        Returns:
            Tuple of (event_type, data)
        """
        return UnifiedEventType.ERROR.value, event.to_dict()

    @staticmethod
    def message(event: MessageEvent) -> tuple[str, dict[str, Any]]:
        """Create a message event.

        Args:
            event: Message event data

        Returns:
            Tuple of (event_type, data)
        """
        return UnifiedEventType.MESSAGE.value, event.to_dict()

    @staticmethod
    def command(event: CommandEvent) -> tuple[str, dict[str, Any]]:
        """Create a command event.

        Args:
            event: Command event data

        Returns:
            Tuple of (event_type, data)
        """
        return UnifiedEventType.COMMAND.value, event.to_dict()

    @staticmethod
    def state_change(event: StateChangeEvent) -> tuple[str, dict[str, Any]]:
        """Create a state_change event.

        Args:
            event: State change event data

        Returns:
            Tuple of (event_type, data)
        """
        return UnifiedEventType.STATE_CHANGE.value, event.to_dict()

    @staticmethod
    def capability_discovery(
        event: CapabilityDiscoveryEvent,
    ) -> tuple[str, dict[str, Any]]:
        """Create a capability_discovery event.

        Args:
            event: Capability discovery event data

        Returns:
            Tuple of (event_type, data)
        """
        return (
            UnifiedEventType.CAPABILITY_DISCOVERY.value,
            event.to_dict(),
        )
