"""State transition model for project state machine audit trail."""
import uuid
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Index, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.project import ProjectStatus


class StateTransitionSource(str, enum.Enum):
    """Source of a state transition."""

    USER = "user"
    SYSTEM = "system"
    API = "api"
    AUTOMATION = "automation"
    TIMEOUT = "timeout"


class StateTransition(Base, TimestampMixin):
    """Database model for tracking project state transitions.

    Records every state change for audit purposes and analytics.

    Attributes:
        id: Unique transition identifier.
        project_id: Project that transitioned.
        from_state: Previous state (None for initial state).
        to_state: New state.
        transition_reason: Optional reason for the transition.
        source: What triggered the transition.
        initiated_by: User or system that initiated the transition.
        metadata: Additional transition metadata.
        duration_ms: Duration of the previous state in milliseconds.
    """

    __tablename__ = "state_transitions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[ProjectStatus | None] = mapped_column(
        SQLEnum(ProjectStatus, native_enum=False),
        nullable=True,
    )
    to_state: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus, native_enum=False),
        nullable=False,
        index=True,
    )
    transition_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    source: Mapped[StateTransitionSource] = mapped_column(
        SQLEnum(StateTransitionSource, native_enum=False),
        nullable=False,
        default=StateTransitionSource.SYSTEM,
        index=True,
    )
    initiated_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="system",
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Relationship
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="state_history",
    )

    __table_args__ = (
        Index("ix_state_transitions_project_created", "project_id", "created_at"),
    )
