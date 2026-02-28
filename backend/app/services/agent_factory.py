"""Agent factory for creating wrapper instances.

This factory provides:
- Dynamic wrapper instantiation based on agent type
- Wrapper lifecycle management
- Unified interface for all agent wrappers
"""
from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.models.session import AgentType


logger = logging.getLogger(__name__)


class BaseAgentWrapper(ABC):
    """Abstract base class for agent wrappers.

    All agent wrappers must implement this interface to ensure
    consistent behavior across different agent types.
    """

    def __init__(
        self,
        project_dir: Path,
        websocket_url: str = "http://localhost:8005",
    ) -> None:
        """Initialize the wrapper.

        Args:
            project_dir: Path to the project directory
            websocket_url: URL of the WebSocket server for event ingestion
        """
        self.project_dir = project_dir
        self.websocket_url = websocket_url
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start the wrapper event monitoring loop."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the wrapper and cleanup resources."""

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the agent type for this wrapper."""

    @property
    def is_running(self) -> bool:
        """Check if the wrapper is running."""
        return self._running

    async def send_control(
        self,
        control: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Send a control command to the agent.

        This method can be overridden by wrapper implementations to handle
        control commands like pause, resume, stop, skip, retry, restart.

        Args:
            control: Control command (pause, resume, stop, skip, retry, restart)
            metadata: Optional metadata for the control command

        Returns:
            True if control was sent successfully, False otherwise
        """
        # Default implementation does nothing
        # Subclasses can override to implement actual control handling
        return False


class AgentFactory:
    """Factory for creating agent wrapper instances.

    This factory handles dynamic instantiation of wrapper classes
    based on the agent type, providing a unified interface for
    all agent types.
    """

    # Wrapper class mapping
    WRAPPER_CLASSES: dict[AgentType, type[BaseAgentWrapper] | str] = {
        AgentType.RALPH: "wrappers.ralph_wrapper:RalphWrapper",
        AgentType.CLAUDE: "wrappers.claude_wrapper:ClaudeWrapper",
        AgentType.CURSOR: "wrappers.cursor_wrapper:CursorWrapper",
        AgentType.TERMINAL: "wrappers.terminal_wrapper:TerminalWrapper",
        # Legacy types map to custom wrapper
        AgentType.CUSTOM: "wrappers.base_wrapper:BaseAgentWrapper",
    }

    _instance: "AgentFactory | None" = None
    _wrapper_cache: dict[AgentType, type[BaseAgentWrapper]] = {}

    def __new__(cls) -> "AgentFactory":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def create_wrapper(
        self,
        agent_type: AgentType,
        project_dir: Path,
        websocket_url: str = "http://localhost:8005",
        **kwargs: Any,
    ) -> BaseAgentWrapper:
        """Create a wrapper instance for the specified agent type.

        Args:
            agent_type: Type of agent to create wrapper for
            project_dir: Path to the project directory
            websocket_url: URL of the WebSocket server for event ingestion
            **kwargs: Additional arguments to pass to the wrapper

        Returns:
            Wrapper instance

        Raises:
            ValueError: If agent type is not supported
        """
        wrapper_class = self._get_wrapper_class(agent_type)

        try:
            wrapper = wrapper_class(
                project_dir=project_dir,
                websocket_url=websocket_url,
                **kwargs,
            )
            logger.info(f"Created {agent_type.value} wrapper for {project_dir}")
            return wrapper

        except Exception as e:
            logger.error(f"Failed to create {agent_type.value} wrapper: {e}", exc_info=True)
            raise

    def create_wrapper_from_detection(
        self,
        agent_type: AgentType,
        project_dir: Path,
        pid: int | None = None,
        working_dir: str | None = None,
        command: str | None = None,
        tmux_session: str | None = None,
        websocket_url: str = "http://localhost:8005",
        **kwargs: Any,
    ) -> BaseAgentWrapper:
        """Create a wrapper instance from detection information.

        Args:
            agent_type: Type of agent
            project_dir: Path to the project directory
            pid: Process ID
            working_dir: Working directory
            command: Command line
            tmux_session: Tmux session name
            websocket_url: URL of the WebSocket server
            **kwargs: Additional arguments

        Returns:
            Wrapper instance
        """
        # Add detection metadata to kwargs
        detection_kwargs = {
            "pid": pid,
            "working_dir": working_dir,
            "command": command,
            "tmux_session": tmux_session,
        }
        detection_kwargs.update(kwargs)

        return self.create_wrapper(
            agent_type=agent_type,
            project_dir=project_dir,
            websocket_url=websocket_url,
            **detection_kwargs,
        )

    def register_wrapper_class(
        self,
        agent_type: AgentType,
        wrapper_class: type[BaseAgentWrapper] | str,
    ) -> None:
        """Register a custom wrapper class for an agent type.

        Args:
            agent_type: Agent type to register wrapper for
            wrapper_class: Wrapper class or import path (module:class)
        """
        self.WRAPPER_CLASSES[agent_type] = wrapper_class
        # Clear cache to force reload
        self._wrapper_cache.pop(agent_type, None)
        logger.info(f"Registered wrapper class for {agent_type.value}")

    def get_supported_agent_types(self) -> list[AgentType]:
        """Get list of supported agent types.

        Returns:
            List of AgentType values that have registered wrappers
        """
        return list(self.WRAPPER_CLASSES.keys())

    def is_agent_type_supported(self, agent_type: AgentType) -> bool:
        """Check if an agent type is supported.

        Args:
            agent_type: Agent type to check

        Returns:
            True if supported, False otherwise
        """
        return agent_type in self.WRAPPER_CLASSES

    def _get_wrapper_class(self, agent_type: AgentType) -> type[BaseAgentWrapper]:
        """Get the wrapper class for an agent type.

        Args:
            agent_type: Agent type to get wrapper for

        Returns:
            Wrapper class

        Raises:
            ValueError: If agent type is not supported
        """
        if agent_type not in self.WRAPPER_CLASSES:
            raise ValueError(f"Unsupported agent type: {agent_type}")

        # Check cache first
        if agent_type in self._wrapper_cache:
            return self._wrapper_cache[agent_type]

        # Import the wrapper class
        wrapper_spec = self.WRAPPER_CLASSES[agent_type]

        if isinstance(wrapper_spec, str):
            # Parse import path (module:class)
            try:
                module_path, class_name = wrapper_spec.split(":")
                module = importlib.import_module(module_path)
                wrapper_class = getattr(module, class_name)
            except (ImportError, AttributeError, ValueError) as e:
                logger.error(f"Failed to import wrapper class {wrapper_spec}: {e}")
                # Return a base wrapper as fallback
                return self._get_fallback_wrapper(agent_type)
        else:
            wrapper_class = wrapper_spec

        # Cache the class
        self._wrapper_cache[agent_type] = wrapper_class
        return wrapper_class

    def _get_fallback_wrapper(self, agent_type: AgentType) -> type[BaseAgentWrapper]:
        """Get a fallback wrapper for unsupported agent types.

        Args:
            agent_type: Agent type that needs fallback

        Returns:
            Fallback wrapper class
        """
        logger.warning(f"Using fallback wrapper for {agent_type.value}")

        # Create a simple fallback wrapper
        class FallbackWrapper(BaseAgentWrapper):
            """Fallback wrapper for unsupported agent types."""

            def __init__(
                self,
                project_dir: Path,
                websocket_url: str = "http://localhost:8005",
                **kwargs: Any,
            ) -> None:
                super().__init__(project_dir, websocket_url)
                self._agent_type = agent_type
                self._kwargs = kwargs

            async def start(self) -> None:
                """Start the fallback wrapper."""
                self._running = True
                logger.info(f"Fallback wrapper started for {agent_type.value}")

            async def stop(self) -> None:
                """Stop the fallback wrapper."""
                self._running = False
                logger.info(f"Fallback wrapper stopped for {agent_type.value}")

            @property
            def agent_type(self) -> AgentType:
                """Return the agent type."""
                return self._agent_type

        return FallbackWrapper


# Singleton instance
_agent_factory: AgentFactory | None = None


def get_agent_factory() -> AgentFactory:
    """Get the singleton agent factory instance.

    Returns:
        AgentFactory instance
    """
    if _agent_factory is None:
        _agent_factory = AgentFactory()
    return _agent_factory
