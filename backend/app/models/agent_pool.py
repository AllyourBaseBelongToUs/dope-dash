"""Agent Pool model for distributed agent management with load balancing.

This module provides the database model and Pydantic schemas for managing
a pool of distributed agents with capacity tracking, health monitoring,
and affinity support.
"""
import uuid
from datetime import datetime
from typing import Any

import enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, JSON, Text, Enum as SQLEnum, Index, Integer, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.session import AgentType


class PoolAgentStatus(str, enum.Enum):
    """Agent pool lifecycle and availability states.

    States:
        AVAILABLE: Agent is idle and can accept new tasks
        BUSY: Agent is at or near capacity (current_load >= max_capacity)
        OFFLINE: Agent is not responding (heartbeat timeout)
        MAINTENANCE: Agent is temporarily unavailable for updates/repairs
        DRAINING: Agent is completing current tasks but not accepting new ones
    """

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    DRAINING = "draining"


class ScalingAction(str, enum.Enum):
    """Auto-scaling action types.

    Actions:
        SCALE_UP: Add more agents to the pool
        SCALE_DOWN: Remove agents from the pool
        NO_OP: No scaling needed (pool is healthy)
    """

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_OP = "no_op"


class AgentPool(Base, TimestampMixin, SoftDeleteMixin):
    """Database model representing an agent in the pool.

    This model tracks distributed agents with their capacity, health status,
    and assignment history for load balancing and auto-scaling decisions.

    Attributes:
        id: Unique pool entry identifier (UUID).
        agent_id: External agent identifier (unique across pool).
        agent_type: Type of agent (ralph, claude, cursor, etc.).
        status: Current availability status of the agent.
        current_project_id: ID of project currently assigned (null if idle).
        current_load: Number of active tasks/assignments (0 to max_capacity).
        max_capacity: Maximum concurrent tasks this agent can handle.
        capabilities: List of capabilities/skills this agent supports.
        metadata: Additional agent metadata (JSON).
        pid: Process ID of the agent (if local).
        working_dir: Working directory of the agent (if local).
        command: Command used to start the agent.
        tmux_session: Tmux session name (if applicable).
        last_heartbeat: Timestamp of last heartbeat from agent.
        total_assigned: Total number of tasks ever assigned to this agent.
        total_completed: Total number of tasks successfully completed.
        total_failed: Total number of tasks that failed.
        average_task_duration_ms: Average task completion time in milliseconds.
        affinity_tag: Tag for sticky sessions (same agent for same project).
        priority: Priority for assignment (higher = preferred).
        created_at: When the agent was registered.
        updated_at: Last update timestamp.
        deleted_at: Soft delete timestamp.
    """

    __tablename__ = "agent_pool"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Agent identification
    agent_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(AgentType, native_enum=False, create_type=False),
        nullable=False,
        index=True,
    )

    # Status and capacity
    status: Mapped[PoolAgentStatus] = mapped_column(
        SQLEnum(PoolAgentStatus, native_enum=False, create_type=True),
        nullable=False,
        default=PoolAgentStatus.AVAILABLE,
        index=True,
    )
    current_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_load: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    # Capabilities and metadata
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Agent runtime information
    pid: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    working_dir: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    command: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    tmux_session: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Statistics
    total_assigned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    average_task_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Affinity and priority
    affinity_tag: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
    )

    # Relationships
    current_project: Mapped["Project | None"] = relationship(
        "Project",
        foreign_keys=[current_project_id],
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_agent_pool_status_current_load", "status", "current_load"),
    )

    @property
    def utilization_percent(self) -> float:
        """Calculate current utilization as percentage (0-100)."""
        if self.max_capacity <= 0:
            return 0.0
        return min(100.0, (self.current_load / self.max_capacity) * 100)

    @property
    def is_available(self) -> bool:
        """Check if agent can accept new tasks."""
        return (
            self.status == PoolAgentStatus.AVAILABLE
            and self.current_load < self.max_capacity
            and self.deleted_at is None
        )

    @property
    def completion_rate(self) -> float:
        """Calculate task completion rate (0-1)."""
        if self.total_assigned <= 0:
            return 0.0
        return self.total_completed / self.total_assigned


# Pydantic schemas for API
class AgentPoolBase(BaseModel):
    """Base schema for Agent Pool."""

    agent_id: str
    agent_type: AgentType
    status: PoolAgentStatus = PoolAgentStatus.AVAILABLE
    current_project_id: uuid.UUID | None = None
    current_load: int = 0
    max_capacity: int = 5
    capabilities: list[str] = []
    metadata: dict[str, Any] = {}
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    tmux_session: str | None = None
    last_heartbeat: str | None = None
    total_assigned: int = 0
    total_completed: int = 0
    total_failed: int = 0
    average_task_duration_ms: int | None = None
    affinity_tag: str | None = None
    priority: int = 0


class AgentPoolCreate(AgentPoolBase):
    """Schema for registering a new agent in the pool."""

    pass


class AgentPoolUpdate(BaseModel):
    """Schema for updating an agent in the pool."""

    status: PoolAgentStatus | None = None
    current_project_id: uuid.UUID | None = None
    current_load: int | None = None
    max_capacity: int | None = None
    capabilities: list[str] | None = None
    metadata: dict[str, Any] | None = None
    pid: int | None = None
    working_dir: str | None = None
    command: str | None = None
    tmux_session: str | None = None
    last_heartbeat: str | None = None
    total_assigned: int | None = None
    total_completed: int | None = None
    total_failed: int | None = None
    average_task_duration_ms: int | None = None
    affinity_tag: str | None = None
    priority: int | None = None


class AgentPoolResponse(AgentPoolBase):
    """Schema for Agent Pool response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
    deleted_at: str | None = None

    # Computed properties
    utilization_percent: float = 0.0
    completion_rate: float = 0.0
    is_available: bool = True


class AgentPoolListResponse(BaseModel):
    """Schema for paginated agent pool list response."""

    agents: list[AgentPoolResponse]
    total: int
    limit: int
    offset: int


class PoolMetrics(BaseModel):
    """Schema for pool-level metrics."""

    total_agents: int
    available_agents: int
    busy_agents: int
    offline_agents: int
    maintenance_agents: int
    draining_agents: int
    total_capacity: int
    used_capacity: int
    available_capacity: int
    utilization_percent: float
    average_completion_rate: float
    agents_by_type: dict[str, int]


class PoolHealthReport(BaseModel):
    """Schema for pool health report."""

    healthy: bool
    metrics: PoolMetrics
    issues: list[str]
    recommendations: list[str]
    stale_agents: list[AgentPoolResponse]
    overloaded_agents: list[AgentPoolResponse]


class ScalingRecommendation(BaseModel):
    """Schema for auto-scaling recommendation."""

    action: ScalingAction
    current_count: int
    recommended_count: int
    delta: int
    reason: str
    metrics: PoolMetrics


class ScalingPolicy(BaseModel):
    """Schema for auto-scaling policy configuration."""

    min_agents: int = 1
    max_agents: int = 10
    scale_up_threshold: float = 80.0  # utilization percent
    scale_down_threshold: float = 20.0  # utilization percent
    scale_up_cooldown_minutes: int = 5
    scale_down_cooldown_minutes: int = 10
    stale_agent_timeout_minutes: int = 5
    enable_auto_scaling: bool = False


class ScalingEventCreate(BaseModel):
    """Schema for creating a scaling event log."""

    action: ScalingAction
    previous_count: int
    new_count: int
    reason: str
    metadata: dict[str, Any] = {}


class ScalingEventResponse(BaseModel):
    """Schema for scaling event response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: ScalingAction
    previous_count: int
    new_count: int
    reason: str
    metadata: dict[str, Any]
    created_at: str


class AgentAssignRequest(BaseModel):
    """Schema for agent assignment request."""

    project_id: uuid.UUID
    agent_type: AgentType | None = None
    capabilities: list[str] = []
    affinity_tag: str | None = None
    preferred_agent_id: str | None = None


class AgentAssignResponse(BaseModel):
    """Schema for agent assignment response."""

    success: bool
    agent: AgentPoolResponse | None = None
    message: str | None = None


class AgentHeartbeatRequest(BaseModel):
    """Schema for agent heartbeat update."""

    agent_id: str
    current_load: int | None = None
    current_project_id: uuid.UUID | None = None
    metadata: dict[str, Any] = {}
