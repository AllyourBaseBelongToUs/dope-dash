"""Project model - portfolio view for multi-project management."""
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Index, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from datetime import datetime

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class ProjectStatus(str, enum.Enum):
    """Project lifecycle states."""

    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPriority(str, enum.Enum):
    """Project priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """Database model representing a project in the portfolio.

    Projects represent the top-level unit of work in the system.
    Each project can have multiple sessions (agent runs) associated with it.

    Attributes:
        id: Unique project identifier (UUID).
        name: Unique project name.
        status: Current status of the project.
        priority: Priority level for resource allocation.
        description: Optional project description.
        progress: Progress percentage (0.0 to 1.0).
        total_specs: Total number of specs in the project.
        completed_specs: Number of completed specs.
        active_agents: Number of currently active agent sessions.
        last_activity_at: Timestamp of last activity on this project.
        metadata: Additional project metadata (JSON).
        deleted_at: Timestamp when record was soft deleted (None if not deleted).
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus, native_enum=False),
        nullable=False,
        index=True,
        default=ProjectStatus.IDLE,
    )
    priority: Mapped[ProjectPriority] = mapped_column(
        SQLEnum(ProjectPriority, native_enum=False),
        nullable=False,
        index=True,
        default=ProjectPriority.MEDIUM,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    progress: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_specs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completed_specs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    active_agents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    control_history: Mapped[list["ProjectControl"]] = relationship(
        "ProjectControl",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(ProjectControl.created_at)",
    )
    command_history: Mapped[list["CommandHistory"]] = relationship(
        "CommandHistory",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(CommandHistory.created_at)",
    )
    state_history: Mapped[list["StateTransition"]] = relationship(
        "StateTransition",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(StateTransition.created_at)",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_projects_status_priority", "status", "priority"),
    )


# Pydantic schemas for API
class ProjectBase(BaseModel):
    """Base schema for Project."""

    name: str
    status: ProjectStatus = ProjectStatus.IDLE
    priority: ProjectPriority = ProjectPriority.MEDIUM
    description: str | None = None
    progress: float = 0.0
    total_specs: int = 0
    completed_specs: int = 0
    active_agents: int = 0
    last_activity_at: str | None = None  # ISO format timestamp
    metadata: dict[str, Any] = {}

    class Config:
        """Pydantic config."""

        populate_by_name = True

    @classmethod
    def from_model(cls, project: Project) -> "ProjectBase":
        """Create schema from model instance."""
        return cls(
            name=project.name,
            status=project.status,
            priority=project.priority,
            description=project.description,
            progress=project.progress,
            total_specs=project.total_specs,
            completed_specs=project.completed_specs,
            active_agents=project.active_agents,
            last_activity_at=project.last_activity_at.isoformat() if project.last_activity_at else None,
            metadata=project.meta_data,
        )


class ProjectCreate(ProjectBase):
    """Schema for creating a new Project."""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a Project."""

    status: ProjectStatus | None = None
    priority: ProjectPriority | None = None
    description: str | None = None
    progress: float | None = None
    total_specs: int | None = None
    completed_specs: int | None = None
    active_agents: int | None = None
    last_activity_at: str | None = None
    metadata: dict[str, Any] | None = None

    class Config:
        """Pydantic config."""

        populate_by_name = True

    def to_model_dict(self) -> dict[str, Any]:
        """Convert to dict for model update (maps metadata to meta_data)."""
        data = self.model_dump(exclude_unset=True)
        if "metadata" in data:
            data["meta_data"] = data.pop("metadata")
        return data


class ProjectResponse(ProjectBase):
    """Schema for Project response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
    deleted_at: str | None = None  # ISO format timestamp
