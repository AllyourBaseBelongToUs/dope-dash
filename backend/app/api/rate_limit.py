"""Rate limit detection API endpoints.

This module provides REST API endpoints for managing rate limit events,
including 429 error tracking, retry status, and event summaries.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quota import (
    ProviderType,
    RateLimitEventCreate,
    RateLimitEventResponse,
    RateLimitEventSummary,
    RateLimitEventStatus,
)
from app.services.rate_limit import (
    RateLimitService,
    ExponentialBackoffCalculator,
    RetryAfterParser,
    RateLimitDetector,
    get_rate_limit_service,
    MAX_RETRY_ATTEMPTS,
)
from db.connection import get_db_session


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rate-limit", tags=["rate-limit"])


# ========== Rate Limit Events ==========


@router.post("/events/record", response_model=dict[str, Any])
async def record_rate_limit_event(
    request: RateLimitEventCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Record a rate limit event (429 error).

    Call this endpoint when a 429 error is detected from an API provider.
    The event will be tracked and can be retried with exponential backoff.

    Args:
        request: Rate limit event details

    Returns:
        Recorded event details
    """
    service = get_rate_limit_service(session)

    try:
        event = await service.record_rate_limit_event(request)
        await session.commit()

        return {
            "message": "Rate limit event recorded",
            "event_id": str(event.id),
            "status": event.status.value,
            "attempt_number": event.attempt_number,
            "max_attempts": event.max_attempts,
            "retry_after_seconds": event.retry_after_seconds,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/events", response_model=dict[str, Any])
async def list_rate_limit_events(
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider"),
    project_id: uuid.UUID | None = Query(None, description="Filter by project"),
    status: RateLimitEventStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List rate limit events with filters.

    Returns a paginated list of rate limit events.
    """
    service = get_rate_limit_service(session)

    events = await service.get_events(
        provider_id=provider_id,
        project_id=project_id,
        status=status,
        limit=limit,
    )

    # Apply pagination
    total = len(events)
    paginated_events = events[offset:offset + limit]

    return {
        "items": [e.model_dump() for e in paginated_events],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/events/summary", response_model=dict[str, Any])
async def get_rate_limit_summary(
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get summary of rate limit events.

    Returns aggregate statistics including total events, active events,
    resolved events, and counts by provider.
    """
    service = get_rate_limit_service(session)

    summary = await service.get_event_summary(provider_id)

    return {
        "total_events": summary.total_events,
        "active_events": summary.active_events,
        "resolved_events": summary.resolved_events,
        "failed_events": summary.failed_events,
        "by_provider": summary.by_provider,
        "recent_events": [e.model_dump() for e in summary.recent_events],
        "timestamp": summary.timestamp.isoformat(),
    }


@router.get("/events/{event_id}", response_model=dict[str, Any])
async def get_rate_limit_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a specific rate limit event by ID.

    Returns detailed event information including retry status.
    """
    service = get_rate_limit_service(session)

    event = await service.get_event(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit event not found: {event_id}",
        )

    return event.model_dump()


@router.post("/events/{event_id}/retry", response_model=dict[str, Any])
async def update_event_retrying(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark an event as retrying with calculated backoff.

    Calculates exponential backoff with jitter and updates the event status.
    """
    service = get_rate_limit_service(session)

    event = await service._get_event(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit event not found: {event_id}",
        )

    # Calculate backoff with jitter
    base_backoff, jitter = ExponentialBackoffCalculator.calculate_backoff_with_jitter(
        event.attempt_number
    )

    # Update event
    updated = await service.update_event_retrying(event_id, base_backoff, jitter)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event cannot be retried: {event_id}",
        )

    await session.commit()

    return {
        "message": "Event marked for retry",
        "event_id": str(event.id),
        "attempt_number": updated.attempt_number,
        "max_attempts": updated.max_attempts,
        "backoff_seconds": base_backoff,
        "jitter_seconds": jitter,
        "total_delay_seconds": base_backoff + jitter,
        "status": updated.status.value,
    }


@router.post("/events/{event_id}/resolve", response_model=dict[str, Any])
async def resolve_rate_limit_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark a rate limit event as successfully resolved.

    Call this when a retried request succeeds.
    """
    service = get_rate_limit_service(session)

    event = await service.mark_event_resolved(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit event not found: {event_id}",
        )

    await session.commit()

    return {
        "message": "Event resolved",
        "event_id": str(event.id),
        "status": event.status.value,
        "attempts_required": event.attempt_number,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
    }


@router.post("/events/{event_id}/fail", response_model=dict[str, Any])
async def fail_rate_limit_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark a rate limit event as failed after exhausting retries.

    Call this when max retries have been exceeded.
    """
    service = get_rate_limit_service(session)

    event = await service.mark_event_failed(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit event not found: {event_id}",
        )

    await session.commit()

    return {
        "message": "Event marked as failed",
        "event_id": str(event.id),
        "status": event.status.value,
        "max_attempts": event.max_attempts,
        "failed_at": event.failed_at.isoformat() if event.failed_at else None,
    }


@router.get("/events/active", response_model=dict[str, Any])
async def get_active_rate_limit_events(
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get all active (detected/retrying) rate limit events.

    Returns events that are still being retried or waiting for retry.
    """
    service = get_rate_limit_service(session)

    events = await service.get_active_events(provider_id)

    return {
        "items": [service._event_to_response(e).model_dump() for e in events],
        "total": len(events),
    }


# ========== Backoff Calculator ==========


@router.get("/backoff/calculate", response_model=dict[str, Any])
async def calculate_backoff(
    attempt_number: int = Query(..., ge=1, le=MAX_RETRY_ATTEMPTS, description="Attempt number (1-based)"),
    include_jitter: bool = Query(True, description="Include random jitter"),
) -> dict[str, Any]:
    """Calculate exponential backoff delay for a given attempt number.

    Returns the backoff delay in seconds with optional jitter.
    Used to determine how long to wait before retrying a rate-limited request.

    Backoff pattern:
    - Attempt 1: 1 second
    - Attempt 2: 2 seconds
    - Attempt 3: 4 seconds
    - Attempt 4: 8 seconds
    - Attempt 5: 16 seconds

    Jitter adds +/- 10% to prevent thundering herd.
    """
    base = ExponentialBackoffCalculator.calculate_backoff(attempt_number)

    if include_jitter:
        _, jitter = ExponentialBackoffCalculator.calculate_backoff_with_jitter(attempt_number)
        total = base + jitter
    else:
        jitter = 0
        total = base

    return {
        "attempt_number": attempt_number,
        "base_backoff_seconds": base,
        "jitter_seconds": jitter,
        "total_delay_seconds": total,
        "jitter_ratio": 0.25,
        "description": "Exponential backoff with jitter to prevent thundering herd",
    }


@router.get("/backoff/retry-after", response_model=dict[str, Any])
async def parse_retry_after(
    retry_after_header: str = Query(..., description="Retry-After header value"),
    attempt_number: int = Query(1, ge=1, description="Current attempt number"),
) -> dict[str, Any]:
    """Parse Retry-After header and get effective delay.

    Supports two formats per RFC 7231:
    - Delay-seconds: "120" (integer seconds)
    - HTTP-date: "Fri, 31 Dec 2026 23:59:59 GMT"

    Falls back to exponential backoff if header is invalid.
    """
    retry_after_seconds, retry_after_date = RetryAfterParser.parse(retry_after_header)
    effective_delay = RetryAfterParser.get_effective_delay(retry_after_header, attempt_number)

    result = {
        "retry_after_header": retry_after_header,
        "parsed_retry_after_seconds": retry_after_seconds,
        "parsed_retry_after_date": retry_after_date.isoformat() if retry_after_date else None,
        "attempt_number": attempt_number,
        "effective_delay_seconds": effective_delay,
    }

    if retry_after_seconds:
        result["source"] = "retry-after_header"
    else:
        result["source"] = "exponential_backoff_fallback"

    return result


# ========== Detection ==========


@router.post("/detect", response_model=dict[str, Any])
async def detect_rate_limit(
    status_code: int,
    response_headers: dict[str, str] | None = None,
    response_body: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Check if a response indicates a rate limit error.

    Analyzes status code, headers, and response body to detect
    rate limiting (429 errors, rate limit headers, error messages).

    Returns detection result and retry information if applicable.
    """
    is_rate_limited = RateLimitDetector.is_rate_limit_error(
        status_code=status_code,
        response_headers=response_headers,
        response_body=response_body,
    )

    retry_after_seconds, retry_after_date = None, None
    effective_delay = None

    if is_rate_limited:
        retry_after_seconds, retry_after_date = RateLimitDetector.extract_retry_after(
            response_headers
        )
        # Calculate delay for first retry
        effective_delay = RetryAfterParser.get_effective_delay(
            response_headers.get("retry-after") if response_headers else None,
            1,
        )

    return {
        "is_rate_limited": is_rate_limited,
        "status_code": status_code,
        "retry_after_seconds": retry_after_seconds,
        "retry_after_date": retry_after_date.isoformat() if retry_after_date else None,
        "suggested_delay_seconds": effective_delay,
        "next_retry_after": effective_delay,
    }


# ========== Configuration ==========


@router.get("/config", response_model=dict[str, Any])
async def get_rate_limit_config() -> dict[str, Any]:
    """Get rate limit detection and retry configuration.

    Returns constants used for backoff calculation and retry limits.
    """
    return {
        "max_retry_attempts": MAX_RETRY_ATTEMPTS,
        "base_backoff_seconds": 1,
        "max_backoff_seconds": 32,
        "jitter_ratio": 0.25,
        "backoff_pattern": {
            1: "1 second (2^0)",
            2: "2 seconds (2^1)",
            3: "4 seconds (2^2)",
            4: "8 seconds (2^3)",
            5: "16 seconds (2^4)",
        },
        "description": "Exponential backoff with jitter for rate limit retries",
    }
