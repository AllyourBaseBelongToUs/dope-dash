"""Agent pool service for distributed agent management with load balancing.

This service provides:
- Agent registration and lifecycle management
- Load balancing using least-loaded algorithm
- Health monitoring via heartbeats
- Capacity tracking and enforcement
- Agent assignment with affinity support
- Pool metrics and health reporting
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent_pool import (
    AgentPool,
    PoolAgentStatus,
    AgentPoolCreate,
    AgentPoolUpdate,
    AgentPoolResponse,
    AgentPoolListResponse,
    PoolMetrics,
    PoolHealthReport,
    AgentAssignRequest,
    AgentAssignResponse,
    AgentHeartbeatRequest,
)
from app.models.session import AgentType


logger = logging.getLogger(__name__)


class AgentPoolService:
    """Service for managing agent pool with load balancing.

    This service handles agent registration, assignment, health monitoring,
    and provides metrics for auto-scaling decisions.
    """

    def __init__(self, heartbeat_timeout_seconds: int = 300) -> None:
        """Initialize the agent pool service.

        Args:
            heartbeat_timeout_seconds: Seconds before considering agent stale
        """
        self._heartbeat_timeout = timedelta(seconds=heartbeat_timeout_seconds)

    async def register_agent(
        self,
        session: AsyncSession,
        data: AgentPoolCreate,
    ) -> AgentPoolResponse:
        """Register a new agent in the pool.

        Args:
            session: Database session
            data: Agent registration data

        Returns:
            Registered agent response

        Raises:
            ValueError: If agent_id already exists
        """
        # Check if agent already exists
        existing = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.agent_id == data.agent_id,
                    AgentPool.deleted_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Agent with id '{data.agent_id}' already registered")

        # Create new agent
        agent = AgentPool(
            agent_id=data.agent_id,
            agent_type=data.agent_type,
            status=data.status or PoolAgentStatus.AVAILABLE,
            current_project_id=data.current_project_id,
            current_load=data.current_load,
            max_capacity=data.max_capacity,
            capabilities=data.capabilities,
            metadata=data.metadata,
            pid=data.pid,
            working_dir=data.working_dir,
            command=data.command,
            tmux_session=data.tmux_session,
            last_heartbeat=datetime.fromisoformat(data.last_heartbeat) if data.last_heartbeat else None,
            total_assigned=data.total_assigned,
            total_completed=data.total_completed,
            total_failed=data.total_failed,
            average_task_duration_ms=data.average_task_duration_ms,
            affinity_tag=data.affinity_tag,
            priority=data.priority,
        )

        session.add(agent)
        await session.flush()
        await session.refresh(agent)

        logger.info(f"Registered agent in pool: {agent.agent_id} ({agent.agent_type.value})")
        return self._to_response(agent)

    async def unregister_agent(
        self,
        session: AsyncSession,
        pool_id: uuid.UUID,
    ) -> bool:
        """Unregister an agent from the pool (soft delete).

        Args:
            session: Database session
            pool_id: Pool entry ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        agent = await session.get(AgentPool, pool_id)
        if agent is None or agent.deleted_at is not None:
            return False

        agent.soft_delete()
        logger.info(f"Unregistered agent from pool: {agent.agent_id}")
        return True

    async def unregister_by_agent_id(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> bool:
        """Unregister an agent by its external agent_id.

        Args:
            session: Database session
            agent_id: External agent ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        result = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.agent_id == agent_id,
                    AgentPool.deleted_at.is_(None),
                )
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return False

        agent.soft_delete()
        logger.info(f"Unregistered agent from pool: {agent_id}")
        return True

    async def get_agent(
        self,
        session: AsyncSession,
        pool_id: uuid.UUID,
    ) -> AgentPoolResponse | None:
        """Get an agent by pool ID.

        Args:
            session: Database session
            pool_id: Pool entry ID

        Returns:
            Agent response or None if not found
        """
        agent = await session.get(AgentPool, pool_id)
        if agent is None or agent.deleted_at is not None:
            return None
        return self._to_response(agent)

    async def get_agent_by_agent_id(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> AgentPoolResponse | None:
        """Get an agent by its external agent_id.

        Args:
            session: Database session
            agent_id: External agent ID

        Returns:
            Agent response or None if not found
        """
        result = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.agent_id == agent_id,
                    AgentPool.deleted_at.is_(None),
                )
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None
        return self._to_response(agent)

    async def list_agents(
        self,
        session: AsyncSession,
        status: PoolAgentStatus | None = None,
        agent_type: AgentType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AgentPoolListResponse:
        """List agents in the pool with filtering.

        Args:
            session: Database session
            status: Filter by status (optional)
            agent_type: Filter by agent type (optional)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Paginated list of agents
        """
        query = select(AgentPool).where(AgentPool.deleted_at.is_(None))

        if status is not None:
            query = query.where(AgentPool.status == status)
        if agent_type is not None:
            query = query.where(AgentPool.agent_type == agent_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(AgentPool.priority.desc(), AgentPool.created_at)
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        agents = result.scalars().all()

        return AgentPoolListResponse(
            agents=[self._to_response(a) for a in agents],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_agent(
        self,
        session: AsyncSession,
        pool_id: uuid.UUID,
        data: AgentPoolUpdate,
    ) -> AgentPoolResponse | None:
        """Update an agent in the pool.

        Args:
            session: Database session
            pool_id: Pool entry ID
            data: Update data

        Returns:
            Updated agent response or None if not found
        """
        agent = await session.get(AgentPool, pool_id)
        if agent is None or agent.deleted_at is not None:
            return None

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "last_heartbeat" and value is not None:
                setattr(agent, field, datetime.fromisoformat(value))
            else:
                setattr(agent, field, value)

        await session.flush()
        await session.refresh(agent)

        return self._to_response(agent)

    async def set_agent_status(
        self,
        session: AsyncSession,
        pool_id: uuid.UUID,
        status: PoolAgentStatus,
    ) -> AgentPoolResponse | None:
        """Set an agent's status.

        Args:
            session: Database session
            pool_id: Pool entry ID
            status: New status

        Returns:
            Updated agent response or None if not found
        """
        agent = await session.get(AgentPool, pool_id)
        if agent is None or agent.deleted_at is not None:
            return None

        agent.status = status
        await session.flush()
        await session.refresh(agent)

        return self._to_response(agent)

    async def set_agent_status_by_agent_id(
        self,
        session: AsyncSession,
        agent_id: str,
        status: PoolAgentStatus,
    ) -> AgentPoolResponse | None:
        """Set an agent's status by external agent_id.

        Args:
            session: Database session
            agent_id: External agent ID
            status: New status

        Returns:
            Updated agent response or None if not found
        """
        result = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.agent_id == agent_id,
                    AgentPool.deleted_at.is_(None),
                )
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None

        agent.status = status
        await session.flush()
        await session.refresh(agent)

        return self._to_response(agent)

    async def update_heartbeat(
        self,
        session: AsyncSession,
        data: AgentHeartbeatRequest,
    ) -> AgentPoolResponse | None:
        """Update an agent's heartbeat.

        Args:
            session: Database session
            data: Heartbeat data

        Returns:
            Updated agent response or None if not found
        """
        result = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.agent_id == data.agent_id,
                    AgentPool.deleted_at.is_(None),
                )
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None

        # Update heartbeat timestamp
        agent.last_heartbeat = datetime.now(timezone.utc)

        # Update load if provided
        if data.current_load is not None:
            agent.current_load = data.current_load

        # Update project if provided
        if data.current_project_id is not None:
            agent.current_project_id = data.current_project_id

        # Merge metadata
        if data.metadata:
            agent.metadata.update(data.metadata)

        # Auto-update status based on load
        if agent.current_load >= agent.max_capacity:
            agent.status = PoolAgentStatus.BUSY
        elif agent.status == PoolAgentStatus.BUSY and agent.current_load < agent.max_capacity:
            agent.status = PoolAgentStatus.AVAILABLE

        await session.flush()
        await session.refresh(agent)

        return self._to_response(agent)

    async def assign_agent(
        self,
        session: AsyncSession,
        request: AgentAssignRequest,
    ) -> AgentAssignResponse:
        """Assign an agent to a project using load balancing.

        Load balancing strategy (in order):
        1. If preferred_agent_id specified, use that agent if available
        2. If affinity_tag specified, look for agent with same tag already assigned to project
        3. Use least-loaded algorithm (agent with lowest current_load/max_capacity ratio)
        4. Filter by agent_type and capabilities if specified

        Args:
            session: Database session
            request: Assignment request

        Returns:
            Assignment response with agent or error message
        """
        # Build query for available agents
        query = select(AgentPool).where(
            and_(
                AgentPool.deleted_at.is_(None),
                AgentPool.status == PoolAgentStatus.AVAILABLE,
                AgentPool.current_load < AgentPool.max_capacity,
            )
        )

        # Filter by agent type if specified
        if request.agent_type is not None:
            query = query.where(AgentPool.agent_type == request.agent_type)

        # Filter by capabilities if specified
        if request.capabilities:
            # Check if all required capabilities are in agent's capabilities
            for cap in request.capabilities:
                query = query.where(AgentPool.capabilities.contains([cap]))

        # Try preferred agent first
        if request.preferred_agent_id:
            preferred_query = query.where(AgentPool.agent_id == request.preferred_agent_id)
            result = await session.execute(preferred_query)
            agent = result.scalar_one_or_none()
            if agent:
                return await self._do_assign(session, agent, request.project_id)

        # Try affinity (agent already working on this project)
        if request.affinity_tag:
            affinity_query = query.where(
                and_(
                    AgentPool.affinity_tag == request.affinity_tag,
                    AgentPool.current_project_id == request.project_id,
                )
            )
            result = await session.execute(affinity_query.order_by(AgentPool.current_load))
            agent = result.scalar_one_or_none()
            if agent:
                return await self._do_assign(session, agent, request.project_id)

        # Least-loaded selection: order by current_load, then by priority
        query = query.order_by(AgentPool.current_load, AgentPool.priority.desc())
        result = await session.execute(query)
        agent = result.scalar_one_or_none()

        if agent is None:
            return AgentAssignResponse(
                success=False,
                agent=None,
                message="No available agents matching criteria",
            )

        return await self._do_assign(session, agent, request.project_id)

    async def _do_assign(
        self,
        session: AsyncSession,
        agent: AgentPool,
        project_id: uuid.UUID,
    ) -> AgentAssignResponse:
        """Perform the actual agent assignment.

        Args:
            session: Database session
            agent: Agent to assign
            project_id: Project ID to assign to

        Returns:
            Assignment response
        """
        # Update agent
        agent.current_project_id = project_id
        agent.current_load += 1
        agent.total_assigned += 1

        # Update status if at capacity
        if agent.current_load >= agent.max_capacity:
            agent.status = PoolAgentStatus.BUSY

        await session.flush()
        await session.refresh(agent)

        logger.info(f"Assigned agent {agent.agent_id} to project {project_id}")
        return AgentAssignResponse(
            success=True,
            agent=self._to_response(agent),
        )

    async def release_agent(
        self,
        session: AsyncSession,
        pool_id: uuid.UUID,
        completed: bool = True,
    ) -> AgentPoolResponse | None:
        """Release an agent from its current assignment.

        Args:
            session: Database session
            pool_id: Pool entry ID
            completed: Whether the task completed successfully

        Returns:
            Updated agent response or None if not found
        """
        agent = await session.get(AgentPool, pool_id)
        if agent is None or agent.deleted_at is not None:
            return None

        # Update load and stats
        if agent.current_load > 0:
            agent.current_load -= 1
        if completed:
            agent.total_completed += 1
        else:
            agent.total_failed += 1

        # Clear project if load is 0
        if agent.current_load == 0:
            agent.current_project_id = None
            if agent.status == PoolAgentStatus.BUSY:
                agent.status = PoolAgentStatus.AVAILABLE

        await session.flush()
        await session.refresh(agent)

        logger.info(f"Released agent {agent.agent_id}")
        return self._to_response(agent)

    async def release_agent_by_agent_id(
        self,
        session: AsyncSession,
        agent_id: str,
        completed: bool = True,
    ) -> AgentPoolResponse | None:
        """Release an agent by its external agent_id.

        Args:
            session: Database session
            agent_id: External agent ID
            completed: Whether the task completed successfully

        Returns:
            Updated agent response or None if not found
        """
        result = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.agent_id == agent_id,
                    AgentPool.deleted_at.is_(None),
                )
            )
        )
        agent = result.scalar_one_or_none()
        if agent is None:
            return None

        # Update load and stats
        if agent.current_load > 0:
            agent.current_load -= 1
        if completed:
            agent.total_completed += 1
        else:
            agent.total_failed += 1

        # Clear project if load is 0
        if agent.current_load == 0:
            agent.current_project_id = None
            if agent.status == PoolAgentStatus.BUSY:
                agent.status = PoolAgentStatus.AVAILABLE

        await session.flush()
        await session.refresh(agent)

        logger.info(f"Released agent {agent_id}")
        return self._to_response(agent)

    async def get_pool_metrics(
        self,
        session: AsyncSession,
    ) -> PoolMetrics:
        """Get aggregate metrics for the agent pool.

        Args:
            session: Database session

        Returns:
            Pool metrics
        """
        # Get all non-deleted agents
        result = await session.execute(
            select(AgentPool).where(AgentPool.deleted_at.is_(None))
        )
        agents = result.scalars().all()

        # Calculate metrics
        total_agents = len(agents)
        available_agents = sum(1 for a in agents if a.status == PoolAgentStatus.AVAILABLE)
        busy_agents = sum(1 for a in agents if a.status == PoolAgentStatus.BUSY)
        offline_agents = sum(1 for a in agents if a.status == PoolAgentStatus.OFFLINE)
        maintenance_agents = sum(1 for a in agents if a.status == PoolAgentStatus.MAINTENANCE)
        draining_agents = sum(1 for a in agents if a.status == PoolAgentStatus.DRAINING)

        total_capacity = sum(a.max_capacity for a in agents)
        used_capacity = sum(a.current_load for a in agents)
        available_capacity = total_capacity - used_capacity

        utilization_percent = (used_capacity / total_capacity * 100) if total_capacity > 0 else 0.0

        total_assigned = sum(a.total_assigned for a in agents)
        total_completed = sum(a.total_completed for a in agents)
        average_completion_rate = (total_completed / total_assigned) if total_assigned > 0 else 0.0

        # Count by agent type
        agents_by_type: dict[str, int] = {}
        for agent in agents:
            agent_type = agent.agent_type.value
            agents_by_type[agent_type] = agents_by_type.get(agent_type, 0) + 1

        return PoolMetrics(
            total_agents=total_agents,
            available_agents=available_agents,
            busy_agents=busy_agents,
            offline_agents=offline_agents,
            maintenance_agents=maintenance_agents,
            draining_agents=draining_agents,
            total_capacity=total_capacity,
            used_capacity=used_capacity,
            available_capacity=available_capacity,
            utilization_percent=round(utilization_percent, 2),
            average_completion_rate=round(average_completion_rate, 4),
            agents_by_type=agents_by_type,
        )

    async def get_health_report(
        self,
        session: AsyncSession,
    ) -> PoolHealthReport:
        """Get comprehensive health report for the agent pool.

        Args:
            session: Database session

        Returns:
            Health report with metrics, issues, and recommendations
        """
        metrics = await self.get_pool_metrics(session)
        issues: list[str] = []
        recommendations: list[str] = []
        stale_agents: list[AgentPoolResponse] = []
        overloaded_agents: list[AgentPoolResponse] = []

        # Get all agents for detailed checks
        result = await session.execute(
            select(AgentPool).where(AgentPool.deleted_at.is_(None))
        )
        agents = result.scalars().all()

        now = datetime.now(timezone.utc)

        for agent in agents:
            # Check for stale heartbeats
            if agent.last_heartbeat:
                elapsed = now - agent.last_heartbeat
                if elapsed > self._heartbeat_timeout:
                    issues.append(f"Agent {agent.agent_id} has stale heartbeat ({elapsed.total_seconds():.0f}s old)")
                    stale_agents.append(self._to_response(agent))
                    # Auto-mark as offline
                    if agent.status != PoolAgentStatus.OFFLINE:
                        agent.status = PoolAgentStatus.OFFLINE

            # Check for overloaded agents
            if agent.current_load >= agent.max_capacity:
                overloaded_agents.append(self._to_response(agent))

        # Check overall health
        healthy = (
            metrics.offline_agents == 0
            and metrics.utilization_percent < 90
            and len(stale_agents) == 0
        )

        # Generate recommendations
        if metrics.utilization_percent > 80:
            recommendations.append("Consider scaling up - pool utilization is high")
        if metrics.utilization_percent < 20 and metrics.total_agents > 1:
            recommendations.append("Consider scaling down - pool utilization is low")
        if metrics.offline_agents > 0:
            recommendations.append(f"Check {metrics.offline_agents} offline agent(s)")
        if metrics.available_agents == 0:
            recommendations.append("No available agents - consider scaling up or checking agent health")

        return PoolHealthReport(
            healthy=healthy,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations,
            stale_agents=stale_agents,
            overloaded_agents=overloaded_agents,
        )

    def _to_response(self, agent: AgentPool) -> AgentPoolResponse:
        """Convert model to response schema.

        Args:
            agent: AgentPool model

        Returns:
            AgentPoolResponse
        """
        return AgentPoolResponse(
            id=agent.id,
            agent_id=agent.agent_id,
            agent_type=agent.agent_type,
            status=agent.status,
            current_project_id=agent.current_project_id,
            current_load=agent.current_load,
            max_capacity=agent.max_capacity,
            capabilities=agent.capabilities,
            metadata=agent.metadata,
            pid=agent.pid,
            working_dir=agent.working_dir,
            command=agent.command,
            tmux_session=agent.tmux_session,
            last_heartbeat=agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            total_assigned=agent.total_assigned,
            total_completed=agent.total_completed,
            total_failed=agent.total_failed,
            average_task_duration_ms=agent.average_task_duration_ms,
            affinity_tag=agent.affinity_tag,
            priority=agent.priority,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat(),
            deleted_at=agent.deleted_at.isoformat() if agent.deleted_at else None,
            utilization_percent=round(agent.utilization_percent, 2),
            completion_rate=round(agent.completion_rate, 4),
            is_available=agent.is_available,
        )


# Singleton instance
_agent_pool_service: AgentPoolService | None = None


def get_agent_pool_service() -> AgentPoolService:
    """Get the singleton agent pool service instance.

    Returns:
        AgentPoolService instance
    """
    global _agent_pool_service
    if _agent_pool_service is None:
        _agent_pool_service = AgentPoolService()
    return _agent_pool_service
