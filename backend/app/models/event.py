"""Event model - source of truth for all agent events."""
import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Event(Base, TimestampMixin, SoftDeleteMixin):
    """Database model representing an agent event.

    Events are the source of truth for all agent activity and are
    stored for 30 days by default.

    Attributes:
        id: Unique event identifier (UUID).
        session_id: Foreign key to the session that generated this event.
        event_type: Type of event (e.g., "spec_start", "spec_complete", "error").
        data: JSON payload containing event-specific data.
        deleted_at: Timestamp when record was soft deleted (None if not deleted).
    """

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="events",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_events_session_id_created_at", "session_id", "created_at"),
        Index("ix_events_event_type_created_at", "event_type", "created_at"),
    )


# Pydantic schemas for API
class EventBase(BaseModel):
    """Base schema for Event."""

    session_id: uuid.UUID
    event_type: str
    data: dict = {}


class EventCreate(EventBase):
    """Schema for creating a new Event."""

    pass


class EventResponse(EventBase):
    """Schema for Event response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
