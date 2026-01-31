"""Analytics API endpoints for report generation.

Provides endpoints for session summaries, trends analysis, comparison,
and error aggregation needed for report generation.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, and_, func, select, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session

from app.models.event import Event
from app.models.session import Session
from app.models.metric_bucket import MetricBucket


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def calculate_duration_seconds(started_at: datetime | None, ended_at: datetime | None) -> int:
    """Calculate duration in seconds between two timestamps."""
    if started_at is None:
        return 0
    end = ended_at if ended_at else datetime.now(started_at.tzinfo)
    return int((end - started_at).total_seconds())


@router.get("/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get detailed summary of a single session for reports.

    Args:
        session_id: Session UUID
        session: Database session

    Returns:
        Dictionary with session summary including metrics, events breakdown, and spec info
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    # Get session data
    session_query = select(Session).where(Session.id == session_uuid)
    session_result = await session.execute(session_query)
    session_obj = session_result.scalar_one_or_none()

    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get event counts by type
    event_counts_query = select(
        Event.event_type,
        func.count().label("count")
    ).where(
        Event.session_id == session_uuid
    ).group_by(Event.event_type)

    event_counts_result = await session.execute(event_counts_query)
    event_type_counts = {row.event_type: row.count for row in event_counts_result.all()}

    # Get total events
    total_events_query = select(func.count()).where(Event.session_id == session_uuid)
    total_events_result = await session.execute(total_events_query)
    total_events = total_events_result.scalar() or 0

    # Get error count
    error_count_query = select(func.count()).where(
        and_(
            Event.session_id == session_uuid,
            Event.event_type.in_(["error", "spec_fail"])
        )
    )
    error_count_result = await session.execute(error_count_query)
    error_count = error_count_result.scalar() or 0

    # Get warning count (events with warning data)
    warning_count_query = select(func.count()).where(
        and_(
            Event.session_id == session_uuid,
            Event.data["warning"].astext != None
        )
    )
    warning_count_result = await session.execute(warning_count_query)
    warning_count = warning_count_result.scalar() or 0

    # Get spec info from session metadata or events
    spec_info = session_obj.meta_data.get("specs", {})
    total_specs = spec_info.get("total", 0)
    completed_specs = spec_info.get("completed", 0)
    failed_specs = spec_info.get("failed", 0)

    # Or calculate from spec_start/spec_complete events
    if total_specs == 0:
        spec_start_query = select(func.count()).where(
            and_(
                Event.session_id == session_uuid,
                Event.event_type == "spec_start"
            )
        )
        spec_start_result = await session.execute(spec_start_query)
        total_specs = spec_start_result.scalar() or 0

    if completed_specs == 0:
        spec_complete_query = select(func.count()).where(
            and_(
                Event.session_id == session_uuid,
                Event.event_type == "spec_complete"
            )
        )
        spec_complete_result = await session.execute(spec_complete_query)
        completed_specs = spec_complete_result.scalar() or 0

    if failed_specs == 0:
        spec_fail_query = select(func.count()).where(
            and_(
                Event.session_id == session_uuid,
                Event.event_type == "spec_fail"
            )
        )
        spec_fail_result = await session.execute(spec_fail_query)
        failed_specs = spec_fail_result.scalar() or 0

    # Calculate success rate
    spec_success_rate = (completed_specs / total_specs) if total_specs > 0 else 0

    # Calculate duration
    duration_seconds = calculate_duration_seconds(session_obj.started_at, session_obj.ended_at)

    return {
        "session_id": str(session_obj.id),
        "agent_type": session_obj.agent_type.value,
        "project_name": session_obj.project_name,
        "status": session_obj.status.value,
        "started_at": session_obj.started_at.isoformat() if session_obj.started_at else None,
        "ended_at": session_obj.ended_at.isoformat() if session_obj.ended_at else None,
        "duration_seconds": duration_seconds,
        "total_events": total_events,
        "event_type_counts": event_type_counts,
        "total_specs": total_specs,
        "completed_specs": completed_specs,
        "failed_specs": failed_specs,
        "spec_success_rate": spec_success_rate,
        "error_count": error_count,
        "warning_count": warning_count,
    }


@router.get("/trends")
async def get_trends(
    period: int = Query(30, ge=1, le=365, description="Period in days"),
    bucket_size: str = Query("day", description="Bucket size: hour, day, week"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get trends analysis over a time period.

    Args:
        period: Number of days to analyze
        bucket_size: Time bucket size for aggregation
        session: Database session

    Returns:
        Dictionary with trends data including session counts, spec trends, and error trends
    """
    from_date = datetime.now() - timedelta(days=period)

    # Map bucket size to PostgreSQL date_trunc values
    bucket_map = {
        "hour": "hour",
        "day": "day",
        "week": "week",
    }
    trunc_unit = bucket_map.get(bucket_size, "day")

    # Get total sessions in period
    total_sessions_query = select(func.count()).where(
        Session.started_at >= from_date
    )
    total_sessions_result = await session.execute(total_sessions_query)
    total_sessions = total_sessions_result.scalar() or 0

    # Get sessions by status
    sessions_by_status_query = select(
        Session.status,
        func.count().label("count")
    ).where(
        Session.started_at >= from_date
    ).group_by(Session.status)

    sessions_by_status_result = await session.execute(sessions_by_status_query)
    sessions_by_status = {row.status.value: row.count for row in sessions_by_status_result.all()}

    # Get sessions by agent type
    sessions_by_agent_query = select(
        Session.agent_type,
        func.count().label("count")
    ).where(
        Session.started_at >= from_date
    ).group_by(Session.agent_type)

    sessions_by_agent_result = await session.execute(sessions_by_agent_query)
    sessions_by_agent = {row.agent_type.value: row.count for row in sessions_by_agent_result.all()}

    # Get session trend over time
    session_trend_query = select(
        func.date_trunc(trunc_unit, Session.started_at).label("timestamp"),
        func.count().label("count")
    ).where(
        Session.started_at >= from_date
    ).group_by(
        func.date_trunc(trunc_unit, Session.started_at)
    ).order_by(
        func.date_trunc(trunc_unit, Session.started_at)
    )

    session_trend_result = await session.execute(session_trend_query)
    session_trend = [
        {
            "timestamp": row.timestamp.isoformat(),
            "count": row.count,
        }
        for row in session_trend_result.all()
    ]

    # Get spec trend over time (completed vs failed)
    spec_complete_trend = select(
        func.date_trunc(trunc_unit, Event.created_at).label("timestamp"),
        func.count().label("count")
    ).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_complete"
        )
    ).group_by(
        func.date_trunc(trunc_unit, Event.created_at)
    ).subquery()

    spec_fail_trend = select(
        func.date_trunc(trunc_unit, Event.created_at).label("timestamp"),
        func.count().label("count")
    ).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_fail"
        )
    ).group_by(
        func.date_trunc(trunc_unit, Event.created_at)
    ).subquery()

    # Combine spec trends
    spec_trend_query = select(
        func.coalesce(spec_complete_trend.c.timestamp, spec_fail_trend.c.timestamp).label("timestamp"),
        func.coalesce(spec_complete_trend.c.count, 0).label("completed"),
        func.coalesce(spec_fail_trend.c.count, 0).label("failed"),
    ).outerjoin(
        spec_fail_trend,
        spec_complete_trend.c.timestamp == spec_fail_trend.c.timestamp
    ).order_by(
        func.coalesce(spec_complete_trend.c.timestamp, spec_fail_trend.c.timestamp)
    )

    spec_trend_result = await session.execute(spec_trend_query)
    spec_trend = [
        {
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "total": row.completed + row.failed,
            "completed": row.completed,
            "failed": row.failed,
        }
        for row in spec_trend_result.all()
    ]

    # Get error trend over time
    error_trend_query = select(
        func.date_trunc(trunc_unit, Event.created_at).label("timestamp"),
        func.count().label("count")
    ).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type.in_(["error", "spec_fail"])
        )
    ).group_by(
        func.date_trunc(trunc_unit, Event.created_at)
    ).order_by(
        func.date_trunc(trunc_unit, Event.created_at)
    )

    error_trend_result = await session.execute(error_trend_query)
    error_trend = [
        {
            "timestamp": row.timestamp.isoformat(),
            "count": row.count,
        }
        for row in error_trend_result.all()
    ]

    # Calculate average session duration
    avg_duration_query = select(
        func.avg(
            func.extract("epoch", Session.ended_at) -
            func.extract("epoch", Session.started_at)
        )
    ).where(
        and_(
            Session.started_at >= from_date,
            Session.ended_at.isnot(None)
        )
    )

    avg_duration_result = await session.execute(avg_duration_query)
    avg_session_duration = avg_duration_result.scalar() or 0

    # Get total spec runs and success rate
    total_complete = select(func.count()).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_complete"
        )
    )
    total_complete_result = await session.execute(total_complete)
    completed_count = total_complete_result.scalar() or 0

    total_fail = select(func.count()).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_fail"
        )
    )
    total_fail_result = await session.execute(total_fail)
    failed_count = total_fail_result.scalar() or 0

    total_spec_runs = completed_count + failed_count
    spec_success_rate = (completed_count / total_spec_runs) if total_spec_runs > 0 else 0

    return {
        "period": str(period),
        "bucket_size": bucket_size,
        "from_date": from_date.isoformat(),
        "to_date": datetime.now().isoformat(),
        "total_sessions": total_sessions,
        "sessions_by_status": sessions_by_status,
        "sessions_by_agent": sessions_by_agent,
        "session_trend": session_trend,
        "spec_trend": spec_trend,
        "error_trend": error_trend,
        "avg_session_duration": avg_session_duration,
        "total_spec_runs": total_spec_runs,
        "spec_success_rate": spec_success_rate,
    }


@router.post("/compare")
async def compare_sessions(
    session_ids: dict[str, list[str]],
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Compare multiple sessions side by side.

    Args:
        session_ids: Dictionary with "session_ids" key containing list of session UUIDs
        db_session: Database session

    Returns:
        Dictionary with comparison data and metrics
    """
    try:
        ids = [uuid.UUID(sid) for sid in session_ids.get("session_ids", [])]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    if not ids:
        raise HTTPException(status_code=400, detail="No session IDs provided")

    # Get session data for all requested sessions
    sessions_query = select(Session).where(Session.id.in_(ids))
    sessions_result = await db_session.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")

    # Build session summaries
    session_summaries = []
    durations = []
    spec_success_rates = []
    total_specs = 0
    total_errors = 0

    for session_obj in sessions:
        # Get event counts
        event_counts_query = select(
            Event.event_type,
            func.count().label("count")
        ).where(
            Event.session_id == session_obj.id
        ).group_by(Event.event_type)

        event_counts_result = await db_session.execute(event_counts_query)
        event_type_counts = {row.event_type: row.count for row in event_counts_result.all()}

        # Get total events
        total_events_query = select(func.count()).where(Event.session_id == session_obj.id)
        total_events_result = await db_session.execute(total_events_query)
        total_events = total_events_result.scalar() or 0

        # Get error count
        error_count_query = select(func.count()).where(
            and_(
                Event.session_id == session_obj.id,
                Event.event_type.in_(["error", "spec_fail"])
            )
        )
        error_count_result = await db_session.execute(error_count_query)
        error_count = error_count_result.scalar() or 0

        # Get warning count
        warning_count_query = select(func.count()).where(
            and_(
                Event.session_id == session_obj.id,
                Event.data["warning"].astext != None
            )
        )
        warning_count_result = await db_session.execute(warning_count_query)
        warning_count = warning_count_result.scalar() or 0

        # Get spec info
        spec_info = session_obj.meta_data.get("specs", {})
        session_total_specs = spec_info.get("total", 0)
        session_completed_specs = spec_info.get("completed", 0)
        session_failed_specs = spec_info.get("failed", 0)

        # Or calculate from events
        if session_total_specs == 0:
            spec_start_query = select(func.count()).where(
                and_(
                    Event.session_id == session_obj.id,
                    Event.event_type == "spec_start"
                )
            )
            spec_start_result = await db_session.execute(spec_start_query)
            session_total_specs = spec_start_result.scalar() or 0

        if session_completed_specs == 0:
            spec_complete_query = select(func.count()).where(
                and_(
                    Event.session_id == session_obj.id,
                    Event.event_type == "spec_complete"
                )
            )
            spec_complete_result = await db_session.execute(spec_complete_query)
            session_completed_specs = spec_complete_result.scalar() or 0

        if session_failed_specs == 0:
            spec_fail_query = select(func.count()).where(
                and_(
                    Event.session_id == session_obj.id,
                    Event.event_type == "spec_fail"
                )
            )
            spec_fail_result = await db_session.execute(spec_fail_query)
            session_failed_specs = spec_fail_result.scalar() or 0

        session_spec_success_rate = (session_completed_specs / session_total_specs) if session_total_specs > 0 else 0
        duration_seconds = calculate_duration_seconds(session_obj.started_at, session_obj.ended_at)

        session_summaries.append({
            "session_id": str(session_obj.id),
            "agent_type": session_obj.agent_type.value,
            "project_name": session_obj.project_name,
            "status": session_obj.status.value,
            "started_at": session_obj.started_at.isoformat() if session_obj.started_at else None,
            "ended_at": session_obj.ended_at.isoformat() if session_obj.ended_at else None,
            "duration_seconds": duration_seconds,
            "total_events": total_events,
            "event_type_counts": event_type_counts,
            "total_specs": session_total_specs,
            "completed_specs": session_completed_specs,
            "failed_specs": session_failed_specs,
            "spec_success_rate": session_spec_success_rate,
            "error_count": error_count,
            "warning_count": warning_count,
        })

        durations.append(duration_seconds)
        spec_success_rates.append(session_spec_success_rate)
        total_specs += session_total_specs
        total_errors += error_count

    # Calculate comparison metrics
    avg_duration = sum(durations) / len(durations) if durations else 0
    avg_spec_success_rate = sum(spec_success_rates) / len(spec_success_rates) if spec_success_rates else 0

    # Find fastest and slowest
    fastest_session = None
    slowest_session = None
    if durations:
        min_duration = min(durations)
        max_duration = max(durations)
        for i, s in enumerate(session_summaries):
            if s["duration_seconds"] == min_duration:
                fastest_session = {"session_id": s["session_id"], "duration": s["duration_seconds"]}
            if s["duration_seconds"] == max_duration:
                slowest_session = {"session_id": s["session_id"], "duration": s["duration_seconds"]}

    # Find highest and lowest success rates
    highest_success = None
    lowest_success = None
    if spec_success_rates:
        min_rate = min(spec_success_rates)
        max_rate = max(spec_success_rates)
        for i, s in enumerate(session_summaries):
            if s["spec_success_rate"] == max_rate:
                highest_success = {"session_id": s["session_id"], "rate": s["spec_success_rate"]}
            if s["spec_success_rate"] == min_rate:
                lowest_success = {"session_id": s["session_id"], "rate": s["spec_success_rate"]}

    return {
        "sessions": session_summaries,
        "metrics": {
            "total_sessions": len(session_summaries),
            "avg_duration": avg_duration,
            "avg_spec_success_rate": avg_spec_success_rate,
            "total_specs": total_specs,
            "total_errors": total_errors,
            "fastest_session": fastest_session,
            "slowest_session": slowest_session,
            "highest_success_rate": highest_success,
            "lowest_success_rate": lowest_success,
        },
    }


@router.get("/errors/aggregated")
async def get_errors_aggregated(
    from_date: str | None = Query(None, description="Start date (ISO format)"),
    to_date: str | None = Query(None, description="End date (ISO format)"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get aggregated error data for reports.

    Args:
        from_date: Start date filter (ISO 8601 format)
        to_date: End date filter (ISO 8601 format)
        session: Database session

    Returns:
        Dictionary with error aggregation data
    """
    base_conditions = [Event.event_type.in_(["error", "spec_fail"])]

    if from_date:
        try:
            start_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            base_conditions.append(Event.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format")

    if to_date:
        try:
            end_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            base_conditions.append(Event.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format")

    # Get total errors
    total_errors_query = select(func.count()).where(and_(*base_conditions))
    total_errors_result = await session.execute(total_errors_query)
    total_errors = total_errors_result.scalar() or 0

    # Get error frequency by message
    error_messages_query = select(
        func.coalesce(Event.data["error"].astext, Event.data["message"].astext, "Unknown").label("message"),
        func.count().label("count")
    ).where(
        and_(*base_conditions)
    ).group_by(
        func.coalesce(Event.data["error"].astext, Event.data["message"].astext, "Unknown")
    ).order_by(
        func.count().desc()
    )

    error_messages_result = await session.execute(error_messages_query)
    error_frequency = {row.message: row.count for row in error_messages_result.all()}

    # Get errors by session
    errors_by_session_query = select(
        Event.session_id,
        func.count().label("error_count")
    ).where(
        and_(*base_conditions)
    ).group_by(Event.session_id)

    errors_by_session_result = await session.execute(errors_by_session_query)
    by_session_counts = {row.session_id: row.error_count for row in errors_by_session_result.all()}

    # Get most recent error per session
    recent_errors_query = select(Event).where(
        and_(*base_conditions)
    ).order_by(Event.created_at.desc()).distinct(Event.session_id)

    recent_errors_result = await session.execute(recent_errors_query)
    recent_errors = recent_errors_result.scalars().all()

    # Build by_session data
    by_session = []
    for session_id, error_count in by_session_counts.items():
        recent_error = next((e for e in recent_errors if e.session_id == session_id), None)
        by_session.append({
            "session_id": str(session_id),
            "error_count": error_count,
            "most_recent_error": {
                "id": str(recent_error.id) if recent_error else None,
                "event_type": recent_error.event_type if recent_error else None,
                "message": recent_error.data.get("error") or recent_error.data.get("message", "Unknown") if recent_error else None,
                "created_at": recent_error.created_at.isoformat() if recent_error else None,
            } if recent_error else None,
        })

    return {
        "total_errors": total_errors,
        "error_frequency": error_frequency,
        "by_session": by_session,
        "sessions_with_errors": len(by_session),
    }
