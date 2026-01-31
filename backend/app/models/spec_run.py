"""SpecRun model - individual spec execution tracking."""
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base, TimestampMixinNullable


class SpecRunStatus(str, enum.Enum):
    """Spec execution lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SpecRun(Base, TimestampMixinNullable):
    """Database model representing an individual spec execution.

    Tracks the execution of individual specs within a session.

    Attributes:
        id: Unique spec run identifier (UUID).
        session_id: Foreign key to the parent session.
        spec_name: Name of the spec being executed.
        status: Current status of the spec run.
        started_at: When the spec run started.
        completed_at: When the spec run completed (null if still running).
    """

    __tablename__ = "spec_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spec_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    status: Mapped[SpecRunStatus] = mapped_column(
        SQLEnum(SpecRunStatus, native_enum=False),
        nullable=False,
        index=True,
        default=SpecRunStatus.PENDING,
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="spec_runs",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_spec_runs_session_id_spec_name", "session_id", "spec_name"),
        Index("ix_spec_runs_status_started_at", "status", "started_at"),
    )


# Pydantic schemas for API
class SpecRunBase(BaseModel):
    """Base schema for SpecRun."""

    spec_name: str
    status: SpecRunStatus = SpecRunStatus.PENDING


class SpecRunCreate(SpecRunBase):
    """Schema for creating a new SpecRun."""

    session_id: uuid.UUID


class SpecRunUpdate(BaseModel):
    """Schema for updating a SpecRun."""

    status: SpecRunStatus | None = None


class SpecRunResponse(SpecRunBase):
    """Schema for SpecRun response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    started_at: str | None  # ISO format timestamp
    completed_at: str | None  # ISO format timestamp
