"""Agent handoff context service based on cli-continues patterns.

This service enables seamless context transfer between agents when
reassigning sessions or when agents need to hand off work.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session


logger = logging.getLogger(__name__)


@dataclass
class ToolSummary:
    """Summary of tool usage by category."""
    category: str
    count: int
    samples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HandoffContext:
    """Context for agent handoff operations."""
    session_id: str
    source_agent_type: str
    source_agent_id: str
    target_agent_type: str
    target_agent_id: str
    summary: str
    tool_summaries: list[ToolSummary]
    files_modified: list[str]
    pending_tasks: list[str]
    decisions: list[str]
    recent_messages: list[dict]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "source_agent_type": self.source_agent_type,
            "source_agent_id": self.source_agent_id,
            "target_agent_type": self.target_agent_type,
            "target_agent_id": self.target_agent_id,
            "summary": self.summary,
            "tool_summaries": [ts.to_dict() for ts in self.tool_summaries],
            "files_modified": self.files_modified,
            "pending_tasks": self.pending_tasks,
            "decisions": self.decisions,
            "recent_messages": self.recent_messages,
            "created_at": self.created_at.isoformat(),
        }


class SummaryCollector:
    """Tracks agent actions during task execution.

    Collects tool usage, file modifications, and activity summaries
    for generating handoff context.
    """

    def __init__(self, max_samples: int = 3):
        """Initialize the summary collector.

        Args:
            max_samples: Maximum number of sample items to keep per category
        """
        self._data: dict[str, dict] = {}
        self._files: set[str] = set()
        self._messages: list[dict] = []
        self._decisions: list[str] = []
        self._pending_tasks: list[str] = []
        self._max_samples = max_samples

    def add(
        self,
        category: str,
        summary: str,
        file_path: str | None = None,
        metadata: dict | None = None
    ) -> None:
        """Add an action to the summary collector.

        Args:
            category: Tool/action category (e.g., "read", "edit", "bash")
            summary: Brief description of the action
            file_path: Optional file path if action modified a file
            metadata: Optional additional metadata
        """
        if category not in self._data:
            self._data[category] = {"count": 0, "samples": []}

        self._data[category]["count"] += 1

        if len(self._data[category]["samples"]) < self._max_samples:
            self._data[category]["samples"].append(summary)

        if file_path:
            self._files.add(file_path)

    def add_message(self, role: str, content: str, timestamp: datetime | None = None) -> None:
        """Add a message to the recent messages log.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            timestamp: Optional timestamp, defaults to now
        """
        self._messages.append({
            "role": role,
            "content": content[:500],  # Truncate long messages
            "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        })

        # Keep only last 10 messages
        if len(self._messages) > 10:
            self._messages = self._messages[-10:]

    def add_decision(self, decision: str) -> None:
        """Add a key decision made during the session.

        Args:
            decision: Description of the decision
        """
        self._decisions.append(decision)

    def add_pending_task(self, task: str) -> None:
        """Add a pending task to be completed.

        Args:
            task: Description of the pending task
        """
        self._pending_tasks.append(task)

    def complete_task(self, task: str) -> None:
        """Mark a pending task as complete.

        Args:
            task: Description of the task to mark complete
        """
        if task in self._pending_tasks:
            self._pending_tasks.remove(task)

    def get_summaries(self) -> list[ToolSummary]:
        """Get all tool summaries.

        Returns:
            List of ToolSummary objects
        """
        return [
            ToolSummary(cat, data["count"], data["samples"])
            for cat, data in self._data.items()
        ]

    def get_files_modified(self) -> list[str]:
        """Get list of modified files.

        Returns:
            List of file paths
        """
        return sorted(list(self._files))

    def get_recent_messages(self) -> list[dict]:
        """Get recent messages.

        Returns:
            List of message dictionaries
        """
        return self._messages.copy()

    def get_decisions(self) -> list[str]:
        """Get key decisions.

        Returns:
            List of decision descriptions
        """
        return self._decisions.copy()

    def get_pending_tasks(self) -> list[str]:
        """Get pending tasks.

        Returns:
            List of pending task descriptions
        """
        return self._pending_tasks.copy()

    def clear(self) -> None:
        """Clear all collected data."""
        self._data.clear()
        self._files.clear()
        self._messages.clear()
        self._decisions.clear()
        self._pending_tasks.clear()


def generate_handoff_markdown(context: HandoffContext) -> str:
    """Generate handoff document in cli-continues format.

    Args:
        context: The handoff context to format

    Returns:
        Markdown-formatted handoff document
    """
    lines = [
        "# Session Handoff Context",
        "",
        "## Session Overview",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Source** | {context.source_agent_type} ({context.source_agent_id}) |",
        f"| **Target** | {context.target_agent_type} ({context.target_agent_id}) |",
        f"| **Session ID** | {context.session_id} |",
        f"| **Created** | {context.created_at.isoformat()} |",
        "",
        "## Summary",
        f"> {context.summary}",
        "",
        "## Tool Activity",
    ]

    for ts in context.tool_summaries:
        samples = " · ".join(ts.samples[:3])
        lines.append(f"- **{ts.category}** (×{ts.count}): {samples}")

    if context.files_modified:
        lines.extend(["", "## Files Modified"])
        for f in context.files_modified:
            lines.append(f"- `{f}`")

    if context.pending_tasks:
        lines.extend(["", "## Pending Tasks"])
        for task in context.pending_tasks:
            lines.append(f"- [ ] {task}")

    if context.decisions:
        lines.extend(["", "## Key Decisions"])
        for decision in context.decisions:
            lines.append(f"- 💭 {decision}")

    if context.recent_messages:
        lines.extend(["", "## Recent Messages"])
        for msg in context.recent_messages[-5:]:  # Last 5 messages
            role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg["role"], "💬")
            content_preview = msg["content"][:100] + ("..." if len(msg["content"]) > 100 else "")
            lines.append(f"- {role_emoji} *{msg['role']}*: {content_preview}")

    lines.extend([
        "",
        "---",
        f"**You are continuing this session from {context.source_agent_type}. Pick up exactly where it left off.**"
    ])

    return "\n".join(lines)


class AgentHandoffService:
    """Service for managing agent handoff operations.

    Provides methods for creating, storing, and retrieving handoff
    contexts when agents transfer work.
    """

    # Maximum age for collectors before cleanup (in seconds)
    MAX_COLLECTOR_AGE_SECONDS = 3600  # 1 hour
    # Maximum number of collectors to keep in memory
    MAX_COLLECTORS = 100
    # Maximum age for handoff files before cleanup (in days)
    MAX_HANDOFF_AGE_DAYS = 30

    def __init__(self, storage_dir: str = "./handoffs"):
        """Initialize the handoff service.

        Args:
            storage_dir: Directory to store handoff documents
        """
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._collectors: dict[str, SummaryCollector] = {}
        self._collector_timestamps: dict[str, datetime] = {}
        # Track last cleanup to avoid doing it on every operation
        self._last_cleanup: datetime | None = None

    def get_collector(self, session_id: str) -> SummaryCollector:
        """Get or create a summary collector for a session.

        Args:
            session_id: The session identifier

        Returns:
            SummaryCollector for the session
        """
        # Cleanup old collectors periodically
        self._cleanup_collectors()

        if session_id not in self._collectors:
            self._collectors[session_id] = SummaryCollector()
        self._collector_timestamps[session_id] = datetime.now(timezone.utc)
        return self._collectors[session_id]

    def clear_collector(self, session_id: str) -> None:
        """Clear and remove a session's collector.

        Args:
            session_id: The session identifier
        """
        if session_id in self._collectors:
            self._collectors[session_id].clear()
            del self._collectors[session_id]
        if session_id in self._collector_timestamps:
            del self._collector_timestamps[session_id]

    def _cleanup_collectors(self) -> None:
        """Remove stale collectors to prevent memory leaks.

        Removes collectors that:
        - Are older than MAX_COLLECTOR_AGE_SECONDS
        - Exceed MAX_COLLECTORS limit (oldest first)
        """
        now = datetime.now(timezone.utc)

        # Remove expired collectors
        expired = [
            sid for sid, ts in self._collector_timestamps.items()
            if (now - ts).total_seconds() > self.MAX_COLLECTOR_AGE_SECONDS
        ]
        for sid in expired:
            self.clear_collector(sid)

        # If still over limit, remove oldest
        if len(self._collectors) > self.MAX_COLLECTORS:
            sorted_sessions = sorted(
                self._collector_timestamps.items(),
                key=lambda x: x[1]
            )
            excess = len(self._collectors) - self.MAX_COLLECTORS
            for sid, _ in sorted_sessions[:excess]:
                self.clear_collector(sid)

    async def _cleanup_old_handoffs(self) -> int:
        """Remove handoff files older than MAX_HANDOFF_AGE_DAYS.

        Returns:
            Number of handoff files removed
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.MAX_HANDOFF_AGE_DAYS)
        removed = 0

        for json_file in self._storage_dir.glob("handoff-*.json"):
            try:
                # Check file modification time as quick filter
                file_mtime = datetime.fromtimestamp(
                    json_file.stat().st_mtime,
                    tz=timezone.utc
                )
                if file_mtime < cutoff:
                    # Also check the created_at inside the file
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    created_at = self._parse_datetime(data["created_at"])
                    if created_at < cutoff:
                        json_file.unlink()
                        # Also remove the corresponding markdown file
                        md_file = json_file.with_suffix(".md")
                        if md_file.exists():
                            md_file.unlink()
                        removed += 1
                        logger.debug(f"Removed old handoff: {json_file.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup handoff file {json_file}: {e}")

        return removed

    async def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed since last cleanup."""
        now = datetime.now(timezone.utc)

        # Only run cleanup every hour
        if self._last_cleanup and (now - self._last_cleanup).total_seconds() < 3600:
            return

        self._cleanup_collectors()
        removed = await self._cleanup_old_handoffs()
        self._last_cleanup = now

        if removed > 0:
            logger.info(f"Cleaned up {removed} old handoff files")

    async def create_handoff(
        self,
        session_id: str,
        source_agent_type: str,
        source_agent_id: str,
        target_agent_type: str,
        target_agent_id: str,
        summary: str,
    ) -> HandoffContext:
        """Create a handoff context for a session transfer.

        Args:
            session_id: The session being transferred
            source_agent_type: Type of the source agent
            source_agent_id: ID of the source agent
            target_agent_type: Type of the target agent
            target_agent_id: ID of the target agent
            summary: Summary of work done so far

        Returns:
            HandoffContext with collected data
        """
        collector = self.get_collector(session_id)

        context = HandoffContext(
            session_id=session_id,
            source_agent_type=source_agent_type,
            source_agent_id=source_agent_id,
            target_agent_type=target_agent_type,
            target_agent_id=target_agent_id,
            summary=summary,
            tool_summaries=collector.get_summaries(),
            files_modified=collector.get_files_modified(),
            pending_tasks=collector.get_pending_tasks(),
            decisions=collector.get_decisions(),
            recent_messages=collector.get_recent_messages(),
        )

        # Store the handoff
        await self._store_handoff(context)

        # Clear the collector after handoff
        self.clear_collector(session_id)

        logger.info(
            f"Created handoff context for session {session_id}: "
            f"{source_agent_type} → {target_agent_type}"
        )

        return context

    async def _store_handoff(self, context: HandoffContext) -> None:
        """Store a handoff context to disk and database.

        Args:
            context: The handoff context to store
        """
        # Store markdown to disk
        markdown = generate_handoff_markdown(context)
        handoff_file = self._storage_dir / f"handoff-{context.id}.md"
        handoff_file.write_text(markdown, encoding="utf-8")

        # Store JSON to disk
        json_file = self._storage_dir / f"handoff-{context.id}.json"
        json_file.write_text(json.dumps(context.to_dict(), indent=2), encoding="utf-8")

        logger.debug(f"Stored handoff context to {handoff_file}")

    async def get_handoff(self, handoff_id: str) -> Optional[HandoffContext]:
        """Retrieve a handoff context by ID.

        Args:
            handoff_id: The handoff identifier

        Returns:
            HandoffContext if found, None otherwise
        """
        # Sanitize handoff_id to prevent path traversal
        if not handoff_id or not all(c.isalnum() or c == "-" for c in handoff_id):
            logger.warning(f"Invalid handoff_id format: {handoff_id}")
            return None

        json_file = self._storage_dir / f"handoff-{handoff_id}.json"

        if not json_file.exists():
            return None

        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))

            return HandoffContext(
                id=data["id"],
                session_id=data["session_id"],
                source_agent_type=data["source_agent_type"],
                source_agent_id=data["source_agent_id"],
                target_agent_type=data["target_agent_type"],
                target_agent_id=data["target_agent_id"],
                summary=data["summary"],
                tool_summaries=[
                    ToolSummary(**ts) for ts in data["tool_summaries"]
                ],
                files_modified=data["files_modified"],
                pending_tasks=data["pending_tasks"],
                decisions=data["decisions"],
                recent_messages=data["recent_messages"],
                created_at=self._parse_datetime(data["created_at"]),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in handoff {handoff_id}: {e}")
            return None
        except KeyError as e:
            logger.error(f"Missing required field in handoff {handoff_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load handoff {handoff_id}: {e}")
            return None

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse ISO datetime string with fallback for various formats.

        Args:
            dt_str: ISO format datetime string

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If datetime string cannot be parsed
        """
        # Try standard ISO format first
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            pass

        # Try with Z suffix (JavaScript format)
        if dt_str.endswith("Z"):
            try:
                return datetime.fromisoformat(dt_str[:-1] + "+00:00")
            except ValueError:
                pass

        raise ValueError(f"Cannot parse datetime: {dt_str}")

    async def get_handoff_markdown(self, handoff_id: str) -> Optional[str]:
        """Get the markdown representation of a handoff.

        Args:
            handoff_id: The handoff identifier

        Returns:
            Markdown string if found, None otherwise
        """
        md_file = self._storage_dir / f"handoff-{handoff_id}.md"

        if not md_file.exists():
            return None

        return md_file.read_text(encoding="utf-8")

    async def list_handoffs(
        self,
        session_id: str | None = None,
        source_agent_id: str | None = None,
        target_agent_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List handoff contexts with optional filtering.

        Args:
            session_id: Filter by session ID
            source_agent_id: Filter by source agent
            target_agent_id: Filter by target agent
            limit: Maximum number of results

        Returns:
            List of handoff metadata dictionaries
        """
        # Periodically cleanup old handoffs
        await self._maybe_cleanup()

        handoffs = []

        for json_file in self._storage_dir.glob("handoff-*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))

                # Apply filters
                if session_id and data.get("session_id") != session_id:
                    continue
                if source_agent_id and data.get("source_agent_id") != source_agent_id:
                    continue
                if target_agent_id and data.get("target_agent_id") != target_agent_id:
                    continue

                handoffs.append({
                    "id": data["id"],
                    "session_id": data["session_id"],
                    "source_agent_type": data["source_agent_type"],
                    "source_agent_id": data["source_agent_id"],
                    "target_agent_type": data["target_agent_type"],
                    "target_agent_id": data["target_agent_id"],
                    "summary": data["summary"][:100] + "..." if len(data["summary"]) > 100 else data["summary"],
                    "created_at": data["created_at"],
                })
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in handoff file {json_file}: {e}")
            except Exception as e:
                logger.warning(f"Failed to read handoff file {json_file}: {e}")

        # Sort by created_at descending
        handoffs.sort(key=lambda x: x["created_at"], reverse=True)

        return handoffs[:limit]


# Singleton instance
_agent_handoff_service: AgentHandoffService | None = None


def get_agent_handoff_service() -> AgentHandoffService:
    """Get the singleton agent handoff service instance.

    Returns:
        AgentHandoffService instance
    """
    global _agent_handoff_service
    if _agent_handoff_service is None:
        _agent_handoff_service = AgentHandoffService()
    return _agent_handoff_service
