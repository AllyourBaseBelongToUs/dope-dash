"""Command history model for tracking custom commands sent to agents.

This module provides the CommandHistory model which records all custom
commands sent to agents, including their results and metadata.
"""
import uuid
import json
from typing import Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, Text, Enum as SQLEnum, Integer, String, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base, TimestampMixin


class CommandStatus(str, enum.Enum):
    """Status of a command execution."""

    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CommandHistory(Base, TimestampMixin):
    """Database model representing a custom command sent to an agent.

    Each command records the command content, result, exit code, duration,
    and other metadata for history tracking and replay functionality.

    Attributes:
        id: Unique command identifier (UUID).
        project_id: ID of the project this command is associated with (optional).
        session_id: Session ID this command was sent to (optional).
        command: The command string that was sent.
        status: Current status of the command execution.
        result: The output result from the command (if available).
        error_message: Error message if the command failed.
        exit_code: Exit code returned by the command.
        duration_ms: Command execution duration in milliseconds.
        is_favorite: Whether this command is marked as a favorite.
        template_name: Name of the template if this is from a template.
        metadata: Additional command metadata (JSON).
    """

    __tablename__ = "commands_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    command: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[CommandStatus] = mapped_column(
        SQLEnum(CommandStatus, native_enum=False),
        nullable=False,
        default=CommandStatus.PENDING,
        index=True,
    )
    result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    exit_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    template_name: Mapped[str | None] = mapped_column(
        String(255),
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
        back_populates="command_history",
    )


# Pydantic schemas for API
class CommandHistoryBase(BaseModel):
    """Base schema for CommandHistory."""

    project_id: uuid.UUID | None = None
    session_id: str | None = None
    command: str
    status: CommandStatus = CommandStatus.PENDING
    result: str | None = None
    error_message: str | None = None
    exit_code: int | None = None
    duration_ms: int | None = None
    is_favorite: bool = False
    template_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        populate_by_name = True


class CommandHistoryCreate(CommandHistoryBase):
    """Schema for creating a new CommandHistory entry."""

    pass


class CommandHistoryUpdate(BaseModel):
    """Schema for updating a CommandHistory entry."""

    status: CommandStatus | None = None
    result: str | None = None
    error_message: str | None = None
    exit_code: int | None = None
    duration_ms: int | None = None
    is_favorite: bool | None = None
    template_name: str | None = None
    metadata: dict[str, Any] | None = None


class CommandHistoryResponse(CommandHistoryBase):
    """Schema for CommandHistory response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CommandHistoryEntry(BaseModel):
    """Schema for a command history entry displayed in UI."""

    id: uuid.UUID
    projectId: uuid.UUID | None
    sessionId: str | None
    command: str
    status: CommandStatus
    result: str | None
    errorMessage: str | None
    exitCode: int | None
    durationMs: int | None
    isFavorite: bool
    templateName: str | None
    createdAt: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def from_model(cls, cmd: CommandHistory) -> "CommandHistoryEntry":
        """Create schema from model instance."""
        return cls(
            id=cmd.id,
            projectId=cmd.project_id,
            sessionId=cmd.session_id,
            command=cmd.command,
            status=cmd.status,
            result=cmd.result,
            errorMessage=cmd.error_message,
            exitCode=cmd.exit_code,
            durationMs=cmd.duration_ms,
            isFavorite=cmd.is_favorite,
            templateName=cmd.template_name,
            createdAt=cmd.created_at,
            metadata=cmd.meta_data if isinstance(cmd.meta_data, dict) else {},
        )


class CommandTemplate(BaseModel):
    """Schema for a command template."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    command: str
    category: str = "general"
    tags: list[str] = Field(default_factory=list)


class CommandHistoryListResponse(BaseModel):
    """Schema for command history list response."""

    commands: list[CommandHistoryEntry]
    total: int
    limit: int
    offset: int
