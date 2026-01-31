"""Query API endpoint for event filtering and error aggregation.

Provides GET /api/query endpoint with filters for session_id, event_type,
and date_range. Includes error aggregation by session and frequency tracking.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, and_, cast, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from db.connection import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.session import Session


router = APIRouter(prefix="/api/query", tags=["query"])


@router.get("/events")
async def query_events(
    session_id: str | None = Query(None, description="Filter by session ID"),
    event_type: str | None = Query(None, description="Filter by event type"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Query events with optional filters.

    Args:
        session_id: Filter by session UUID
        event_type: Filter by event type (e.g., 'error', 'spec_fail')
        start_date: Start date filter (ISO 8601 format)
        end_date: End date filter (ISO 8601 format)
        limit: Maximum number of results (1-1000)
        offset: Pagination offset
        session: Database session

    Returns:
        Dictionary with events list, total count, and filters applied
    """
    query: Select[tuple[Event]] = select(Event).order_by(Event.created_at.desc())

    filters_applied: list[str] = []

    # Apply session_id filter
    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            query = query.where(Event.session_id == session_uuid)
            filters_applied.append(f"session_id={session_id}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

    # Apply event_type filter
    if event_type:
        query = query.where(Event.event_type == event_type)
        filters_applied.append(f"event_type={event_type}")

    # Apply date range filter
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Event.created_at >= start_dt)
            filters_applied.append(f"start_date={start_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Event.created_at <= end_dt)
            filters_applied.append(f"end_date={end_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": str(event.id),
                "session_id": str(event.session_id),
                "event_type": event.event_type,
                "data": event.data,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "filters_applied": filters_applied,
    }


@router.get("/errors")
async def query_errors(
    session_id: str | None = Query(None, description="Filter by session ID"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Query error events specifically.

    Returns events with event_type 'error' or 'spec_fail'.

    Args:
        session_id: Filter by session UUID
        start_date: Start date filter (ISO 8601 format)
        end_date: End date filter (ISO 8601 format)
        limit: Maximum number of results (1-1000)
        offset: Pagination offset
        session: Database session

    Returns:
        Dictionary with error events and metadata
    """
    query: Select[tuple[Event]] = select(Event).where(
        Event.event_type.in_(["error", "spec_fail"])
    ).order_by(Event.created_at.desc())

    filters_applied: list[str] = ["event_type in (error, spec_fail)"]

    # Apply session_id filter
    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            query = query.where(Event.session_id == session_uuid)
            filters_applied.append(f"session_id={session_id}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

    # Apply date range filter
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Event.created_at >= start_dt)
            filters_applied.append(f"start_date={start_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Event.created_at <= end_dt)
            filters_applied.append(f"end_date={end_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(query)
    events = result.scalars().all()

    return {
        "errors": [
            {
                "id": str(event.id),
                "session_id": str(event.session_id),
                "event_type": event.event_type,
                "message": event.data.get("error") or event.data.get("message", "Unknown error"),
                "stack_trace": event.data.get("stack_trace"),
                "data": event.data,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "filters_applied": filters_applied,
    }


@router.get("/errors/aggregated")
async def get_error_aggregation(
    session_id: str | None = Query(None, description="Filter by session ID"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get error aggregation grouped by session.

    Returns error counts and statistics grouped by session.

    Args:
        session_id: Filter by session UUID (if provided, returns stats for that session only)
        start_date: Start date filter (ISO 8601 format)
        end_date: End date filter (ISO 8601 format)
        session: Database session

    Returns:
        Dictionary with aggregated error statistics per session
    """
    # Base query for error events
    base_conditions = [Event.event_type.in_(["error", "spec_fail"])]

    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            base_conditions.append(Event.session_id == session_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            base_conditions.append(Event.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            base_conditions.append(Event.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Query for error counts by session
    error_counts_query = select(
        Event.session_id,
        func.count().label("error_count"),
    ).where(
        and_(*base_conditions)
    ).group_by(Event.session_id)

    error_counts_result = await session.execute(error_counts_query)
    error_counts = error_counts_result.all()

    # Query for most recent error per session
    recent_errors_query = select(Event).where(
        and_(*base_conditions)
    ).order_by(Event.created_at.desc()).distinct(Event.session_id)

    recent_errors_result = await session.execute(recent_errors_query)
    recent_errors = recent_errors_result.scalars().all()

    # Build aggregation response
    session_errors: dict[str, dict[str, Any]] = {}

    for session_id_val, count in error_counts:
        sid_str = str(session_id_val)
        session_errors[sid_str] = {
            "session_id": sid_str,
            "error_count": count,
        }

    # Add most recent error info
    for error in recent_errors:
        sid_str = str(error.session_id)
        if sid_str in session_errors:
            session_errors[sid_str]["most_recent_error"] = {
                "id": str(error.id),
                "event_type": error.event_type,
                "message": error.data.get("error") or error.data.get("message", "Unknown error"),
                "created_at": error.created_at.isoformat(),
            }

    # Calculate total errors across all sessions
    total_errors = sum(se["error_count"] for se in session_errors.values())

    # Get error frequency by type
    frequency_query = select(
        Event.event_type,
        func.count().label("count"),
    ).where(
        and_(*base_conditions)
    ).group_by(Event.event_type)

    frequency_result = await session.execute(frequency_query)
    error_frequency = {
        event_type: count for event_type, count in frequency_result.all()
    }

    return {
        "total_errors": total_errors,
        "error_frequency": error_frequency,
        "by_session": list(session_errors.values()),
        "sessions_with_errors": len(session_errors),
    }


@router.get("/errors/export")
async def export_errors_csv(
    session_id: str | None = Query(None, description="Filter by session ID"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Export errors as structured data for CSV generation.

    Returns error data in a format suitable for CSV export.

    Args:
        session_id: Filter by session UUID
        start_date: Start date filter (ISO 8601 format)
        end_date: End date filter (ISO 8601 format)
        session: Database session

    Returns:
        Dictionary with headers and rows for CSV export
    """
    query: Select[tuple[Event]] = select(Event).where(
        Event.event_type.in_(["error", "spec_fail"])
    ).order_by(Event.created_at.desc())

    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            query = query.where(Event.session_id == session_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Event.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Event.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    result = await session.execute(query)
    events = result.scalars().all()

    # Build CSV data
    headers = ["Error ID", "Session ID", "Event Type", "Message", "Created At", "Error Data"]
    rows = []
    for event in events:
        message = event.data.get("error") or event.data.get("message", "Unknown error")
        rows.append([
            str(event.id),
            str(event.session_id),
            event.event_type,
            message,
            event.created_at.isoformat(),
            str(event.data),
        ])

    return {
        "headers": headers,
        "rows": rows,
        "total_errors": len(rows),
    }


@router.get("/sessions")
async def query_sessions(
    project_name: str | None = Query(None, description="Filter by project name"),
    agent_type: str | None = Query(None, description="Filter by agent type"),
    status: str | None = Query(None, description="Filter by session status"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Query sessions with optional filters.

    Args:
        project_name: Filter by project name
        agent_type: Filter by agent type
        status: Filter by session status
        start_date: Start date filter (ISO 8601 format)
        end_date: End date filter (ISO 8601 format)
        limit: Maximum number of results (1-1000)
        offset: Pagination offset
        session: Database session

    Returns:
        Dictionary with sessions list, total count, and filters applied
    """
    query: Select[tuple[Session]] = select(Session).order_by(Session.started_at.desc())

    filters_applied: list[str] = []

    # Apply filters
    if project_name:
        query = query.where(Session.project_name == project_name)
        filters_applied.append(f"project_name={project_name}")

    if agent_type:
        query = query.where(Session.agent_type == agent_type)
        filters_applied.append(f"agent_type={agent_type}")

    if status:
        query = query.where(Session.status == status)
        filters_applied.append(f"status={status}")

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Session.started_at >= start_dt)
            filters_applied.append(f"start_date={start_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Session.started_at <= end_dt)
            filters_applied.append(f"end_date={end_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(query)
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "id": str(s.id),
                "agent_type": s.agent_type.value if s.agent_type else "unknown",
                "project_name": s.project_name,
                "status": s.status.value if s.status else "unknown",
                "metadata": s.metadata,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "filters_applied": filters_applied,
    }
