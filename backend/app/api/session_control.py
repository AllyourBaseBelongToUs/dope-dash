"""Session Control API endpoints.

Provides endpoints for controlling session lifecycle:
- Pause/resume running sessions
- Abort sessions (terminal state)
- Reassign sessions to different agents
"""
import logging
import uuid
from datetime import datetime, timezone
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
    from sqlalchemy import update
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
        # Use SELECT FOR UPDATE to prevent race conditions
        # This locks the agent row until the transaction completes
        agent_result = await session.execute(
            select(AgentPool)
            .where(
                AgentPool.agent_id == new_agent_id,
                AgentPool.deleted_at.is_(None),
            )
            .with_for_update()
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

        # CRITICAL: Check capacity AFTER acquiring lock
        if agent.current_load >= agent.max_capacity:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{new_agent_id}' is at full capacity ({agent.current_load}/{agent.max_capacity})"
            )

        # Get the old agent ID from metadata
        old_agent_id = db_session.meta_data.get("assigned_agent_id") if db_session.meta_data else None

        # Decrement old agent's load if different from new agent
        if old_agent_id and old_agent_id != new_agent_id:
            old_agent_result = await session.execute(
                select(AgentPool)
                .where(AgentPool.agent_id == old_agent_id)
                .with_for_update()
            )
            old_agent = old_agent_result.scalar_one_or_none()
            if old_agent and old_agent.current_load > 0:
                old_agent.current_load -= 1
                # If load drops to zero and agent was busy, set to available
                if old_agent.current_load == 0 and old_agent.status == PoolAgentStatus.BUSY:
                    old_agent.status = PoolAgentStatus.AVAILABLE

        # Increment new agent's load (we already verified capacity above)
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
    metadata["last_reassigned_at"] = datetime.now(timezone.utc).isoformat()
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


# ============================================================================
# Handoff Endpoints
# ============================================================================

@router.get("/{session_id}/handoff", response_model=dict[str, Any])
async def get_session_handoff(
    session_id: uuid.UUID,
    handoff_id: str | None = Query(None, description="Specific handoff ID to retrieve"),
    format: str = Query("json", description="Output format: json or markdown"),
) -> dict[str, Any]:
    """Get handoff context for a session transfer.

    Retrieves handoff context that captures the session state for
    seamless transfer to another agent.

    Args:
        session_id: UUID of the session
        handoff_id: Optional specific handoff ID to retrieve
        format: Output format (json or markdown)

    Returns:
        Handoff context in requested format

    Raises:
        HTTPException: If session or handoff not found
    """
    from app.services.agent_handoff import get_agent_handoff_service

    service = get_agent_handoff_service()

    if handoff_id:
        if format == "markdown":
            markdown = await service.get_handoff_markdown(handoff_id)
            if not markdown:
                raise HTTPException(status_code=404, detail="Handoff not found")
            return {"handoff_id": handoff_id, "format": "markdown", "content": markdown}
        else:
            context = await service.get_handoff(handoff_id)
            if not context:
                raise HTTPException(status_code=404, detail="Handoff not found")
            return {"handoff_id": handoff_id, "format": "json", "context": context.to_dict()}

    # List handoffs for this session
    handoffs = await service.list_handoffs(session_id=str(session_id))

    if not handoffs:
        raise HTTPException(status_code=404, detail="No handoffs found for this session")

    return {
        "session_id": str(session_id),
        "handoffs": handoffs,
        "count": len(handoffs),
    }


@router.post("/{session_id}/handoff", response_model=dict[str, Any])
async def create_session_handoff(
    session_id: uuid.UUID,
    target_agent_type: AgentType = Query(..., description="Target agent type"),
    target_agent_id: str = Query(..., description="Target agent ID"),
    summary: str = Query(..., description="Summary of work done so far", min_length=1, max_length=2000),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a handoff context for session transfer.

    Creates a handoff context that captures the current session state
    for seamless transfer to another agent. This is typically called
    before reassigning a session.

    Args:
        session_id: UUID of the session
        target_agent_type: Type of agent to hand off to
        target_agent_id: ID of the target agent
        summary: Summary of work done so far (1-2000 chars)
        session: Database session

    Returns:
        Created handoff context

    Raises:
        HTTPException: If session not found
    """
    from app.services.agent_handoff import get_agent_handoff_service

    db_session = await session.get(Session, session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate target_agent_id format (basic sanitization)
    if not target_agent_id or len(target_agent_id) > 255:
        raise HTTPException(
            status_code=400,
            detail="target_agent_id must be 1-255 characters"
        )

    service = get_agent_handoff_service()

    # Get source agent info from session metadata
    metadata = db_session.meta_data or {}
    source_agent_id = metadata.get("assigned_agent_id", db_session.agent_type.value)

    try:
        context = await service.create_handoff(
            session_id=str(session_id),
            source_agent_type=db_session.agent_type.value,
            source_agent_id=source_agent_id,
            target_agent_type=target_agent_type.value,
            target_agent_id=target_agent_id,
            summary=summary,
        )
    except OSError as e:
        logger.error(f"Failed to store handoff for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create handoff document"
        )

    logger.info(f"Created handoff for session {session_id}: {source_agent_id} → {target_agent_id}")

    return {
        "handoff_id": context.id,
        "session_id": str(session_id),
        "source_agent_type": context.source_agent_type,
        "source_agent_id": context.source_agent_id,
        "target_agent_type": context.target_agent_type,
        "target_agent_id": context.target_agent_id,
        "summary": context.summary,
        "files_modified_count": len(context.files_modified),
        "pending_tasks_count": len(context.pending_tasks),
        "created_at": context.created_at.isoformat(),
    }


@router.get("/handoffs", response_model=dict[str, Any])
async def list_handoffs(
    session_id: str | None = Query(None, description="Filter by session ID"),
    source_agent_id: str | None = Query(None, description="Filter by source agent"),
    target_agent_id: str | None = Query(None, description="Filter by target agent"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
) -> dict[str, Any]:
    """List handoff contexts with optional filtering.

    Lists all handoff contexts, optionally filtered by session or agent.

    Args:
        session_id: Filter by session ID
        source_agent_id: Filter by source agent
        target_agent_id: Filter by target agent
        limit: Maximum number of results

    Returns:
        List of handoff metadata
    """
    from app.services.agent_handoff import get_agent_handoff_service

    service = get_agent_handoff_service()

    handoffs = await service.list_handoffs(
        session_id=session_id,
        source_agent_id=source_agent_id,
        target_agent_id=target_agent_id,
        limit=limit,
    )

    return {
        "handoffs": handoffs,
        "count": len(handoffs),
        "filters": {
            "session_id": session_id,
            "source_agent_id": source_agent_id,
            "target_agent_id": target_agent_id,
        },
    }


@router.get("/handoffs/{handoff_id}", response_model=dict[str, Any])
async def get_handoff_by_id(
    handoff_id: str,
    format: str = Query("json", description="Output format: json or markdown"),
) -> dict[str, Any]:
    """Get a specific handoff context by ID.

    Retrieves the full handoff context in the specified format.

    Args:
        handoff_id: The handoff identifier
        format: Output format (json or markdown)

    Returns:
        Handoff context in requested format

    Raises:
        HTTPException: If handoff not found
    """
    from app.services.agent_handoff import get_agent_handoff_service

    service = get_agent_handoff_service()

    if format == "markdown":
        markdown = await service.get_handoff_markdown(handoff_id)
        if not markdown:
            raise HTTPException(status_code=404, detail="Handoff not found")
        return {"handoff_id": handoff_id, "format": "markdown", "content": markdown}
    else:
        context = await service.get_handoff(handoff_id)
        if not context:
            raise HTTPException(status_code=404, detail="Handoff not found")
        return {"handoff_id": handoff_id, "format": "json", "context": context.to_dict()}
