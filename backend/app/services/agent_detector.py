"""Agent detection service for multi-agent support.

This service provides unified detection and monitoring of different agent types:
- Ralph Inferno: tmux-based spec execution agent
- Claude Code: CLI-based AI coding assistant
- Cursor IDE: GUI-based AI code editor
- Terminal: Raw shell session tracking

Detection methods:
- Tmux session scanning
- Process scanning for agent binaries
- Working directory detection
- PID-based liveness checks
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

from app.models.session import AgentType


logger = logging.getLogger(__name__)


class AgentDetectionMethod(str, Enum):
    """Method used to detect an agent."""

    TMUX_SESSION = "tmux_session"
    PROCESS_SCAN = "process_scan"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass
class AgentInfo:
    """Information about a detected agent."""

    agent_type: AgentType
    project_name: str
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    tmux_session: str | None = None
    detection_method: AgentDetectionMethod = AgentDetectionMethod.UNKNOWN
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessMatchResult:
    """Result of a process matching operation."""

    pid: int
    name: str
    cmdline: list[str]
    working_dir: str | None = None
    command: str | None = None


class AgentDetector:
    """Service for detecting and monitoring active agents.

    This class provides methods to detect different types of agents
    through various detection strategies (tmux sessions, process scanning, etc.).
    """

    # Agent-specific detection patterns
    RALPH_PATTERNS = ["ralph.sh", "ralph", ".ralph"]
    CLAUDE_PATTERNS = ["claude", "claude-code", "anthropic"]
    CURSOR_PATTERNS = ["cursor", "cursor-id"]
    TERMINAL_PATTERNS = ["bash", "zsh", "fish", "nu"]

    # Tmux session name patterns
    TMUX_PATTERNS = {
        AgentType.RALPH: ["ralph", "inferno"],
        AgentType.CLAUDE: ["claude"],
        AgentType.CURSOR: ["cursor"],
        AgentType.TERMINAL: ["term", "terminal"],
    }

    def __init__(self) -> None:
        """Initialize the agent detector."""
        self._detected_agents: dict[str, AgentInfo] = {}

    async def detect_all_agents(
        self,
        project_dir: Path | None = None,
    ) -> list[AgentInfo]:
        """Detect all active agents.

        Args:
            project_dir: Optional project directory to filter agents by.
                        If None, detects agents across all projects.

        Returns:
            List of detected agent information
        """
        detected: list[AgentInfo] = []

        # Scan for tmux sessions
        tmux_agents = await self._scan_tmux_sessions()
        detected.extend(tmux_agents)

        # Scan for processes
        process_agents = await self._scan_processes(project_dir)
        detected.extend(process_agents)

        # Deduplicate by (agent_type, project_name, pid)
        unique_agents: dict[tuple[AgentType, str, int | None], AgentInfo] = {}
        for agent in detected:
            key = (agent.agent_type, agent.project_name, agent.pid)
            # Prefer agents with more information (pid > no pid)
            if key not in unique_agents or agent.pid is not None:
                unique_agents[key] = agent

        result = list(unique_agents.values())

        # Update cache
        for agent in result:
            cache_key = self._get_cache_key(agent)
            self._detected_agents[cache_key] = agent

        logger.debug(f"Detected {len(result)} active agents")
        return result

    async def detect_agent(
        self,
        agent_type: AgentType,
        project_dir: Path,
    ) -> AgentInfo | None:
        """Detect a specific agent type for a project.

        Args:
            agent_type: Type of agent to detect
            project_dir: Project directory to search in

        Returns:
            AgentInfo if detected, None otherwise
        """
        project_name = project_dir.name

        # Check cache first
        cache_key = f"{agent_type.value}:{project_name}"
        if cache_key in self._detected_agents:
            cached = self._detected_agents[cache_key]
            if await self._is_agent_alive(cached):
                return cached
            else:
                del self._detected_agents[cache_key]

        # Try tmux detection
        tmux_info = await self._detect_tmux_agent(agent_type, project_name)
        if tmux_info:
            self._detected_agents[cache_key] = tmux_info
            return tmux_info

        # Try process detection
        process_info = await self._detect_process_agent(agent_type, project_dir)
        if process_info:
            self._detected_agents[cache_key] = process_info
            return process_info

        return None

    async def is_agent_alive(self, agent_info: AgentInfo) -> bool:
        """Check if an agent is still alive.

        Args:
            agent_info: Agent information to check

        Returns:
            True if agent is alive, False otherwise
        """
        return await self._is_agent_alive(agent_info)

    async def _is_agent_alive(self, agent_info: AgentInfo) -> bool:
        """Internal method to check if an agent is still alive.

        Args:
            agent_info: Agent information to check

        Returns:
            True if agent is alive, False otherwise
        """
        # Check PID if available
        if agent_info.pid:
            try:
                if psutil.pid_exists(agent_info.pid):
                    # Verify it's still the same type of process
                    proc = psutil.Process(agent_info.pid)
                    cmdline = proc.cmdline()
                    if cmdline:
                        cmdline_str = " ".join(cmdline).lower()
                        patterns = self._get_patterns_for_agent(agent_info.agent_type)
                        if any(p.lower() in cmdline_str for p in patterns):
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False

        # Check tmux session if available
        if agent_info.tmux_session:
            return await self._tmux_session_exists(agent_info.tmux_session)

        # No definitive way to check - assume alive
        return True

    async def _scan_tmux_sessions(self) -> list[AgentInfo]:
        """Scan for tmux sessions matching agent patterns.

        Returns:
            List of detected agents from tmux sessions
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

            if proc.returncode != 0:
                return []

            sessions = stdout.decode().strip().split("\n")
            detected: list[AgentInfo] = []

            for session in sessions:
                session = session.strip()
                if not session:
                    continue

                # Try to match against agent patterns
                for agent_type, patterns in self.TMUX_PATTERNS.items():
                    if any(pattern in session.lower() for pattern in patterns):
                        # Extract project name from session if possible
                        project_name = self._extract_project_from_session(session)

                        detected.append(
                            AgentInfo(
                                agent_type=agent_type,
                                project_name=project_name or session,
                                tmux_session=session,
                                detection_method=AgentDetectionMethod.TMUX_SESSION,
                                metadata={"tmux_session_name": session},
                            )
                        )
                        break

            return detected

        except (FileNotFoundError, asyncio.CancelledError):
            return []

    async def _scan_processes(
        self,
        project_dir: Path | None = None,
    ) -> list[AgentInfo]:
        """Scan for agent processes.

        Args:
            project_dir: Optional project directory to filter by

        Returns:
            List of detected agents from process scanning
        """
        detected: list[AgentInfo] = []

        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
                try:
                    match = self._match_agent_process(
                        proc.info.get("cmdline", []),
                        proc.info.get("cwd"),
                        project_dir,
                    )
                    if match:
                        # Filter by project directory if specified
                        if project_dir and match.working_dir:
                            try:
                                if Path(match.working_dir).resolve() != project_dir.resolve():
                                    continue
                            except (OSError, ValueError):
                                pass

                        detected.append(
                            AgentInfo(
                                agent_type=match.agent_type,
                                project_name=self._get_project_name_from_path(
                                    match.working_dir
                                )
                                or "unknown",
                                pid=match.pid,
                                working_dir=match.working_dir,
                                command=match.command,
                                detection_method=AgentDetectionMethod.PROCESS_SCAN,
                            )
                        )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception:
            pass

        return detected

    async def _detect_tmux_agent(
        self,
        agent_type: AgentType,
        project_name: str,
    ) -> AgentInfo | None:
        """Detect an agent via tmux session.

        Args:
            agent_type: Type of agent to detect
            project_name: Project name to look for

        Returns:
            AgentInfo if found, None otherwise
        """
        patterns = self.TMUX_PATTERNS.get(agent_type, [])

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

            if proc.returncode != 0:
                return None

            sessions = stdout.decode().strip().split("\n")

            for session in sessions:
                session = session.strip()
                if not session:
                    continue

                # Check if session matches pattern and project
                if any(pattern in session.lower() for pattern in patterns):
                    if project_name.lower() in session.lower():
                        return AgentInfo(
                            agent_type=agent_type,
                            project_name=project_name,
                            tmux_session=session,
                            detection_method=AgentDetectionMethod.TMUX_SESSION,
                            metadata={"tmux_session_name": session},
                        )

        except (FileNotFoundError, asyncio.CancelledError):
            pass

        return None

    async def _detect_process_agent(
        self,
        agent_type: AgentType,
        project_dir: Path,
    ) -> AgentInfo | None:
        """Detect an agent via process scanning.

        Args:
            agent_type: Type of agent to detect
            project_dir: Project directory to search in

        Returns:
            AgentInfo if found, None otherwise
        """
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    cwd = proc.info.get("cwd")

                    if not cmdline:
                        continue

                    match = self._match_agent_process(cmdline, cwd, project_dir)
                    if match and match.agent_type == agent_type:
                        return AgentInfo(
                            agent_type=agent_type,
                            project_name=project_dir.name,
                            pid=match.pid,
                            working_dir=match.working_dir,
                            command=match.command,
                            detection_method=AgentDetectionMethod.PROCESS_SCAN,
                        )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception:
            pass

        return None

    def _match_agent_process(
        self,
        cmdline: list[str],
        cwd: str | None,
        project_dir: Path | None = None,
    ) -> ProcessMatchResult | None:
        """Match a process to an agent type.

        Args:
            cmdline: Process command line
            cwd: Process working directory
            project_dir: Optional project directory for filtering

        Returns:
            ProcessMatchResult if matched, None otherwise
        """
        if not cmdline:
            return None

        cmdline_str = " ".join(cmdline).lower()
        command = " ".join(cmdline)

        # Check each agent type
        for agent_type in AgentType:
            patterns = self._get_patterns_for_agent(agent_type)
            if any(pattern.lower() in cmdline_str for pattern in patterns):
                # Filter by project directory if specified
                if project_dir and cwd:
                    try:
                        if Path(cwd).resolve() != project_dir.resolve():
                            # Check if project_dir is a parent of cwd
                            try:
                                Path(cwd).relative_to(project_dir.resolve())
                            except ValueError:
                                continue
                    except (OSError, ValueError):
                        pass

                return ProcessMatchResult(
                    pid=0,  # Will be filled by caller
                    name=cmdline[0] if cmdline else "",
                    cmdline=cmdline,
                    working_dir=cwd,
                    command=command,
                )

        return None

    def _get_patterns_for_agent(self, agent_type: AgentType) -> list[str]:
        """Get detection patterns for an agent type.

        Args:
            agent_type: Agent type to get patterns for

        Returns:
            List of detection patterns
        """
        patterns_map = {
            AgentType.RALPH: self.RALPH_PATTERNS,
            AgentType.CLAUDE: self.CLAUDE_PATTERNS,
            AgentType.CURSOR: self.CURSOR_PATTERNS,
            AgentType.TERMINAL: self.TERMINAL_PATTERNS,
        }
        return patterns_map.get(agent_type, [])

    def _extract_project_from_session(self, session_name: str) -> str | None:
        """Extract project name from tmux session name.

        Args:
            session_name: Tmux session name

        Returns:
            Extracted project name or None
        """
        # Common patterns: "ralph-project", "claude_myproject", etc.
        parts = session_name.split(["-", "_", "."][0])
        if len(parts) > 1:
            return parts[-1]
        return None

    def _get_project_name_from_path(self, path: str | None) -> str | None:
        """Extract project name from working directory path.

        Args:
            path: Working directory path

        Returns:
            Project name or None
        """
        if not path:
            return None
        try:
            return Path(path).name
        except (OSError, ValueError):
            return None

    def _get_cache_key(self, agent_info: AgentInfo) -> str:
        """Generate a cache key for an agent.

        Args:
            agent_info: Agent information

        Returns:
            Cache key string
        """
        parts = [agent_info.agent_type.value, agent_info.project_name]
        if agent_info.pid:
            parts.append(str(agent_info.pid))
        if agent_info.tmux_session:
            parts.append(agent_info.tmux_session)
        return ":".join(parts)

    async def _tmux_session_exists(self, session_name: str) -> bool:
        """Check if a tmux session exists.

        Args:
            session_name: Tmux session name to check

        Returns:
            True if session exists, False otherwise
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
                return session_name in sessions

        except (FileNotFoundError, asyncio.CancelledError):
            pass

        return False


# Singleton instance
_agent_detector: AgentDetector | None = None


def get_agent_detector() -> AgentDetector:
    """Get the singleton agent detector instance.

    Returns:
        AgentDetector instance
    """
    global _agent_detector
    if _agent_detector is None:
        _agent_detector = AgentDetector()
    return _agent_detector
