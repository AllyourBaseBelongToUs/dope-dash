"""Auto-pause model for tracking automatic project pauses.

This module provides models for:
- Auto-pause configuration per project
- Auto-pause log for audit trail
- Auto-resume tracking
"""
import uuid
import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AutoPauseTrigger(str, enum.Enum):
    """Trigger types for auto-pause."""

    QUOTA_THRESHOLD = "quota_threshold"  # Paused due to quota threshold
    QUOTA_EXCEEDED = "quota_exceeded"    # Paused due to quota exceeded
    MANUAL_OVERRIDE = "manual_override"   # Manual override triggered


class AutoPauseStatus(str, enum.Enum):
    """Status of auto-pause actions."""

    PENDING = "pending"          # Pause pending execution
    PAUSED = "paused"            # Project has been paused
    RESUMED = "resumed"          # Project was auto-resumed
    OVERRIDDEN = "overridden"    # Manual override applied
    CANCELLED = "cancelled"      # Pause was cancelled


class AutoPauseLog(Base, TimestampMixin):
    """Database model for tracking auto-pause actions.

    Records every auto-pause event for audit and analytics purposes.

    Attributes:
        id: Unique log identifier (UUID).
        project_id: Project that was auto-paused.
        trigger: What triggered the auto-pause.
        status: Current status of the auto-pause.
        threshold_percent: Quota percentage at trigger time.
        priority_at_pause: Project priority when paused.
        paused_at: When the project was paused.
        resumed_at: When the project was resumed (if applicable).
        override_by: User who applied manual override (if applicable).
        override_at: When manual override was applied (if applicable).
        metadata: Additional metadata (JSON).
    """

    __tablename__ = "auto_pause_log"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger: Mapped[AutoPauseTrigger] = mapped_column(
        SQLEnum(AutoPauseTrigger, native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[AutoPauseStatus] = mapped_column(
        SQLEnum(AutoPauseStatus, native_enum=False),
        nullable=False,
        default=AutoPauseStatus.PENDING,
        index=True,
    )
    threshold_percent: Mapped[float] = mapped_column(
        Integer,
        nullable=False,
        comment="Quota percentage at trigger time",
    )
    priority_at_pause: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Project priority when paused",
    )
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    override_by: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User who applied manual override",
    )
    override_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="auto_pause_log",
    )

    def mark_paused(self) -> None:
        """Mark the auto-pause as executed."""
        self.status = AutoPauseStatus.PAUSED
        self.paused_at = datetime.now(timezone.utc)

    def mark_resumed(self) -> None:
        """Mark the project as auto-resumed."""
        self.status = AutoPauseStatus.RESUMED
        self.resumed_at = datetime.now(timezone.utc)

    def mark_overridden(self, override_by: str) -> None:
        """Mark the auto-pause as manually overridden."""
        self.status = AutoPauseStatus.OVERRIDDEN
        self.override_by = override_by
        self.override_at = datetime.now(timezone.utc)


# Add relationship to Project (will be imported at end)
from app.models.project import Project


# Pydantic schemas for API
class AutoPauseSettings(BaseModel):
    """Auto-pause settings for a project."""

    enabled: bool = True
    threshold_percent: float = 95.0  # Default to 95%
    auto_resume: bool = True  # Auto-resume when quota resets
    warning_threshold: float = 80.0  # Warning at 80%


class AutoPauseLogResponse(BaseModel):
    """Schema for AutoPauseLog response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    trigger: AutoPauseTrigger
    status: AutoPauseStatus
    threshold_percent: float
    priority_at_pause: str
    paused_at: datetime | None
    resumed_at: datetime | None
    override_by: str | None
    override_at: datetime | None
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AutoPauseLogListResponse(BaseModel):
    """Schema for auto-pause log list response."""

    items: list[AutoPauseLogResponse]
    total: int


class AutoPauseStatusResponse(BaseModel):
    """Schema for auto-pause status response."""

    enabled: bool
    current_threshold: float
    warning_threshold: float
    auto_resume_enabled: bool
    last_pause_at: datetime | None
    last_resume_at: datetime | None
    total_pauses: int
    total_resumes: int


# Add back-reference to Project
Project.auto_pause_log = relationship(
    "AutoPauseLog",
    back_populates="project",
    cascade="all, delete-orphan",
    order_by="desc(AutoPauseLog.created_at)",
)


__all__ = [
    # Enums
    "AutoPauseTrigger",
    "AutoPauseStatus",
    # Models
    "AutoPauseLog",
    # Schemas
    "AutoPauseSettings",
    "AutoPauseLogResponse",
    "AutoPauseLogListResponse",
    "AutoPauseStatusResponse",
]
