"""Agent registry for managing multi-agent wrapper instances.

This registry provides:
- Agent registration and tracking
- Agent capability discovery
- Agent health monitoring via heartbeats
- Centralized agent lifecycle management
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from app.models.session import AgentType
from app.services.agent_detector import AgentInfo, get_agent_detector


logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Status of a registered agent."""

    REGISTERED = "registered"
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTED = "disconnected"
    TERMINATED = "terminated"


@dataclass
class AgentCapability:
    """Capability description for an agent."""

    name: str
    description: str
    supported: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentHeartbeat:
    """Heartbeat information for an agent."""

    agent_id: str
    timestamp: datetime
    status: AgentStatus
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_stale(self, timeout_seconds: int = 30) -> bool:
        """Check if heartbeat is stale.

        Args:
            timeout_seconds: Seconds before considering heartbeat stale

        Returns:
            True if heartbeat is stale, False otherwise
        """
        elapsed = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return elapsed > timeout_seconds


@dataclass
class RegisteredAgent:
    """Information about a registered agent."""

    agent_id: str
    agent_type: AgentType
    project_name: str
    status: AgentStatus = AgentStatus.REGISTERED
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    tmux_session: str | None = None
    capabilities: list[AgentCapability] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: AgentHeartbeat | None = None
    session_id: uuid.UUID | None = None

    def update_heartbeat(
        self,
        status: AgentStatus,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update the agent's heartbeat.

        Args:
            status: Current agent status
            metadata: Optional additional metadata
        """
        self.last_heartbeat = AgentHeartbeat(
            agent_id=self.agent_id,
            timestamp=datetime.now(timezone.utc),
            status=status,
            metadata=metadata or {},
        )
        self.status = status

    def is_alive(self, heartbeat_timeout: int = 30) -> bool:
        """Check if agent is alive based on heartbeat.

        Args:
            heartbeat_timeout: Seconds before considering agent dead

        Returns:
            True if agent is alive, False otherwise
        """
        if self.last_heartbeat is None:
            # No heartbeat yet, check status
            return self.status != AgentStatus.TERMINATED

        return not self.last_heartbeat.is_stale(heartbeat_timeout)


class AgentRegistry:
    """Registry for managing agent lifecycle and health.

    This class provides a centralized registry for tracking agents,
    monitoring their health via heartbeats, and managing their lifecycle.
    """

    def __init__(self, heartbeat_timeout: int = 30) -> None:
        """Initialize the agent registry.

        Args:
            heartbeat_timeout: Seconds before considering agent dead
        """
        self._agents: dict[str, RegisteredAgent] = {}
        self._project_agents: dict[str, list[str]] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._detector = get_agent_detector()
        self._monitor_task: asyncio.Task[None] | None = None

    async def register_agent(
        self,
        agent_type: AgentType,
        project_name: str,
        pid: int | None = None,
        working_dir: str | None = None,
        command: str | None = None,
        tmux_session: str | None = None,
        capabilities: list[AgentCapability] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RegisteredAgent:
        """Register a new agent.

        Args:
            agent_type: Type of agent
            project_name: Project name
            pid: Process ID (optional)
            working_dir: Working directory (optional)
            command: Command line (optional)
            tmux_session: Tmux session name (optional)
            capabilities: Agent capabilities (optional)
            metadata: Additional metadata (optional)

        Returns:
            RegisteredAgent instance
        """
        # Generate unique agent ID
        agent_id = self._generate_agent_id(agent_type, project_name, pid)

        # Create registered agent
        agent = RegisteredAgent(
            agent_id=agent_id,
            agent_type=agent_type,
            project_name=project_name,
            pid=pid,
            working_dir=working_dir,
            command=command,
            tmux_session=tmux_session,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )

        # Store agent
        self._agents[agent_id] = agent

        # Update project index
        if project_name not in self._project_agents:
            self._project_agents[project_name] = []
        self._project_agents[project_name].append(agent_id)

        logger.info(f"Registered agent: {agent_id} ({agent_type.value} for {project_name})")
        return agent

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent ID to unregister
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent not found for unregistration: {agent_id}")
            return

        agent = self._agents[agent_id]

        # Remove from project index
        if agent.project_name in self._project_agents:
            self._project_agents[agent.project_name] = [
                aid for aid in self._project_agents[agent.project_name] if aid != agent_id
            ]

        # Mark as terminated
        agent.status = AgentStatus.TERMINATED

        # Remove from registry
        del self._agents[agent_id]

        logger.info(f"Unregistered agent: {agent_id}")

    def get_agent(self, agent_id: str) -> RegisteredAgent | None:
        """Get an agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            RegisteredAgent if found, None otherwise
        """
        return self._agents.get(agent_id)

    def get_agents_by_project(self, project_name: str) -> list[RegisteredAgent]:
        """Get all agents for a project.

        Args:
            project_name: Project name

        Returns:
            List of registered agents
        """
        agent_ids = self._project_agents.get(project_name, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agents_by_type(self, agent_type: AgentType) -> list[RegisteredAgent]:
        """Get all agents of a specific type.

        Args:
            agent_type: Agent type to filter by

        Returns:
            List of registered agents
        """
        return [
            agent for agent in self._agents.values() if agent.agent_type == agent_type
        ]

    def get_all_agents(self) -> list[RegisteredAgent]:
        """Get all registered agents.

        Returns:
            List of all registered agents
        """
        return list(self._agents.values())

    def get_active_agents(self) -> list[RegisteredAgent]:
        """Get all active (alive) agents.

        Returns:
            List of active agents
        """
        return [
            agent for agent in self._agents.values() if agent.is_alive(self._heartbeat_timeout)
        ]

    async def update_heartbeat(
        self,
        agent_id: str,
        status: AgentStatus,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update heartbeat for an agent.

        Args:
            agent_id: Agent ID
            status: Current status
            metadata: Optional additional metadata

        Returns:
            True if updated, False if agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            logger.warning(f"Heartbeat for unknown agent: {agent_id}")
            return False

        agent.update_heartbeat(status, metadata)
        logger.debug(f"Heartbeat updated for {agent_id}: {status.value}")
        return True

    async def detect_and_register(
        self,
        project_dir: str,
    ) -> list[RegisteredAgent]:
        """Detect and register all agents for a project.

        Args:
            project_dir: Project directory path

        Returns:
            List of newly registered agents
        """
        from pathlib import Path

        project_path = Path(project_dir)

        # Detect agents
        detected = await self._detector.detect_all_agents(project_path)

        registered: list[RegisteredAgent] = []

        for agent_info in detected:
            # Check if already registered
            existing = self._find_agent_by_info(agent_info)
            if existing:
                # Update heartbeat
                await self.update_heartbeat(existing.agent_id, AgentStatus.ACTIVE)
                continue

            # Register new agent
            agent = await self.register_agent(
                agent_type=agent_info.agent_type,
                project_name=agent_info.project_name,
                pid=agent_info.pid,
                working_dir=agent_info.working_dir,
                command=agent_info.command,
                tmux_session=agent_info.tmux_session,
                metadata=agent_info.metadata,
            )

            # Discover capabilities
            await self._discover_capabilities(agent)

            # Update initial heartbeat
            await self.update_heartbeat(agent.agent_id, AgentStatus.ACTIVE)

            registered.append(agent)

        return registered

    async def start_monitoring(self, interval: int = 10) -> None:
        """Start background monitoring of agent health.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitor_task is not None:
            logger.warning("Agent monitoring already started")
            return

        self._monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"Started agent monitoring (interval: {interval}s)")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring of agent health."""
        if self._monitor_task is None:
            return

        self._monitor_task.cancel()
        try:
            await self._monitor_task
        except asyncio.CancelledError:
            pass
        self._monitor_task = None
        logger.info("Stopped agent monitoring")

    async def _monitoring_loop(self, interval: int) -> None:
        """Background monitoring loop for agent health.

        Args:
            interval: Monitoring interval in seconds
        """
        while True:
            try:
                await asyncio.sleep(interval)

                # Check all agents
                for agent in list(self._agents.values()):
                    if not agent.is_alive(self._heartbeat_timeout):
                        logger.warning(f"Agent {agent.agent_id} appears dead (stale heartbeat)")
                        agent.status = AgentStatus.DISCONNECTED

                        # Try to verify with detector
                        if agent.pid:
                            if not await self._detector.is_agent_alive(
                                AgentInfo(
                                    agent_type=agent.agent_type,
                                    project_name=agent.project_name,
                                    pid=agent.pid,
                                    working_dir=agent.working_dir,
                                    command=agent.command,
                                    tmux_session=agent.tmux_session,
                                )
                            ):
                                logger.warning(f"Agent {agent.agent_id} confirmed dead")
                                agent.status = AgentStatus.TERMINATED

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in agent monitoring loop: {e}", exc_info=True)

    def _find_agent_by_info(self, agent_info: AgentInfo) -> RegisteredAgent | None:
        """Find an existing agent by detection info.

        Args:
            agent_info: Agent detection info

        Returns:
            RegisteredAgent if found, None otherwise
        """
        for agent in self._agents.values():
            if (
                agent.agent_type == agent_info.agent_type
                and agent.project_name == agent_info.project_name
            ):
                # Match by PID if available
                if agent_info.pid and agent.pid == agent_info.pid:
                    return agent
                # Match by tmux session if available
                if agent_info.tmux_session and agent.tmux_session == agent_info.tmux_session:
                    return agent

        return None

    def _generate_agent_id(
        self,
        agent_type: AgentType,
        project_name: str,
        pid: int | None = None,
    ) -> str:
        """Generate a unique agent ID.

        Args:
            agent_type: Type of agent
            project_name: Project name
            pid: Process ID (optional)

        Returns:
            Unique agent ID
        """
        parts = [agent_type.value, project_name]
        if pid:
            parts.append(str(pid))
        base = "-".join(parts)

        # Ensure uniqueness
        counter = 0
        agent_id = base
        while agent_id in self._agents:
            counter += 1
            agent_id = f"{base}-{counter}"

        return agent_id

    async def _discover_capabilities(self, agent: RegisteredAgent) -> None:
        """Discover capabilities for an agent.

        Args:
            agent: Agent to discover capabilities for
        """
        # Default capabilities based on agent type
        capability_map: dict[AgentType, list[AgentCapability]] = {
            AgentType.RALPH: [
                AgentCapability("spec_execution", "Execute spec files"),
                AgentCapability("event_streaming", "Stream events to dashboard"),
                AgentCapability("heartbeat_monitoring", "Provide heartbeat status"),
            ],
            AgentType.CLAUDE: [
                AgentCapability("code_generation", "Generate code from prompts"),
                AgentCapability("file_operations", "Read and write files"),
                AgentCapability("terminal_access", "Execute terminal commands"),
            ],
            AgentType.CURSOR: [
                AgentCapability("code_editing", "Edit code in IDE"),
                AgentCapability("ai_assistance", "AI-powered code suggestions"),
                AgentCapability("multi_file_edit", "Edit multiple files simultaneously"),
            ],
            AgentType.TERMINAL: [
                AgentCapability("command_execution", "Execute shell commands"),
                AgentCapability("output_capture", "Capture command output"),
            ],
        }

        agent.capabilities = capability_map.get(agent.agent_type, [])


# Singleton instance
_agent_registry: AgentRegistry | None = None


def get_agent_registry(heartbeat_timeout: int = 30) -> AgentRegistry:
    """Get the singleton agent registry instance.

    Args:
        heartbeat_timeout: Heartbeat timeout in seconds (only used on first call)

    Returns:
        AgentRegistry instance
    """
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry(heartbeat_timeout=heartbeat_timeout)
    return _agent_registry
