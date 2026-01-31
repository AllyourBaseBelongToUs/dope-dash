"""Analytics API server for metrics and trends.

This module provides a FastAPI application for on-demand analytics
including session summaries, historical trends, and metric aggregation.

Features:
- Session summary with metrics aggregation
- Historical trends (30/90/365 days)
- Time bucketing (hour, day, week, month)
- Redis caching with 5-minute TTL
- On-demand analytics rebuild
- Session comparison
- Export to JSON/CSV
"""
import asyncio
import csv
import io
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

import sys
from pathlib import Path as PathLib

# Add parent directory to path for imports
sys.path.insert(0, str(PathLib(__file__).parent.parent))

from app.core.config import settings
from db.connection import get_db_session, db_manager
from sqlalchemy import Select, and_, case, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.session import Session, SessionStatus
from app.models.spec_run import SpecRun, SpecRunStatus
from app.models.metric_bucket import MetricBucket


logger = logging.getLogger(__name__)


# Enums
class TimeBucket(str, Enum):
    """Time bucket sizes for aggregation."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendPeriod(str, Enum):
    """Predefined time periods for trends."""

    DAYS_30 = "30d"
    DAYS_90 = "90d"
    DAYS_365 = "365d"


class ExportFormat(str, Enum):
    """Export formats for analytics data."""

    JSON = "json"
    CSV = "csv"


# Request/Response schemas
class SessionSummaryResponse(BaseModel):
    """Response schema for session summary."""

    session_id: str = Field(..., description="The session ID")
    agent_type: str = Field(..., description="Type of agent")
    project_name: str = Field(..., description="Project name")
    status: str = Field(..., description="Session status")

    # Event metrics
    total_events: int = Field(..., description="Total events in session")
    event_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of events by type"
    )

    # Spec run metrics
    total_specs: int = Field(..., description="Total spec runs")
    completed_specs: int = Field(..., description="Completed spec runs")
    failed_specs: int = Field(..., description="Failed spec runs")
    spec_success_rate: float = Field(..., description="Spec success rate (0-1)")

    # Duration metrics
    started_at: str | None = Field(None, description="Session start time")
    ended_at: str | None = Field(None, description="Session end time")
    duration_seconds: float | None = Field(None, description="Session duration in seconds")

    # Error metrics
    error_count: int = Field(..., description="Total errors")
    warning_count: int = Field(..., description="Total warnings")

    # Metric buckets summary
    metric_summary: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Summary of metric buckets (min, max, avg)"
    )


class TrendsResponse(BaseModel):
    """Response schema for trends data."""

    period: str = Field(..., description="Time period queried")
    bucket_size: str = Field(..., description="Time bucket size used")
    from_date: str = Field(..., description="Start of period")
    to_date: str = Field(..., description="End of period")

    # Session trends
    total_sessions: int = Field(..., description="Total sessions in period")
    sessions_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Sessions grouped by status"
    )
    sessions_by_agent: dict[str, int] = Field(
        default_factory=dict,
        description="Sessions grouped by agent type"
    )

    # Time series data
    session_trend: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sessions over time (bucketed)"
    )
    spec_trend: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Spec runs over time (bucketed)"
    )
    error_trend: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Errors over time (bucketed)"
    )

    # Aggregate metrics
    avg_session_duration: float | None = Field(None, description="Average session duration")
    total_spec_runs: int = Field(..., description="Total spec runs in period")
    spec_success_rate: float = Field(..., description="Overall spec success rate")


class SessionComparisonResponse(BaseModel):
    """Response schema for session comparison."""

    sessions: list[dict[str, Any]] = Field(
        ...,
        description="Session data for comparison"
    )
    comparison_metrics: dict[str, dict[str, Any]] = Field(
        ...,
        description="Side-by-side comparison of key metrics"
    )


class RebuildRequest(BaseModel):
    """Request schema for analytics rebuild."""

    force: bool = Field(
        default=False,
        description="Force rebuild even if cache is valid"
    )
    session_ids: list[str] | None = Field(
        default=None,
        description="Specific session IDs to rebuild (None = all)"
    )


class RebuildResponse(BaseModel):
    """Response schema for analytics rebuild."""

    status: str = Field(..., description="Rebuild status")
    sessions_processed: int = Field(..., description="Number of sessions processed")
    cache_cleared: int = Field(..., description="Number of cache entries cleared")
    started_at: str = Field(..., description="Rebuild start time")
    completed_at: str | None = Field(None, description="Rebuild completion time")


# Redis cache helper
class AnalyticsCache:
    """Redis cache for analytics results."""

    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        """Initialize the cache manager."""
        self._redis = None
        self._enabled = False

    async def init(self):
        """Initialize Redis connection."""
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._enabled = True
            logger.info(f"Analytics cache connected to Redis at {settings.redis_url}")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}. Caching disabled.")
            self._enabled = False

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._enabled = False

    def _make_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key."""
        parts = [f"analytics:{prefix}"]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                parts.append(f"{k}={v}")
        return ":".join(parts)

    async def get(self, prefix: str, **kwargs) -> Any | None:
        """Get cached value."""
        if not self._enabled:
            return None
        try:
            key = self._make_key(prefix, **kwargs)
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None

    async def set(self, value: Any, prefix: str, **kwargs) -> bool:
        """Set cached value."""
        if not self._enabled:
            return False
        try:
            key = self._make_key(prefix, **kwargs)
            await self._redis.setex(
                key,
                self.CACHE_TTL,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, prefix: str, **kwargs) -> bool:
        """Delete cached value."""
        if not self._enabled:
            return False
        try:
            key = self._make_key(prefix, **kwargs)
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        if not self._enabled:
            return 0
        try:
            keys = []
            async for key in self._redis.scan_iter(f"analytics:{pattern}*"):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return 0


# Global cache instance
cache = AnalyticsCache()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info("Starting Analytics API server...")

    # Initialize database
    db_manager.init_db()

    # Initialize cache
    await cache.init()

    logger.info(f"Analytics API ready on port 8004")

    yield

    # Shutdown
    logger.info("Shutting down Analytics API server...")
    await cache.close()
    await db_manager.close_db()


# Create FastAPI application
app = FastAPI(
    title="Dope Dash Analytics API",
    description="REST API for analytics, metrics, and trends",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_period_dates(period: TrendPeriod) -> tuple[datetime, datetime]:
    """Get start and end dates for a trend period.

    Args:
        period: The trend period enum.

    Returns:
        Tuple of (start_date, end_date).
    """
    now = datetime.utcnow()
    if period == TrendPeriod.DAYS_30:
        start = now - timedelta(days=30)
    elif period == TrendPeriod.DAYS_90:
        start = now - timedelta(days=90)
    elif period == TrendPeriod.DAYS_365:
        start = now - timedelta(days=365)
    else:
        start = now - timedelta(days=30)
    return start, now


def _get_time_bucket_trunc(bucket: TimeBucket):
    """Get SQL truncation function for time bucketing.

    Args:
        bucket: The time bucket enum.

    Returns:
        SQLAlchemy truncation expression.
    """
    if bucket == TimeBucket.HOUR:
        return func.date_trunc('hour', Session.started_at)
    elif bucket == TimeBucket.DAY:
        return func.date_trunc('day', Session.started_at)
    elif bucket == TimeBucket.WEEK:
        return func.date_trunc('week', Session.started_at)
    elif bucket == TimeBucket.MONTH:
        return func.date_trunc('month', Session.started_at)
    return func.date_trunc('day', Session.started_at)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": "Dope Dash Analytics API",
        "version": "0.1.0",
        "status": "running",
        "port": 8004,
        "cache_enabled": cache._enabled,
        "endpoints": {
            "session_summary": "GET /api/analytics/{session_id}/summary",
            "trends": "GET /api/analytics/trends",
            "compare": "GET /api/analytics/compare",
            "rebuild": "POST /api/analytics/rebuild",
            "export": "GET /api/analytics/export/{format}",
            "health": "/health",
        },
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    db_healthy = await db_manager.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "cache_enabled": cache._enabled,
        "database": "connected" if db_healthy else "disconnected",
    }


@app.get("/api/analytics/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    use_cache: bool = Query(True, description="Whether to use cached results"),
    session: AsyncSession = Depends(get_db_session),
) -> SessionSummaryResponse:
    """Get analytics summary for a specific session.

    Args:
        session_id: The session UUID.
        use_cache: Whether to use cached results (default: True).
        session: Database session.

    Returns:
        SessionSummaryResponse with aggregated metrics.

    Raises:
        404: If session is not found.
    """
    # Validate session ID
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format",
        )

    # Check cache
    if use_cache:
        cached = await cache.get("summary", session_id=session_id)
        if cached:
            logger.debug(f"Cache hit for session summary: {session_id}")
            return SessionSummaryResponse(**cached)

    # Query session
    session_query = select(Session).where(Session.id == session_uuid)
    session_result = await session.execute(session_query)
    sess = session_result.scalar_one_or_none()

    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Count events by type
    event_counts_query = select(
        Event.event_type,
        func.count().label("count")
    ).where(
        Event.session_id == session_uuid
    ).group_by(Event.event_type)

    event_counts_result = await session.execute(event_counts_query)
    event_type_counts = {
        event_type: count
        for event_type, count in event_counts_result.all()
    }
    total_events = sum(event_type_counts.values())

    # Count spec runs
    specs_query = select(
        func.count().label("total"),
        func.sum(case((SpecRun.status == SpecRunStatus.COMPLETED, 1), else_=0)).label("completed"),
        func.sum(case((SpecRun.status == SpecRunStatus.FAILED, 1), else_=0)).label("failed"),
    ).where(SpecRun.session_id == session_uuid)

    specs_result = await session.execute(specs_query)
    spec_row = specs_result.one()
    total_specs = spec_row.total or 0
    completed_specs = spec_row.completed or 0
    failed_specs = spec_row.failed or 0
    spec_success_rate = completed_specs / total_specs if total_specs > 0 else 0.0

    # Error counts
    error_count = event_type_counts.get("error", 0)
    warning_count = event_type_counts.get("warning", 0)

    # Duration
    duration_seconds = None
    if sess.started_at and sess.ended_at:
        duration_seconds = (sess.ended_at - sess.started_at).total_seconds()
    elif sess.started_at:
        duration_seconds = (datetime.utcnow() - sess.started_at).total_seconds()

    # Metric buckets summary
    metrics_query = select(
        MetricBucket.metric_name,
        func.min(MetricBucket.value).label("min_val"),
        func.max(MetricBucket.value).label("max_val"),
        func.avg(MetricBucket.value).label("avg_val"),
    ).where(
        MetricBucket.session_id == session_uuid
    ).group_by(MetricBucket.metric_name)

    metrics_result = await session.execute(metrics_query)
    metric_summary = {
        metric_name: {
            "min": min_val,
            "max": max_val,
            "avg": avg_val,
        }
        for metric_name, min_val, max_val, avg_val in metrics_result.all()
    }

    # Build response
    response = SessionSummaryResponse(
        session_id=str(sess.id),
        agent_type=sess.agent_type.value,
        project_name=sess.project_name,
        status=sess.status.value,
        total_events=total_events,
        event_type_counts=event_type_counts,
        total_specs=total_specs,
        completed_specs=completed_specs,
        failed_specs=failed_specs,
        spec_success_rate=spec_success_rate,
        started_at=sess.started_at.isoformat() if sess.started_at else None,
        ended_at=sess.ended_at.isoformat() if sess.ended_at else None,
        duration_seconds=duration_seconds,
        error_count=error_count,
        warning_count=warning_count,
        metric_summary=metric_summary,
    )

    # Cache response
    if use_cache:
        await cache.set(response.model_dump(), "summary", session_id=session_id)

    return response


@app.get("/api/analytics/trends", response_model=TrendsResponse)
async def get_trends(
    period: TrendPeriod = Query(TrendPeriod.DAYS_30, description="Time period for trends"),
    bucket: TimeBucket = Query(TimeBucket.DAY, description="Time bucket size"),
    use_cache: bool = Query(True, description="Whether to use cached results"),
    session: AsyncSession = Depends(get_db_session),
) -> TrendsResponse:
    """Get historical analytics trends.

    Args:
        period: Time period (30d, 90d, 365d).
        bucket: Time bucket size (hour, day, week, month).
        use_cache: Whether to use cached results.
        session: Database session.

    Returns:
        TrendsResponse with historical data.
    """
    # Check cache
    if use_cache:
        cached = await cache.get("trends", period=period.value, bucket=bucket.value)
        if cached:
            logger.debug(f"Cache hit for trends: {period.value}/{bucket.value}")
            return TrendsResponse(**cached)

    start_date, end_date = _get_period_dates(period)

    # Session counts by status
    status_counts_query = select(
        Session.status,
        func.count().label("count")
    ).where(
        and_(
            Session.started_at >= start_date,
            Session.started_at <= end_date,
        )
    ).group_by(Session.status)

    status_counts_result = await session.execute(status_counts_query)
    sessions_by_status = {
        status.value: count
        for status, count in status_counts_result.all()
    }

    # Session counts by agent type
    agent_counts_query = select(
        Session.agent_type,
        func.count().label("count")
    ).where(
        and_(
            Session.started_at >= start_date,
            Session.started_at <= end_date,
        )
    ).group_by(Session.agent_type)

    agent_counts_result = await session.execute(agent_counts_query)
    sessions_by_agent = {
        agent.value: count
        for agent, count in agent_counts_result.all()
    }

    total_sessions = sum(sessions_by_status.values())

    # Time bucket truncation
    time_bucket = _get_time_bucket_trunc(bucket)

    # Session trend over time
    session_trend_query = select(
        time_bucket.label("bucket"),
        func.count().label("count"),
    ).where(
        and_(
            Session.started_at >= start_date,
            Session.started_at <= end_date,
        )
    ).group_by("bucket").order_by("bucket")

    session_trend_result = await session.execute(session_trend_query)
    session_trend = [
        {
            "timestamp": bucket.isoformat() if bucket else None,
            "count": count,
        }
        for bucket, count in session_trend_result.all()
    ]

    # Spec trend over time
    spec_trend_query = select(
        time_bucket.label("bucket"),
        func.count().label("total"),
        func.sum(case((SpecRun.status == SpecRunStatus.COMPLETED, 1), else_=0)).label("completed"),
    ).join(
        SpecRun, Session.id == SpecRun.session_id
    ).where(
        and_(
            SpecRun.started_at >= start_date,
            SpecRun.started_at <= end_date,
        )
    ).group_by("bucket").order_by("bucket")

    spec_trend_result = await session.execute(spec_trend_query)
    spec_trend = [
        {
            "timestamp": bucket.isoformat() if bucket else None,
            "total": total or 0,
            "completed": completed or 0,
        }
        for bucket, total, completed in spec_trend_result.all()
    ]

    # Error trend over time
    error_trend_query = select(
        func.date_trunc(bucket.value, Event.created_at).label("bucket"),
        func.count().label("count"),
    ).where(
        and_(
            Event.created_at >= start_date,
            Event.created_at <= end_date,
            Event.event_type.in_(["error", "spec_fail"]),
        )
    ).group_by("bucket").order_by("bucket")

    error_trend_result = await session.execute(error_trend_query)
    error_trend = [
        {
            "timestamp": bucket.isoformat() if bucket else None,
            "count": count,
        }
        for bucket, count in error_trend_result.all()
    ]

    # Average session duration
    duration_query = select(
        func.avg(
            func.extract("epoch", Session.ended_at) -
            func.extract("epoch", Session.started_at)
        ).label("avg_duration")
    ).where(
        and_(
            Session.started_at >= start_date,
            Session.started_at <= end_date,
            Session.ended_at.isnot(None),
        )
    )

    duration_result = await session.execute(duration_query)
    avg_duration = duration_result.scalar()

    # Overall spec success rate
    spec_totals_query = select(
        func.count().label("total"),
        func.sum(case((SpecRun.status == SpecRunStatus.COMPLETED, 1), else_=0)).label("completed"),
    ).where(
        and_(
            SpecRun.started_at >= start_date,
            SpecRun.started_at <= end_date,
        )
    )

    spec_totals_result = await session.execute(spec_totals_query)
    spec_totals = spec_totals_result.one()
    total_spec_runs = spec_totals.total or 0
    spec_success_rate = (
        (spec_totals.completed or 0) / total_spec_runs
        if total_spec_runs > 0
        else 0.0
    )

    # Build response
    response = TrendsResponse(
        period=period.value,
        bucket_size=bucket.value,
        from_date=start_date.isoformat(),
        to_date=end_date.isoformat(),
        total_sessions=total_sessions,
        sessions_by_status=sessions_by_status,
        sessions_by_agent=sessions_by_agent,
        session_trend=session_trend,
        spec_trend=spec_trend,
        error_trend=error_trend,
        avg_session_duration=avg_duration,
        total_spec_runs=total_spec_runs,
        spec_success_rate=spec_success_rate,
    )

    # Cache response
    if use_cache:
        await cache.set(
            response.model_dump(),
            "trends",
            period=period.value,
            bucket=bucket.value,
        )

    return response


@app.get("/api/analytics/compare", response_model=SessionComparisonResponse)
async def compare_sessions(
    session_ids: str = Query(..., description="Comma-separated list of session IDs to compare"),
    use_cache: bool = Query(True, description="Whether to use cached results"),
    session: AsyncSession = Depends(get_db_session),
) -> SessionComparisonResponse:
    """Compare metrics across multiple sessions.

    Args:
        session_ids: Comma-separated list of session UUIDs.
        use_cache: Whether to use cached results.
        session: Database session.

    Returns:
        SessionComparisonResponse with side-by-side comparison.
    """
    # Parse and validate session IDs
    try:
        session_uuids = [uuid.UUID(sid.strip()) for sid in session_ids.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format",
        )

    if len(session_uuids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 session IDs required for comparison",
        )

    # Check cache
    cache_key = ",".join(sorted(str(s) for s in session_uuids))
    if use_cache:
        cached = await cache.get("compare", sessions=cache_key)
        if cached:
            logger.debug(f"Cache hit for session comparison: {cache_key}")
            return SessionComparisonResponse(**cached)

    # Get all sessions
    sessions_query = select(Session).where(Session.id.in_(session_uuids))
    sessions_result = await session.execute(sessions_query)
    sessions_list = sessions_result.scalars().all()

    if len(sessions_list) != len(session_uuids):
        found_ids = {str(s.id) for s in sessions_list}
        missing = set(str(s) for s in session_uuids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessions not found: {', '.join(missing)}",
        )

    # Build session data
    sessions_data = []
    for sess in sessions_list:
        # Get event counts
        event_count_query = select(func.count()).where(Event.session_id == sess.id)
        event_count_result = await session.execute(event_count_query)
        total_events = event_count_result.scalar() or 0

        # Get error count
        error_count_query = select(func.count()).where(
            and_(
                Event.session_id == sess.id,
                Event.event_type.in_(["error", "spec_fail"]),
            )
        )
        error_count_result = await session.execute(error_count_query)
        error_count = error_count_result.scalar() or 0

        # Get spec counts
        spec_count_query = select(
            func.count().label("total"),
            func.sum(case((SpecRun.status == SpecRunStatus.COMPLETED, 1), else_=0)).label("completed"),
        ).where(SpecRun.session_id == sess.id)
        spec_count_result = await session.execute(spec_count_query)
        spec_row = spec_count_result.one()

        duration = None
        if sess.started_at and sess.ended_at:
            duration = (sess.ended_at - sess.started_at).total_seconds()

        sessions_data.append({
            "session_id": str(sess.id),
            "agent_type": sess.agent_type.value,
            "project_name": sess.project_name,
            "status": sess.status.value,
            "started_at": sess.started_at.isoformat() if sess.started_at else None,
            "duration_seconds": duration,
            "total_events": total_events,
            "error_count": error_count,
            "total_specs": spec_row.total or 0,
            "completed_specs": spec_row.completed or 0,
            "spec_success_rate": (
                (spec_row.completed or 0) / (spec_row.total or 1)
                if spec_row.total and spec_row.total > 0
                else 0.0
            ),
        })

    # Build comparison metrics
    comparison_metrics = {
        "duration": {
            "min": min(s.get("duration_seconds") or float("inf") for s in sessions_data),
            "max": max(s.get("duration_seconds") or 0 for s in sessions_data),
        },
        "total_events": {
            "min": min(s["total_events"] for s in sessions_data),
            "max": max(s["total_events"] for s in sessions_data),
        },
        "error_count": {
            "min": min(s["error_count"] for s in sessions_data),
            "max": max(s["error_count"] for s in sessions_data),
        },
        "spec_success_rate": {
            "min": min(s["spec_success_rate"] for s in sessions_data),
            "max": max(s["spec_success_rate"] for s in sessions_data),
        },
    }

    response = SessionComparisonResponse(
        sessions=sessions_data,
        comparison_metrics=comparison_metrics,
    )

    # Cache response
    if use_cache:
        await cache.set(response.model_dump(), "compare", sessions=cache_key)

    return response


@app.post("/api/analytics/rebuild", response_model=RebuildResponse)
async def rebuild_analytics(
    request: RebuildRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RebuildResponse:
    """Trigger on-demand rebuild of analytics.

    This clears the cache and forces recomputation of analytics data.

    Args:
        request: Rebuild request parameters.
        session: Database session.

    Returns:
        RebuildResponse with rebuild status.
    """
    started_at = datetime.utcnow()

    # Clear cache
    sessions_to_clear = request.session_ids
    if sessions_to_clear is None:
        # Clear all cache
        cleared = await cache.clear_pattern("*")
    else:
        # Clear specific sessions
        cleared = 0
        for sid in sessions_to_clear:
            if await cache.delete("summary", session_id=sid):
                cleared += 1
        # Also clear trends cache
        await cache.clear_pattern("trends*")
        await cache.clear_pattern("compare*")

    # Count sessions
    if sessions_to_clear is None:
        count_query = select(func.count()).select_from(Session)
    else:
        try:
            session_uuids = [uuid.UUID(sid) for sid in sessions_to_clear]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session_id format in session_ids",
            )
        count_query = select(func.count()).where(Session.id.in_(session_uuids))

    count_result = await session.execute(count_query)
    sessions_processed = count_result.scalar() or 0

    completed_at = datetime.utcnow()

    return RebuildResponse(
        status="completed",
        sessions_processed=sessions_processed,
        cache_cleared=cleared,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
    )


@app.get("/api/analytics/export/{format}")
async def export_analytics(
    format: ExportFormat,
    session_id: str | None = Query(None, description="Filter by session ID"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Export analytics data in specified format.

    Args:
        format: Export format (json or csv).
        session_id: Optional session filter.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        session: Database session.

    Returns:
        Response with exported data.
    """
    # Build query
    query = select(Session).order_by(Session.started_at.desc())

    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            query = query.where(Session.id == session_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session_id format",
            )

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.where(Session.started_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format",
            )

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.where(Session.started_at <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format",
            )

    result = await session.execute(query)
    sessions = result.scalars().all()

    if format == ExportFormat.JSON:
        # Export as JSON
        data = [
            {
                "session_id": str(s.id),
                "agent_type": s.agent_type.value,
                "project_name": s.project_name,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "metadata": s.meta_data,
            }
            for s in sessions
        ]
        return JSONResponse(
            content=data,
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="analytics.json"',
            },
        )

    elif format == ExportFormat.CSV:
        # Export as CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Session ID",
            "Agent Type",
            "Project Name",
            "Status",
            "Started At",
            "Ended At",
            "Duration (seconds)",
            "PID",
            "Working Dir",
            "Command",
        ])

        # Rows
        for s in sessions:
            duration = None
            if s.started_at and s.ended_at:
                duration = (s.ended_at - s.started_at).total_seconds()

            writer.writerow([
                str(s.id),
                s.agent_type.value,
                s.project_name,
                s.status.value,
                s.started_at.isoformat() if s.started_at else "",
                s.ended_at.isoformat() if s.ended_at else "",
                duration or "",
                s.pid or "",
                s.working_dir or "",
                s.command or "",
            ])

        csv_data = output.getvalue()

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="analytics.csv"',
            },
        )


def main() -> None:
    """Run the Analytics API server.

    Binds to 0.0.0.0:8004 for external access.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        "analytics:app",
        host="0.0.0.0",
        port=8004,
        log_level="info",
        access_log=True,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
