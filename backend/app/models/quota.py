"""Quota and request queue models for API provider management.

This module provides models for:
- Provider configuration and rate limits
- Quota usage tracking
- Request queue for throttling
- Queue management with priority system
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Integer, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base, TimestampMixin


# ================================================================
# ENUMS
# ================================================================


class ProviderType(str, enum.Enum):
    """API provider types."""

    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"
    CURSOR = "cursor"


class QuotaResetType(str, enum.Enum):
    """Quota reset schedule types."""

    DAILY = "daily"
    MONTHLY = "monthly"
    FIXED_DATE = "fixed_date"


class QuotaAlertType(str, enum.Enum):
    """Quota alert severity levels."""

    WARNING = "warning"  # 80% threshold
    CRITICAL = "critical"  # 90% threshold
    OVERAGE = "overage"  # 95%+ threshold (emergency)


class QuotaAlertStatus(str, enum.Enum):
    """Quota alert status states."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertChannel(str, enum.Enum):
    """Alert delivery channels."""

    DASHBOARD = "dashboard"
    DESKTOP = "desktop"
    AUDIO = "audio"
    EMAIL = "email"


class QueuePriority(str, enum.Enum):
    """Request queue priority levels.

    Higher priority requests are processed first.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QueueStatus(str, enum.Enum):
    """Request queue status states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ================================================================
# DATABASE MODELS
# ================================================================


class Provider(Base, TimestampMixin):
    """API provider configuration and rate limits.

    Attributes:
        id: Unique provider identifier (UUID).
        name: Provider type (claude, gemini, openai, cursor).
        display_name: Human-readable provider name.
        api_endpoint: Base API endpoint URL.
        rate_limit_rpm: Requests per minute limit.
        rate_limit_rph: Requests per hour limit.
        rate_limit_tpm: Tokens per minute limit.
        rate_limit_tokens_per_day: Tokens per day limit.
        default_quota_limit: Default request quota per period.
        quota_reset_type: How quota resets (daily, monthly, fixed_date).
        quota_reset_day_of_month: Day of month for reset (1-31).
        quota_reset_hour: Hour of day for reset (0-23).
        quota_reset_timezone: Timezone for reset calculation.
        is_active: Whether provider is active.
        metadata: Additional provider configuration (JSON).
    """

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[ProviderType] = mapped_column(
        SQLEnum(ProviderType, native_enum=False),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    api_endpoint: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    rate_limit_rpm: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Requests per minute limit",
    )
    rate_limit_rph: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Requests per hour limit",
    )
    rate_limit_tpm: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Tokens per minute limit",
    )
    rate_limit_tokens_per_day: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Tokens per day limit",
    )
    default_quota_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        comment="Default requests per period",
    )
    quota_reset_type: Mapped[QuotaResetType] = mapped_column(
        SQLEnum(QuotaResetType, native_enum=False),
        nullable=False,
        default=QuotaResetType.DAILY,
    )
    quota_reset_day_of_month: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Day of month for reset (1-31)",
    )
    quota_reset_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Hour of day for reset (0-23)",
    )
    quota_reset_timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="UTC",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    quota_usages: Mapped[list["QuotaUsage"]] = relationship(
        "QuotaUsage",
        back_populates="provider",
        cascade="all, delete-orphan",
    )
    queued_requests: Mapped[list["RequestQueue"]] = relationship(
        "RequestQueue",
        back_populates="provider",
        cascade="all, delete-orphan",
        order_by="desc(RequestQueue.created_at)",
    )


class QuotaUsage(Base, TimestampMixin):
    """Quota usage tracking for providers and projects.

    Tracks current usage against quota limits for API requests.
    Can be global (provider-level) or per-project.

    Attributes:
        id: Unique quota usage identifier (UUID).
        provider_id: Associated provider.
        project_id: Associated project (null for global quota).
        current_requests: Current request count this period.
        current_tokens: Current token count this period.
        quota_limit: Request quota limit for this period.
        quota_limit_tokens: Token quota limit for this period.
        period_start: Start of current quota period.
        period_end: End of current quota period.
        last_reset_at: When quota was last reset.
        last_request_at: When last request was made.
        overage_count: Number of times quota was exceeded.
        metadata: Additional quota metadata (JSON).
    """

    __tablename__ = "quota_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Null for global quota, set for per-project quota",
    )
    current_requests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    current_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    quota_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quota_limit_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    last_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_request_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    overage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    last_alert_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the last alert was sent for this usage",
    )

    # Relationships
    provider: Mapped["Provider"] = relationship(
        "Provider",
        back_populates="quota_usages",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="quota_usages",
    )

    # Computed properties
    @property
    def usage_percent(self) -> float:
        """Calculate usage as percentage of quota limit."""
        if self.quota_limit == 0:
            return 0.0
        return (self.current_requests / self.quota_limit) * 100

    @property
    def is_over_limit(self) -> bool:
        """Check if current usage exceeds quota limit."""
        return self.current_requests >= self.quota_limit

    @property
    def remaining_quota(self) -> int:
        """Calculate remaining quota for this period."""
        return max(0, self.quota_limit - self.current_requests)


class RequestQueue(Base, TimestampMixin):
    """Queued API requests for throttling and delayed processing.

    Requests are queued when:
    - Quota limits are reached
    - Rate limiting is detected (429 responses)
    - Manual scheduling for batch processing

    Attributes:
        id: Unique request identifier (UUID).
        provider_id: API provider for this request.
        project_id: Associated project (null for global requests).
        session_id: Associated session if applicable.
        endpoint: Target endpoint URL.
        method: HTTP method.
        payload: Request body/payload (JSON).
        headers: Request headers (JSON).
        priority: Queue priority (high, medium, low).
        status: Queue status.
        scheduled_at: When to process this request (null = immediately).
        retry_count: Number of retry attempts.
        max_retries: Maximum retry attempts.
        last_error: Last error message if failed.
        error_details: Detailed error information (JSON).
        processing_started_at: When processing started.
        completed_at: When successfully completed.
        failed_at: When failed.
        cancelled_at: When cancelled.
        meta: Additional metadata (JSON).
    """

    __tablename__ = "request_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="API provider for this request",
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Associated project (null for global requests)",
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated session if applicable",
    )
    endpoint: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Target endpoint URL",
    )
    method: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="POST",
        comment="HTTP method",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Request body/payload",
    )
    headers: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Request headers",
    )
    priority: Mapped[QueuePriority] = mapped_column(
        SQLEnum(QueuePriority, native_enum=False),
        nullable=False,
        default=QueuePriority.MEDIUM,
        index=True,
        comment="Queue priority (high, medium, low)",
    )
    status: Mapped[QueueStatus] = mapped_column(
        SQLEnum(QueueStatus, native_enum=False),
        nullable=False,
        default=QueueStatus.PENDING,
        index=True,
        comment="Queue status",
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When to process this request (null = immediately)",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum retry attempts",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Last error message if failed",
    )
    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Detailed error information",
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When successfully completed",
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When failed",
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When cancelled",
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        comment="Additional metadata",
    )

    # Relationships
    provider: Mapped["Provider"] = relationship(
        "Provider",
        back_populates="queued_requests",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="queued_requests",
    )
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="queued_requests",
    )

    # Computed properties
    @property
    def priority_weight(self) -> int:
        """Get numeric priority weight for ordering."""
        weights = {QueuePriority.HIGH: 3, QueuePriority.MEDIUM: 2, QueuePriority.LOW: 1}
        return weights.get(self.priority, 0)

    @property
    def is_ready(self) -> bool:
        """Check if request is ready for processing."""
        if self.status != QueueStatus.PENDING:
            return False
        if self.scheduled_at is None:
            return True
        return self.scheduled_at <= datetime.now(timezone.utc)

    @property
    def should_retry(self) -> bool:
        """Check if request should be retried."""
        return self.retry_count < self.max_retries

    @property
    def is_terminal(self) -> bool:
        """Check if request is in a terminal state."""
        return self.status in {
            QueueStatus.COMPLETED,
            QueueStatus.FAILED,
            QueueStatus.CANCELLED,
        }

    @property
    def wait_time_seconds(self) -> float | None:
        """Calculate time waited in queue."""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    # State transition methods
    def mark_processing(self) -> None:
        """Mark request as processing."""
        self.status = QueueStatus.PROCESSING
        self.processing_started_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark request as completed."""
        self.status = QueueStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str, details: dict[str, Any] | None = None) -> None:
        """Mark request as failed."""
        self.status = QueueStatus.FAILED
        self.failed_at = datetime.now(timezone.utc)
        self.last_error = error
        if details:
            self.error_details.update(details)

    def mark_cancelled(self) -> None:
        """Mark request as cancelled."""
        self.status = QueueStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)

    def increment_retry(self) -> None:
        """Increment retry count and reschedule."""
        self.retry_count += 1
        # Exponential backoff: 2^retry_count seconds
        backoff_seconds = 2 ** self.retry_count
        self.scheduled_at = datetime.now(timezone.utc) + datetime.timedelta(
            seconds=backoff_seconds
        )
        self.status = QueueStatus.PENDING


class QuotaAlert(Base, TimestampMixin):
    """Quota alert for overage notifications.

    Attributes:
        id: Unique alert identifier (UUID).
        quota_usage_id: Associated quota usage record.
        alert_type: Alert severity (warning, critical, overage).
        status: Alert status (active, acknowledged, resolved).
        threshold_percent: Threshold that triggered the alert.
        current_usage: Usage value when alert triggered.
        quota_limit: Quota limit at time of alert.
        message: Alert message.
        acknowledged_by: User who acknowledged the alert.
        acknowledged_at: When alert was acknowledged.
        resolved_at: When alert was resolved.
        metadata: Additional alert metadata (JSON).
    """

    __tablename__ = "quota_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    quota_usage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quota_usage.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[QuotaAlertType] = mapped_column(
        SQLEnum(QuotaAlertType, native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[QuotaAlertStatus] = mapped_column(
        SQLEnum(QuotaAlertStatus, native_enum=False),
        nullable=False,
        default=QuotaAlertStatus.ACTIVE,
        index=True,
    )
    threshold_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Threshold that triggered the alert",
    )
    current_usage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    quota_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    # New fields for multi-channel alerting and escalation
    alert_channels: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        comment="Channels the alert was sent to (dashboard, desktop, audio)",
    )
    escalation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times alert has been escalated",
    )
    escalation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the last escalation occurred",
    )

    # Relationships
    quota_usage: Mapped["QuotaUsage"] = relationship(
        "QuotaUsage",
        back_populates="alerts",
    )

    def acknowledge(self, acknowledged_by: str | None = None) -> None:
        """Mark alert as acknowledged."""
        self.status = QuotaAlertStatus.ACKNOWLEDGED
        self.acknowledged_by = acknowledged_by
        self.acknowledged_at = datetime.now(timezone.utc)

    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.status = QuotaAlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)

    def escalate(self) -> None:
        """Escalate the alert (increment count and update timestamp)."""
        self.escalation_count += 1
        self.escalation_at = datetime.now(timezone.utc)

    def add_channel(self, channel: str) -> None:
        """Add a channel that the alert was sent to."""
        if channel not in self.alert_channels:
            self.alert_channels = [*self.alert_channels, channel]


# Add alerts relationship to QuotaUsage
QuotaUsage.alerts = relationship(
    "QuotaAlert",
    back_populates="quota_usage",
    cascade="all, delete-orphan",
    order_by="desc(QuotaAlert.created_at)",
)


# Import Project and Session for relationships (avoid circular import)
# These are imported at runtime to resolve forward references
from app.models.project import Project
from app.models.session import Session

# Add back-references to Project and Session
Project.quota_usages = relationship(
    "QuotaUsage",
    back_populates="project",
    cascade="all, delete-orphan",
)
Project.queued_requests = relationship(
    "RequestQueue",
    back_populates="project",
    cascade="all, delete-orphan",
    order_by="desc(RequestQueue.created_at)",
)
Session.queued_requests = relationship(
    "RequestQueue",
    back_populates="session",
    cascade="all, delete-orphan",
)


class AlertConfig(Base, TimestampMixin):
    """Alert configuration for per-provider alert settings.

    Stores alert thresholds, channels, cooldown, and escalation settings.
    Can be global (null provider/project) or specific to a provider/project.

    Attributes:
        id: Unique config identifier (UUID).
        provider_id: Provider ID (null for global settings).
        project_id: Project ID (null for global settings).
        warning_threshold: Warning threshold percentage (default 80%).
        critical_threshold: Critical threshold percentage (default 90%).
        emergency_threshold: Emergency threshold percentage (default 95%).
        channels: Enabled alert channels (dashboard, desktop, audio).
        dashboard_enabled: Show in-dashboard alerts.
        desktop_enabled: Send desktop notifications.
        audio_enabled: Play audio alerts at emergency threshold.
        cooldown_minutes: Minutes between alerts for same threshold.
        escalation_enabled: Enable alert escalation.
        escalation_minutes: Minutes before escalating unacknowledged alert.
        max_escalations: Maximum number of escalations.
        is_active: Whether this config is active.
        metadata: Additional configuration (JSON).
    """

    __tablename__ = "alert_config"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Provider ID (null for global settings)",
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Project ID (null for global settings)",
    )
    warning_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=80,
        comment="Warning threshold percentage",
    )
    critical_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=90,
        comment="Critical threshold percentage",
    )
    emergency_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=95,
        comment="Emergency threshold percentage",
    )
    channels: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        comment="Enabled alert channels",
    )
    dashboard_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Show in-dashboard alerts",
    )
    desktop_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Send desktop notifications",
    )
    audio_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Play audio alerts at emergency threshold",
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        comment="Minutes between alerts for same threshold",
    )
    escalation_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Enable alert escalation",
    )
    escalation_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=15,
        comment="Minutes before escalating unacknowledged alert",
    )
    max_escalations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum number of escalations",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # Relationships
    provider: Mapped["Provider | None"] = relationship(
        "Provider",
        foreign_keys=[provider_id],
    )
    project: Mapped["Project | None"] = relationship(
        "Project",
        foreign_keys=[project_id],
    )


# ================================================================
# PYDANTIC SCHEMAS
# ================================================================


class ProviderCreate(BaseModel):
    """Schema for creating a new Provider."""

    name: ProviderType
    display_name: str
    api_endpoint: str | None = None
    rate_limit_rpm: int | None = None
    rate_limit_rph: int | None = None
    rate_limit_tpm: int | None = None
    rate_limit_tokens_per_day: int | None = None
    default_quota_limit: int = 1000
    quota_reset_type: QuotaResetType = QuotaResetType.DAILY
    quota_reset_day_of_month: int | None = None
    quota_reset_hour: int = 0
    quota_reset_timezone: str = "UTC"
    is_active: bool = True
    metadata: dict[str, Any] = {}


class ProviderResponse(BaseModel):
    """Schema for Provider response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: ProviderType
    display_name: str
    api_endpoint: str | None
    rate_limit_rpm: int | None
    rate_limit_rph: int | None
    rate_limit_tpm: int | None
    rate_limit_tokens_per_day: int | None
    default_quota_limit: int
    quota_reset_type: QuotaResetType
    quota_reset_day_of_month: int | None
    quota_reset_hour: int
    quota_reset_timezone: str
    is_active: bool
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    # Additional fields for frontend compatibility
    models: list[str] = []
    enabled: bool = True  # Alias for is_active
    priority: int = 0


class QuotaUsageResponse(BaseModel):
    """Schema for QuotaUsage response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str | None = None
    project_id: uuid.UUID | None
    current_requests: int
    current_tokens: int
    quota_limit: int
    quota_limit_tokens: int | None
    period_start: datetime
    period_end: datetime
    last_reset_at: datetime
    last_request_at: datetime | None
    overage_count: int
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    # Computed properties
    usage_percent: float
    is_over_limit: bool
    remaining_quota: int
    remaining_requests: int = 0  # Alias for remaining_quota for frontend compatibility
    time_until_reset_seconds: int | None = None


class RequestQueueCreate(BaseModel):
    """Schema for creating a new queued request."""

    provider_id: uuid.UUID
    project_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    endpoint: str
    method: str = "POST"
    payload: dict[str, Any] = {}
    headers: dict[str, str] = {}
    priority: QueuePriority = QueuePriority.MEDIUM
    scheduled_at: datetime | None = None
    max_retries: int = 3
    metadata: dict[str, Any] = Field(default_factory=dict)


class RequestQueueResponse(BaseModel):
    """Schema for RequestQueue response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    project_id: uuid.UUID | None
    session_id: uuid.UUID | None
    endpoint: str
    method: str
    priority: QueuePriority
    status: QueueStatus
    scheduled_at: datetime | None
    retry_count: int
    max_retries: int
    last_error: str | None
    error_details: dict[str, Any]
    processing_started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    # Computed properties
    priority_weight: int
    is_ready: bool
    should_retry: bool
    wait_time_seconds: float | None


class QueueStatsResponse(BaseModel):
    """Schema for queue statistics response."""

    total_pending: int
    total_processing: int
    total_completed: int
    total_failed: int
    total_cancelled: int
    by_priority: dict[str, int]
    by_provider: dict[str, int]
    by_project: dict[str, int]
    oldest_pending: datetime | None
    newest_pending: datetime | None
    avg_wait_time_seconds: float | None
    queue_depth: int
    timestamp: datetime


class QuotaAlertResponse(BaseModel):
    """Schema for QuotaAlert response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quota_usage_id: uuid.UUID
    provider_id: uuid.UUID | None = None
    provider_name: str | None = None
    alert_type: QuotaAlertType
    status: QuotaAlertStatus
    threshold_percent: int
    current_usage: int
    quota_limit: int
    message: str
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    # New fields for multi-channel alerting and escalation
    alert_channels: list[str] = []
    escalation_count: int = 0
    escalation_at: datetime | None = None


class AlertConfigCreate(BaseModel):
    """Schema for creating alert configuration."""

    provider_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    warning_threshold: int = 80
    critical_threshold: int = 90
    emergency_threshold: int = 95
    channels: list[str] = ["dashboard", "desktop", "audio"]
    dashboard_enabled: bool = True
    desktop_enabled: bool = True
    audio_enabled: bool = True
    cooldown_minutes: int = 30
    escalation_enabled: bool = True
    escalation_minutes: int = 15
    max_escalations: int = 3
    is_active: bool = True
    metadata: dict[str, Any] = {}


class AlertConfigUpdate(BaseModel):
    """Schema for updating alert configuration."""

    warning_threshold: int | None = None
    critical_threshold: int | None = None
    emergency_threshold: int | None = None
    channels: list[str] | None = None
    dashboard_enabled: bool | None = None
    desktop_enabled: bool | None = None
    audio_enabled: bool | None = None
    cooldown_minutes: int | None = None
    escalation_enabled: bool | None = None
    escalation_minutes: int | None = None
    max_escalations: int | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class AlertConfigResponse(BaseModel):
    """Schema for AlertConfig response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID | None
    project_id: uuid.UUID | None
    warning_threshold: int
    critical_threshold: int
    emergency_threshold: int
    channels: list[str]
    dashboard_enabled: bool
    desktop_enabled: bool
    audio_enabled: bool
    cooldown_minutes: int
    escalation_enabled: bool
    escalation_minutes: int
    max_escalations: int
    is_active: bool
    meta_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AlertConfigListResponse(BaseModel):
    """Schema for alert config list response."""

    items: list[AlertConfigResponse]
    total: int


class QuotaSummaryResponse(BaseModel):
    """Schema for quota summary response."""

    total_providers: int
    active_providers: int
    total_requests: int
    total_tokens: int
    total_usage_percent: float
    alerts_count: int
    alerts_critical: int
    providers_over_limit: int
    last_updated: datetime


class ProviderListResponse(BaseModel):
    """Schema for provider list response."""

    items: list[ProviderResponse]
    total: int


class QuotaUsageListResponse(BaseModel):
    """Schema for quota usage list response."""

    items: list[QuotaUsageResponse]
    total: int


class QuotaAlertListResponse(BaseModel):
    """Schema for quota alert list response."""

    items: list[QuotaAlertResponse]
    total: int


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Enums
    "ProviderType",
    "QuotaResetType",
    "QuotaAlertType",
    "QuotaAlertStatus",
    "AlertChannel",
    "QueuePriority",
    "QueueStatus",
    # Models
    "Provider",
    "QuotaUsage",
    "QuotaAlert",
    "AlertConfig",
    "RequestQueue",
    # Schemas
    "ProviderCreate",
    "ProviderResponse",
    "ProviderListResponse",
    "QuotaUsageResponse",
    "QuotaUsageListResponse",
    "QuotaAlertResponse",
    "QuotaAlertListResponse",
    "QuotaSummaryResponse",
    "AlertConfigCreate",
    "AlertConfigUpdate",
    "AlertConfigResponse",
    "AlertConfigListResponse",
    "RequestQueueCreate",
    "RequestQueueResponse",
    "QueueStatsResponse",
]
