"""Agent Pool API endpoints.

Provides endpoints for managing the agent pool, including:
- Agent registration and lifecycle
- Load balancing and assignment
- Health monitoring and metrics
- Auto-scaling management
"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session

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
    ScalingEventResponse,
    AgentAssignRequest,
    AgentAssignResponse,
    AgentHeartbeatRequest,
)
from app.models.session import AgentType
from app.services.agent_pool import get_agent_pool_service
from app.services.agent_auto_scaler import get_agent_auto_scaler, ScalingEvent


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-pool", tags=["agent-pool"])

# Service instances
_pool_service = get_agent_pool_service()
_auto_scaler = get_agent_auto_scaler()


# ============================================================================
# Pool Management Endpoints
# ============================================================================


@router.get("", response_model=dict[str, Any])
async def list_agents(
    status: PoolAgentStatus | None = Query(None, description="Filter by status"),
    agent_type: AgentType | None = Query(None, description="Filter by agent type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List all agents in the pool with optional filtering.

    Returns a paginated list of agents with their current status,
    capacity, and performance metrics.
    """
    result = await _pool_service.list_agents(
        session=session,
        status=status,
        agent_type=agent_type,
        limit=limit,
        offset=offset,
    )

    return {
        "agents": [a.model_dump() for a in result.agents],
        "total": result.total,
        "limit": result.limit,
        "offset": result.offset,
    }


@router.post("", response_model=dict[str, Any], status_code=201)
async def register_agent(
    data: AgentPoolCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Register a new agent in the pool.

    Creates a new agent pool entry with the specified configuration.
    The agent_id must be unique across the pool.
    """
    try:
        agent = await _pool_service.register_agent(session=session, data=data)
        await session.commit()
        return agent.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{pool_id}", response_model=dict[str, Any])
async def get_agent(
    pool_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get an agent by pool entry ID.

    Returns detailed information about a specific agent including
    utilization, completion rate, and availability status.
    """
    agent = await _pool_service.get_agent(session=session, pool_id=pool_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.model_dump()


@router.get("/agent-id/{agent_id}", response_model=dict[str, Any])
async def get_agent_by_agent_id(
    agent_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get an agent by its external agent_id.

    Returns detailed information about a specific agent using
    its external identifier instead of the internal pool ID.
    """
    agent = await _pool_service.get_agent_by_agent_id(session=session, agent_id=agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.model_dump()


@router.patch("/{pool_id}", response_model=dict[str, Any])
async def update_agent(
    pool_id: uuid.UUID,
    data: AgentPoolUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update an agent's configuration.

    Partially update an agent's properties. Only provided fields
    will be updated. Useful for changing capacity, capabilities, or metadata.
    """
    agent = await _pool_service.update_agent(session=session, pool_id=pool_id, data=data)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()
    return agent.model_dump()


@router.delete("/{pool_id}", status_code=204)
async def unregister_agent(
    pool_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Unregister an agent from the pool (soft delete).

    Marks the agent as deleted but keeps the record for historical
    analysis. The agent will no longer appear in listings or be
    considered for assignment.
    """
    success = await _pool_service.unregister_agent(session=session, pool_id=pool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()


# ============================================================================
# Agent Control Endpoints
# ============================================================================


@router.post("/{agent_id}/status", response_model=dict[str, Any])
async def set_agent_status_by_id(
    agent_id: str,
    status: PoolAgentStatus,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Set an agent's status by external agent_id.

    Updates the agent's availability status (available, busy, offline, etc.).
    This is typically called by the agent itself during its lifecycle.
    """
    agent = await _pool_service.set_agent_status_by_agent_id(
        session=session,
        agent_id=agent_id,
        status=status,
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()
    return agent.model_dump()


@router.post("/heartbeat", response_model=dict[str, Any])
async def update_heartbeat(
    data: AgentHeartbeatRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update an agent's heartbeat.

    Called by agents to signal they are still alive and functioning.
    Automatically updates the last_heartbeat timestamp and can adjust
    the agent's status based on current load.
    """
    agent = await _pool_service.update_heartbeat(session=session, data=data)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()
    return agent.model_dump()


@router.post("/assign", response_model=dict[str, Any])
async def assign_agent(
    request: AgentAssignRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Assign an available agent to a project.

    Uses load balancing to select the best agent for the assignment.
    Factors considered include:
    - Current load (least-loaded algorithm)
    - Agent type and capabilities
    - Affinity tags for sticky sessions
    - Priority settings

    Returns the assigned agent or an error if no suitable agent is available.
    """
    result = await _pool_service.assign_agent(session=session, request=request)
    await session.commit()

    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)

    return {
        "success": result.success,
        "agent": result.agent.model_dump() if result.agent else None,
        "message": result.message,
    }


@router.post("/{agent_id}/release", response_model=dict[str, Any])
async def release_agent_by_id(
    agent_id: str,
    completed: bool = Query(True, description="Whether the task completed successfully"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Release an agent from its current assignment.

    Decrements the agent's current load and updates completion statistics.
    If the agent's load reaches zero, it becomes available for new assignments.
    """
    agent = await _pool_service.release_agent_by_agent_id(
        session=session,
        agent_id=agent_id,
        completed=completed,
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()
    return agent.model_dump()


# ============================================================================
# Metrics Endpoints
# ============================================================================


@router.get("/metrics/summary", response_model=dict[str, Any])
async def get_pool_metrics(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get aggregate metrics for the agent pool.

    Returns pool-level statistics including:
    - Total, available, busy, offline agents
    - Total and used capacity
    - Utilization percentage
    - Average completion rate
    - Agent counts by type
    """
    metrics = await _pool_service.get_pool_metrics(session=session)
    return metrics.model_dump()


@router.get("/metrics/health", response_model=dict[str, Any])
async def get_health_report(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get comprehensive health report for the agent pool.

    Returns detailed health information including:
    - Overall health status
    - Pool metrics
    - Detected issues (stale agents, overload, etc.)
    - Recommendations for scaling or maintenance
    - Lists of stale and overloaded agents
    """
    report = await _pool_service.get_health_report(session=session)
    return {
        "healthy": report.healthy,
        "metrics": report.metrics.model_dump(),
        "issues": report.issues,
        "recommendations": report.recommendations,
        "stale_agents": [a.model_dump() for a in report.stale_agents],
        "overloaded_agents": [a.model_dump() for a in report.overloaded_agents],
    }


# ============================================================================
# Auto-Scaling Endpoints
# ============================================================================


@router.get("/scaling/recommendation", response_model=dict[str, Any])
async def get_scaling_recommendation(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a scaling recommendation based on current pool metrics.

    Analyzes the pool and recommends whether to scale up, scale down,
    or take no action. Includes reasoning and current metrics.
    """
    recommendation = await _auto_scaler.get_scaling_recommendation(session=session)
    return recommendation.model_dump()


@router.post("/scaling/execute", response_model=dict[str, Any])
async def execute_scaling(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute a scaling action based on current recommendation.

    Records the scaling event and updates the scaling history.
    Note: Actual agent spawning/termination is handled by external systems.
    """
    recommendation = await _auto_scaler.get_scaling_recommendation(session=session)
    event = await _auto_scaler.execute_scaling(session=session, recommendation=recommendation)
    return {
        "id": str(event.id),
        "action": event.action.value,
        "previous_count": event.previous_count,
        "new_count": event.new_count,
        "reason": event.reason,
        "metadata": event.metadata,
        "created_at": event.created_at.isoformat(),
    }


@router.get("/scaling/history", response_model=dict[str, Any])
async def get_scaling_history(
    limit: int = Query(50, ge=1, le=500, description="Maximum events to return"),
) -> dict[str, Any]:
    """Get history of scaling events.

    Returns a list of past scaling actions including the action taken,
    agent count changes, reasons, and timestamps.
    """
    events = await _auto_scaler.get_scaling_history(limit=limit)
    return {
        "events": [
            {
                "id": str(e.id),
                "action": e.action.value,
                "previous_count": e.previous_count,
                "new_count": e.new_count,
                "reason": e.reason,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
    }


@router.get("/scaling/policy", response_model=dict[str, Any])
async def get_scaling_policy() -> dict[str, Any]:
    """Get the current auto-scaling policy configuration.

    Returns the scaling thresholds, cooldowns, and limits that
    determine when and how the pool scales automatically.
    """
    policy = _auto_scaler.get_policy()
    return policy.model_dump()


@router.post("/scaling/policy", response_model=dict[str, Any])
async def update_scaling_policy(
    policy: ScalingPolicy,
) -> dict[str, Any]:
    """Update the auto-scaling policy configuration.

    Updates the scaling policy with new thresholds, cooldowns, or limits.
    Changes take effect on the next monitoring cycle.
    """
    _auto_scaler.set_policy(policy=policy)
    return policy.model_dump()


@router.post("/scaling/start", status_code=202)
async def start_scaling_monitoring(
    interval_seconds: int = Query(60, ge=10, le=600, description="Monitoring interval in seconds"),
) -> dict[str, Any]:
    """Start auto-scaling monitoring.

    Begins the background monitoring loop that periodically checks
    pool metrics and executes scaling actions when needed.
    """
    await _auto_scaler.start_monitoring(interval_seconds=interval_seconds)
    return {
        "status": "started",
        "interval_seconds": interval_seconds,
        "message": "Auto-scaling monitoring started",
    }


@router.post("/scaling/stop", status_code=202)
async def stop_scaling_monitoring() -> dict[str, Any]:
    """Stop auto-scaling monitoring.

    Stops the background monitoring loop. Scaling can still be
    triggered manually via the execute endpoint.
    """
    await _auto_scaler.stop_monitoring()
    return {
        "status": "stopped",
        "message": "Auto-scaling monitoring stopped",
    }
