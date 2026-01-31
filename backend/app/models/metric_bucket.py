"""MetricBucket model - time-series metrics for performance."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MetricBucket(Base, TimestampMixin):
    """Database model representing time-series metric buckets.

    Stores aggregated metrics for performance monitoring and analysis.
    Data is bucketed by time to improve query performance.

    Attributes:
        id: Unique metric bucket identifier (UUID).
        session_id: Foreign key to the parent session.
        metric_name: Name of the metric (e.g., "cpu_usage", "memory_mb").
        value: Numeric value of the metric.
        bucket_size: Size of the time bucket in seconds.
        timestamp: Timestamp for the metric (bucket start time).
    """

    __tablename__ = "metric_buckets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        index=True,
        nullable=False,
    )
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    bucket_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="metric_buckets",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_metric_buckets_session_id_timestamp", "session_id", "timestamp"),
        Index(
            "ix_metric_buckets_metric_name_timestamp",
            "metric_name",
            "timestamp",
        ),
        Index(
            "ix_metric_buckets_session_metric_timestamp",
            "session_id",
            "metric_name",
            "timestamp",
        ),
    )


# Pydantic schemas for API
class MetricBucketBase(BaseModel):
    """Base schema for MetricBucket."""

    metric_name: str
    value: float
    bucket_size: int
    timestamp: datetime


class MetricBucketCreate(MetricBucketBase):
    """Schema for creating a new MetricBucket."""

    session_id: uuid.UUID


class MetricBucketResponse(MetricBucketBase):
    """Schema for MetricBucket response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    created_at: str  # ISO format timestamp
