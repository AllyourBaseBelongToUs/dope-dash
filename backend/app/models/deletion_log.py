"""Deletion log model for auditing permanent deletions.

This model tracks all permanent deletions for compliance,
debugging, and audit purposes.
"""
import uuid
from typing import Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Index, DateTime, UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DeletionType(str, Enum):
    """Types of deletion reasons."""

    RETENTION = "retention"
    MANUAL = "manual"
    CASCADE = "cascade"


class EntityType(str, Enum):
    """Types of entities that can be deleted."""

    EVENT = "event"
    SESSION = "session"
    SPEC_RUN = "spec_run"
    METRIC_BUCKET = "metric_bucket"


class DeletionLog(Base, TimestampMixin):
    """Database model representing a deletion log entry.

    This table logs all permanent deletions for audit and compliance.

    Attributes:
        id: Unique log entry identifier (UUID).
        entity_type: Type of entity that was deleted.
        entity_id: ID of the deleted entity.
        deletion_type: Reason for deletion (retention, manual, cascade).
        deleted_by: Who initiated the deletion (system, user, scheduler).
        metadata: Additional context about the deletion.
        session_id: Related session ID (for cascade tracking).
        project_name: Project name for easier querying.
    """

    __tablename__ = "deletion_log"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    deletion_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    deleted_by: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        SQLUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    project_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_deletion_log_entity_type", "entity_type"),
        Index("ix_deletion_log_entity_id", "entity_id"),
        Index("ix_deletion_log_deleted_at", "created_at"),
        Index("ix_deletion_log_session_id", "session_id"),
        Index("ix_deletion_log_project_name", "project_name"),
    )


# Pydantic schemas for API
class DeletionLogBase(BaseModel):
    """Base schema for DeletionLog."""

    entity_type: str
    entity_id: uuid.UUID
    deletion_type: str
    deleted_by: str | None = None
    metadata: dict[str, Any] = {}
    session_id: uuid.UUID | None = None
    project_name: str | None = None


class DeletionLogCreate(DeletionLogBase):
    """Schema for creating a new DeletionLog entry."""

    pass


class DeletionLogResponse(DeletionLogBase):
    """Schema for DeletionLog response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
