"""SQLAlchemy models for the Dope Dash application.

This module exports all database models for use in the application.
"""
from app.models.base import Base, TimestampMixin, TimestampMixinNullable, SoftDeleteMixin
from app.models.event import Event, EventCreate, EventResponse
from app.models.session import Session, SessionCreate, SessionUpdate, SessionResponse, AgentType, SessionStatus
from app.models.spec_run import SpecRun, SpecRunCreate, SpecRunUpdate, SpecRunResponse, SpecRunStatus
from app.models.metric_bucket import MetricBucket, MetricBucketCreate, MetricBucketResponse
from app.models.deletion_log import (
    DeletionLog,
    DeletionLogCreate,
    DeletionLogResponse,
    DeletionType,
    EntityType,
)
from app.models.report import (
    Report,
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportConfig,
    ReportSchedule,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    ReportScheduleResponse,
    ReportScheduleConfig,
    ReportType,
    ReportFormat,
    ReportStatus,
    ScheduleFrequency,
)
from app.models.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectStatus,
    ProjectPriority,
)
from app.models.project_control import (
    ProjectControl,
    ProjectControlAction,
    ProjectControlStatus,
    ProjectControlCreate,
    ProjectControlResponse,
    ProjectControlHistoryEntry,
)
from app.models.command_history import (
    CommandHistory,
    CommandStatus,
    CommandHistoryCreate,
    CommandHistoryUpdate,
    CommandHistoryResponse,
    CommandHistoryEntry,
    CommandHistoryListResponse,
    CommandTemplate,
)
from app.models.quota import (
    Provider,
    ProviderType,
    QuotaUsage,
    QuotaUsageResponse,
    ProviderCreate,
    ProviderResponse,
    RequestQueue,
    RequestQueueCreate,
    RequestQueueResponse,
    QueuePriority,
    QueueStatus,
    QueueStatsResponse,
    QuotaResetType,
    QuotaAlertType,
    QuotaAlertStatus,
)
from app.models.agent_pool import (
    AgentPool,
    PoolAgentStatus,
    ScalingAction,
    AgentPoolCreate,
    AgentPoolUpdate,
    AgentPoolResponse,
    AgentPoolListResponse,
    PoolMetrics,
    PoolHealthReport,
    ScalingRecommendation,
    ScalingPolicy,
    ScalingEventCreate,
    ScalingEventResponse,
    AgentAssignRequest,
    AgentAssignResponse,
    AgentHeartbeatRequest,
)
from app.models.state_transition import (
    StateTransition,
    StateTransitionSource,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "TimestampMixinNullable",
    "SoftDeleteMixin",
    # Event
    "Event",
    "EventCreate",
    "EventResponse",
    # Session
    "Session",
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "AgentType",
    "SessionStatus",
    # SpecRun
    "SpecRun",
    "SpecRunCreate",
    "SpecRunUpdate",
    "SpecRunResponse",
    "SpecRunStatus",
    # MetricBucket
    "MetricBucket",
    "MetricBucketCreate",
    "MetricBucketResponse",
    # DeletionLog
    "DeletionLog",
    "DeletionLogCreate",
    "DeletionLogResponse",
    "DeletionType",
    "EntityType",
    # Report
    "Report",
    "ReportCreate",
    "ReportUpdate",
    "ReportResponse",
    "ReportConfig",
    "ReportSchedule",
    "ReportScheduleCreate",
    "ReportScheduleUpdate",
    "ReportScheduleResponse",
    "ReportScheduleConfig",
    "ReportType",
    "ReportFormat",
    "ReportStatus",
    "ScheduleFrequency",
    # Project
    "Project",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectStatus",
    "ProjectPriority",
    # ProjectControl
    "ProjectControl",
    "ProjectControlAction",
    "ProjectControlStatus",
    "ProjectControlCreate",
    "ProjectControlResponse",
    "ProjectControlHistoryEntry",
    # CommandHistory
    "CommandHistory",
    "CommandStatus",
    "CommandHistoryCreate",
    "CommandHistoryUpdate",
    "CommandHistoryResponse",
    "CommandHistoryEntry",
    "CommandHistoryListResponse",
    "CommandTemplate",
    # Quota
    "Provider",
    "ProviderType",
    "QuotaUsage",
    "QuotaUsageResponse",
    "ProviderCreate",
    "ProviderResponse",
    "RequestQueue",
    "RequestQueueCreate",
    "RequestQueueResponse",
    "QueuePriority",
    "QueueStatus",
    "QueueStatsResponse",
    "QuotaResetType",
    "QuotaAlertType",
    "QuotaAlertStatus",
    # AgentPool
    "AgentPool",
    "PoolAgentStatus",
    "ScalingAction",
    "AgentPoolCreate",
    "AgentPoolUpdate",
    "AgentPoolResponse",
    "AgentPoolListResponse",
    "PoolMetrics",
    "PoolHealthReport",
    "ScalingRecommendation",
    "ScalingPolicy",
    "ScalingEventCreate",
    "ScalingEventResponse",
    "AgentAssignRequest",
    "AgentAssignResponse",
    "AgentHeartbeatRequest",
    # StateTransition
    "StateTransition",
    "StateTransitionSource",
]
