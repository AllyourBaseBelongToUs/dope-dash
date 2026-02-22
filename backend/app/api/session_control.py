"""Session Control API endpoints.

Provides endpoints for controlling session lifecycle:
- Pause/resume running sessions
- Abort sessions (terminal state)
- Reassign sessions to different agents
"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session
from app.models.session import Session, SessionStatus, AgentType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["session-control"])


@router.post("/{session_id}/pause", response_model=dict[str, Any])
async def pause_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Pause a running session.

    Pauses the session execution. The session can be resumed later.
    Only RUNNING sessions can be paused.

    Args:
        session_id: UUID of the session to pause
        session: Database session

    Returns:
        Updated session information

    Raises:
        HTTPException: If session not found or not in RUNNING state
    """
    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.status != SessionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause session in {db_session.status.value} state"
        )

    db_session.status = SessionStatus.PAUSED
    await session.commit()
    await session.refresh(db_session)

    logger.info(f"Session {session_id} paused")

    return {
        "id": str(db_session.id),
        "status": db_session.status.value,
        "message": "Session paused successfully",
    }


@router.post("/{session_id}/resume", response_model=dict[str, Any])
async def resume_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Resume a paused session.

    Resumes execution of a previously paused session.
    Only PAUSED sessions can be resumed.

    Args:
        session_id: UUID of the session to resume
        session: Database session

    Returns:
        Updated session information

    Raises:
        HTTPException: If session not found or not in PAUSED state
    """
    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.status != SessionStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume session in {db_session.status.value} state"
        )

    db_session.status = SessionStatus.RUNNING
    await session.commit()
    await session.refresh(db_session)

    logger.info(f"Session {session_id} resumed")

    return {
        "id": str(db_session.id),
        "status": db_session.status.value,
        "message": "Session resumed successfully",
    }


@router.post("/{session_id}/abort", response_model=dict[str, Any])
async def abort_session(
    session_id: uuid.UUID,
    reason: str | None = Query(None, description="Optional reason for aborting"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Abort a session (terminal state).

    Aborts the session execution. This is a terminal state -
    the session cannot be resumed after being aborted.
    Only RUNNING or PAUSED sessions can be aborted.

    Args:
        session_id: UUID of the session to abort
        reason: Optional reason for aborting
        session: Database session

    Returns:
        Updated session information

    Raises:
        HTTPException: If session not found or in terminal state
    """
    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED, SessionStatus.ABORTED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot abort session in terminal state {db_session.status.value}"
        )

    db_session.status = SessionStatus.ABORTED

    # Store reason in metadata
    if reason:
        metadata = db_session.meta_data or {}
        metadata["abort_reason"] = reason
        db_session.meta_data = metadata

    await session.commit()
    await session.refresh(db_session)

    logger.info(f"Session {session_id} aborted" + (f": {reason}" if reason else ""))

    return {
        "id": str(db_session.id),
        "status": db_session.status.value,
        "message": "Session aborted successfully",
        "reason": reason,
    }


@router.post("/{session_id}/reassign", response_model=dict[str, Any])
async def reassign_session(
    session_id: uuid.UUID,
    new_agent_type: AgentType | None = Query(None, description="New agent type to assign"),
    new_agent_id: str | None = Query(None, description="Specific agent ID to assign to"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reassign a session to a different agent.

    Reassigns the session to run on a different agent.
    Only PAUSED or RUNNING sessions can be reassigned.

    This endpoint:
    - Validates the target agent exists and is available
    - Updates agent pool loads (decrements old, increments new)
    - Tracks reassignment history in session metadata

    Args:
        session_id: UUID of the session to reassign
        new_agent_type: Type of agent to reassign to
        new_agent_id: Specific agent ID to reassign to
        session: Database session

    Returns:
        Updated session information

    Raises:
        HTTPException: If session not found, not in valid state, or agent unavailable
    """
    from app.models.agent_pool import AgentPool, PoolAgentStatus

    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.status not in (SessionStatus.PAUSED, SessionStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reassign session in {db_session.status.value} state. Pause first."
        )

    # CRITICAL: Store previous type BEFORE any updates
    previous_agent_type = db_session.agent_type.value

    # Validate and update agent pool if specifying a specific agent
    if new_agent_id:
        # Check if the new agent exists and is available
        agent_result = await session.execute(
            select(AgentPool).where(
                AgentPool.agent_id == new_agent_id,
                AgentPool.deleted_at.is_(None),
            )
        )
        agent = agent_result.scalar_one_or_none()

        if not agent:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{new_agent_id}' not found in pool"
            )

        if agent.status not in (PoolAgentStatus.AVAILABLE, PoolAgentStatus.BUSY):
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{new_agent_id}' is {agent.status.value} (must be available or busy)"
            )

        # Get the old agent ID from metadata
        old_agent_id = db_session.meta_data.get("assigned_agent_id") if db_session.meta_data else None

        # Decrement old agent's load if different from new agent
        if old_agent_id and old_agent_id != new_agent_id:
            old_agent_result = await session.execute(
                select(AgentPool).where(AgentPool.agent_id == old_agent_id)
            )
            old_agent = old_agent_result.scalar_one_or_none()
            if old_agent and old_agent.current_load > 0:
                old_agent.current_load -= 1
                # If load drops to zero and agent was busy, set to available
                if old_agent.current_load == 0 and old_agent.status == PoolAgentStatus.BUSY:
                    old_agent.status = PoolAgentStatus.AVAILABLE

        # Increment new agent's load
        if agent.current_load < agent.max_capacity:
            agent.current_load += 1
            # Update status to BUSY if at capacity
            if agent.current_load >= agent.max_capacity:
                agent.status = PoolAgentStatus.BUSY

        # Increment total_assigned for the new agent
        agent.total_assigned += 1

    # Update agent type if specified
    if new_agent_type:
        db_session.agent_type = new_agent_type

    # Store reassignment info in metadata with CORRECT previous type
    metadata = db_session.meta_data or {}
    metadata["reassigned"] = True
    metadata["previous_agent_type"] = previous_agent_type  # FIXED: Store actual previous type
    if new_agent_id:
        metadata["assigned_agent_id"] = new_agent_id
    db_session.meta_data = metadata

    await session.commit()
    await session.refresh(db_session)

    logger.info(f"Session {session_id} reassigned to {new_agent_type or 'same type'} (agent: {new_agent_id or 'any'})")

    return {
        "id": str(db_session.id),
        "status": db_session.status.value,
        "agent_type": db_session.agent_type.value,
        "message": "Session reassigned successfully",
        "assigned_agent_id": new_agent_id,
        "previous_agent_type": previous_agent_type,
    }


@router.get("/{session_id}/status", response_model=dict[str, Any])
async def get_session_status(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get the current status of a session.

    Args:
        session_id: UUID of the session
        session: Database session

    Returns:
        Session status information

    Raises:
        HTTPException: If session not found
    """
    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": str(db_session.id),
        "status": db_session.status.value,
        "agent_type": db_session.agent_type.value,
        "project_name": db_session.project_name,
        "can_pause": db_session.status == SessionStatus.RUNNING,
        "can_resume": db_session.status == SessionStatus.PAUSED,
        "can_abort": db_session.status in (SessionStatus.RUNNING, SessionStatus.PAUSED),
        "can_reassign": db_session.status in (SessionStatus.RUNNING, SessionStatus.PAUSED),
    }
