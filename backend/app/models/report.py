"""Report model for storing generated reports."""
import uuid
from typing import Any

import enum
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ReportType(str, enum.Enum):
    """Types of reports that can be generated."""

    SESSION = "session"
    TRENDS = "trends"
    COMPARISON = "comparison"
    ERROR_ANALYSIS = "error_analysis"


class ReportFormat(str, enum.Enum):
    """Formats for report output."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class ReportStatus(str, enum.Enum):
    """Status of report generation."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleFrequency(str, enum.Enum):
    """Frequency for scheduled reports."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Report(Base, TimestampMixin):
    """Database model for generated reports.

    Reports store metadata and configuration for generated reports.
    The actual report content is stored in the content field or file_path.

    Attributes:
        id: Unique report identifier (UUID).
        title: Report title.
        type: Type of report (session, trends, comparison, error_analysis).
        format: Report format (pdf, markdown, json, html).
        status: Generation status (pending, generating, completed, failed).
        config: Report configuration (JSON).
        content: Generated report content (text, nullable).
        file_path: Path to generated report file (nullable).
        created_at: When the report was created.
        updated_at: When the report was last updated.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType, native_enum=False),
        nullable=False,
        index=True,
    )
    format: Mapped[ReportFormat] = mapped_column(
        SQLEnum(ReportFormat, native_enum=False),
        nullable=False,
    )
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus, native_enum=False),
        nullable=False,
        index=True,
        default=ReportStatus.PENDING,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    file_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_reports_type_status", "type", "status"),
        Index("ix_reports_created_at", "created_at"),
    )


class ReportSchedule(Base, TimestampMixin):
    """Database model for report schedules.

    Schedules store configuration for automated report generation.

    Attributes:
        id: Unique schedule identifier (UUID).
        name: Schedule name.
        enabled: Whether the schedule is enabled.
        frequency: Frequency of report generation (daily, weekly, monthly, none).
        report_types: List of report types to generate.
        format: Report format for scheduled reports.
        retention_days: Number of days to retain generated reports.
        config: Additional schedule configuration (JSON).
        last_run_at: Timestamp of last run.
        next_run_at: Timestamp of next scheduled run.
        created_at: When the schedule was created.
        updated_at: When the schedule was last updated.
    """

    __tablename__ = "report_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        index=True,
    )
    frequency: Mapped[ScheduleFrequency] = mapped_column(
        SQLEnum(ScheduleFrequency, native_enum=False),
        nullable=False,
        default=ScheduleFrequency.NONE,
    )
    report_types: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    format: Mapped[ReportFormat] = mapped_column(
        SQLEnum(ReportFormat, native_enum=False),
        nullable=False,
        default=ReportFormat.PDF,
    )
    retention_days: Mapped[int] = mapped_column(
        nullable=False,
        default=30,
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    last_run_at: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    next_run_at: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


# Pydantic schemas for API
class ReportConfig(BaseModel):
    """Configuration for report generation."""

    type: ReportType = Field(..., description="Report type")
    format: ReportFormat = Field(..., description="Report format")
    title: str = Field(..., description="Report title")
    include_charts: bool = Field(default=True, description="Include charts in report")
    session_ids: list[str] | None = Field(default=None, description="Session IDs for session reports")
    compare_session_ids: list[str] | None = Field(default=None, description="Session IDs for comparison")
    date_range: dict[str, str] | None = Field(default=None, description="Date range: {from, to}")


class ReportBase(BaseModel):
    """Base schema for Report."""

    title: str
    type: ReportType
    format: ReportFormat
    status: ReportStatus = ReportStatus.PENDING
    config: dict[str, Any] = {}
    content: str | None = None
    file_path: str | None = None


class ReportCreate(ReportConfig):
    """Schema for creating a new Report."""

    pass


class ReportUpdate(BaseModel):
    """Schema for updating a Report."""

    status: ReportStatus | None = None
    content: str | None = None
    file_path: str | None = None


class ReportResponse(ReportBase):
    """Schema for Report response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp


class ReportScheduleConfig(BaseModel):
    """Configuration for report scheduling."""

    enabled: bool = Field(default=False, description="Enable scheduled reports")
    frequency: ScheduleFrequency = Field(default=ScheduleFrequency.NONE, description="Frequency")
    report_types: list[ReportType] = Field(default_factory=list, description="Report types to generate")
    format: ReportFormat = Field(default=ReportFormat.PDF, description="Report format")
    retention_days: int = Field(default=30, description="Retention period in days")


class ReportScheduleBase(BaseModel):
    """Base schema for ReportSchedule."""

    name: str
    enabled: bool = True
    frequency: ScheduleFrequency = ScheduleFrequency.NONE
    report_types: list[ReportType] = []
    format: ReportFormat = ReportFormat.PDF
    retention_days: int = 30
    config: dict[str, Any] = {}
    last_run_at: str | None = None
    next_run_at: str | None = None


class ReportScheduleCreate(ReportScheduleConfig):
    """Schema for creating a new ReportSchedule."""

    name: str


class ReportScheduleUpdate(BaseModel):
    """Schema for updating a ReportSchedule."""

    name: str | None = None
    enabled: bool | None = None
    frequency: ScheduleFrequency | None = None
    report_types: list[ReportType] | None = None
    format: ReportFormat | None = None
    retention_days: int | None = None
    config: dict[str, Any] | None = None
    next_run_at: str | None = None


class ReportScheduleResponse(ReportScheduleBase):
    """Schema for ReportSchedule response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
