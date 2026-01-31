"""Project control model for tracking project control actions.

This module provides the ProjectControl model which records all control
actions taken on projects (pause, resume, skip, stop, retry, restart).
"""
import uuid
import json
from typing import Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, Text, Enum as SQLEnum, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base, TimestampMixin


class ProjectControlAction(str, enum.Enum):
    """Types of project control actions."""

    PAUSE = "pause"
    RESUME = "resume"
    SKIP = "skip"
    STOP = "stop"
    RETRY = "retry"
    RESTART = "restart"


class ProjectControlStatus(str, enum.Enum):
    """Status of a control action."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ProjectControl(Base, TimestampMixin):
    """Database model representing a project control action.

    Each control action records a command sent to control a project's execution.
    This includes pause, resume, skip, stop, retry, and restart actions.

    Attributes:
        id: Unique control identifier (UUID).
        project_id: ID of the project this control applies to.
        action: The type of control action.
        status: Current status of the control action.
        initiated_by: Who initiated the control (user, system, etc.).
        agents_affected: Number of agents affected by this control.
        error_message: Error message if the control failed.
        metadata: Additional control metadata (JSON).
    """

    __tablename__ = "project_controls"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[ProjectControlAction] = mapped_column(
        SQLEnum(ProjectControlAction, native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[ProjectControlStatus] = mapped_column(
        SQLEnum(ProjectControlStatus, native_enum=False),
        nullable=False,
        default=ProjectControlStatus.PENDING,
        index=True,
    )
    initiated_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="user",
    )
    agents_affected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
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
        back_populates="control_history",
    )


# Pydantic schemas for API
class ProjectControlBase(BaseModel):
    """Base schema for ProjectControl."""

    project_id: uuid.UUID
    action: ProjectControlAction
    status: ProjectControlStatus = ProjectControlStatus.PENDING
    initiated_by: str = "user"
    agents_affected: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = {}

    class Config:
        """Pydantic config."""

        populate_by_name = True


class ProjectControlCreate(ProjectControlBase):
    """Schema for creating a new ProjectControl."""

    pass


class ProjectControlResponse(ProjectControlBase):
    """Schema for ProjectControl response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProjectControlHistoryEntry(BaseModel):
    """Schema for a control history entry displayed in UI."""

    id: uuid.UUID
    action: ProjectControlAction
    status: ProjectControlStatus
    initiatedBy: str
    agentsAffected: int
    errorMessage: str | None
    createdAt: datetime
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def from_model(cls, control: ProjectControl) -> "ProjectControlHistoryEntry":
        """Create schema from model instance."""
        return cls(
            id=control.id,
            action=control.action,
            status=control.status,
            initiatedBy=control.initiated_by,
            agentsAffected=control.agents_affected,
            errorMessage=control.error_message,
            createdAt=control.created_at,
            metadata=control.meta_data if isinstance(control.meta_data, dict) else {},
        )
