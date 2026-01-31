"""Session model - aggregates events for overnight runs."""
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Index, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.models.base import Base, TimestampMixinNullable, SoftDeleteMixin


class SessionStatus(str, enum.Enum):
    """Session lifecycle states."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, enum.Enum):
    """Types of agents that can run sessions.

    Primary Agents:
        RALPH: Ralph Inferno - tmux-based spec execution agent
        CLAUDE: Claude Code - CLI-based AI coding assistant
        CURSOR: Cursor IDE - GUI-based AI code editor
        TERMINAL: Terminal session - raw shell session tracking

    Legacy Agents (for backward compatibility):
        CRAWLER: Generic crawler agent
        ANALYZER: Generic analyzer agent
        REPORTER: Generic reporter agent
        TESTER: Generic tester agent
        CUSTOM: Generic custom agent
    """

    # Primary multi-agent types
    RALPH = "ralph"
    CLAUDE = "claude"
    CURSOR = "cursor"
    TERMINAL = "terminal"

    # Legacy types for backward compatibility
    CRAWLER = "crawler"
    ANALYZER = "analyzer"
    REPORTER = "reporter"
    TESTER = "tester"
    CUSTOM = "custom"


class Session(Base, TimestampMixinNullable, SoftDeleteMixin):
    """Database model representing an agent session.

    Sessions aggregate events for overnight runs and are stored
    for 1 year by default.

    Attributes:
        id: Unique session identifier (UUID).
        agent_type: Type of agent that ran this session.
        project_name: Name of the project being processed.
        status: Current status of the session.
        metadata: Additional session metadata (JSON).
        started_at: When the session started.
        ended_at: When the session ended (null if still running).
        deleted_at: Timestamp when record was soft deleted (None if not deleted).
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(AgentType, native_enum=False),
        nullable=False,
        index=True,
    )
    project_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, native_enum=False),
        nullable=False,
        index=True,
        default=SessionStatus.RUNNING,
    )
    # Use 'data' as the column name since 'metadata' is reserved in SQLAlchemy 2.x
    # The 'metadata' attribute name is preserved for Python API compatibility
    # Renamed from 'metadata' to 'meta_data' because 'metadata' is reserved
    # in SQLAlchemy 2.x Declarative API (Base.metadata is the schema metadata)
    # The column name in the database is still 'metadata' for compatibility
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # Agent runtime metadata for multi-agent support
    pid: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    working_dir: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    command: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    tmux_session: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    # Foreign key to Project (optional - sessions can exist without explicit project)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(
        "Project",
        back_populates="sessions",
    )
    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    spec_runs: Mapped[list["SpecRun"]] = relationship(
        "SpecRun",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    metric_buckets: Mapped[list["MetricBucket"]] = relationship(
        "MetricBucket",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_sessions_project_name_status", "project_name", "status"),
        Index("ix_sessions_status_started_at", "status", "started_at"),
    )


# Pydantic schemas for API
class SessionBase(BaseModel):
    """Base schema for Session."""

    agent_type: AgentType
    project_name: str
    status: SessionStatus = SessionStatus.RUNNING
    # Use 'metadata' for the API (maps to 'meta_data' in the model)
    metadata: dict[str, Any] = {}
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    last_heartbeat: str | None = None  # ISO format timestamp
    tmux_session: str | None = None

    class Config:
        """Pydantic config to map field names."""

        populate_by_name = True

    # Map 'metadata' in API to 'meta_data' in model
    @classmethod
    def from_model(cls, session: Session) -> "SessionBase":
        """Create schema from model instance."""
        return cls(
            agent_type=session.agent_type,
            project_name=session.project_name,
            status=session.status,
            metadata=session.meta_data,
            pid=session.pid,
            working_dir=session.working_dir,
            command=session.command,
            last_heartbeat=session.last_heartbeat.isoformat() if session.last_heartbeat else None,
            tmux_session=session.tmux_session,
        )


class SessionCreate(SessionBase):
    """Schema for creating a new Session."""

    pass


class SessionUpdate(BaseModel):
    """Schema for updating a Session."""

    status: SessionStatus | None = None
    metadata: dict[str, Any] | None = None
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    last_heartbeat: str | None = None
    tmux_session: str | None = None

    class Config:
        """Pydantic config to map field names."""

        populate_by_name = True

    def to_model_dict(self) -> dict[str, Any]:
        """Convert to dict for model update (maps metadata to meta_data)."""
        data = self.model_dump(exclude_unset=True)
        if "metadata" in data:
            data["meta_data"] = data.pop("metadata")
        return data


class SessionResponse(SessionBase):
    """Schema for Session response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
    started_at: str | None  # ISO format timestamp
    ended_at: str | None  # ISO format timestamp
