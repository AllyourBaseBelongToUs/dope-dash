"""Request queue API endpoints.

This module provides REST API endpoints for managing the request queue,
including queuing, monitoring, cancelling, and flushing requests.
"""
from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quota import (
    QueuePriority,
    QueueStatus,
    RequestQueueCreate,
    RequestQueueResponse,
    QueueStatsResponse,
)
from app.services.request_queue import (
    RequestQueueService,
    get_request_queue_service,
)
from db.connection import get_db_session


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["request-queue"])


# ========== Queue Management ==========


@router.post("/enqueue", response_model=dict[str, Any])
async def enqueue_request(
    request: RequestQueueCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Add a request to the queue.

    Requests are queued when:
    - Quota limits are reached
    - Rate limiting is detected (429 responses)
    - Manual scheduling for batch processing

    Queue priority determines processing order (high > medium > low).

    Args:
        request: Request details to queue

    Returns:
        Queued request details
    """
    service = get_request_queue_service(session)

    try:
        queued_request = await service.enqueue_request(request)
        await session.commit()

        return {
            "message": "Request queued successfully",
            "request_id": str(queued_request.id),
            "status": queued_request.status.value,
            "priority": queued_request.priority.value,
            "scheduled_at": queued_request.scheduled_at.isoformat() if queued_request.scheduled_at else None,
            "position": "pending",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/stats", response_model=dict[str, Any])
async def get_queue_stats(
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider"),
    project_id: uuid.UUID | None = Query(None, description="Filter by project"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get queue statistics.

    Returns aggregate statistics including:
    - Total requests by status
    - Queue depth (pending + processing)
    - Distribution by priority and provider
    - Average wait time
    """
    service = get_request_queue_service(session)

    stats = await service.get_queue_stats(
        provider_id=provider_id,
        project_id=project_id,
    )

    return {
        "total_pending": stats.total_pending,
        "total_processing": stats.total_processing,
        "total_completed": stats.total_completed,
        "total_failed": stats.total_failed,
        "total_cancelled": stats.total_cancelled,
        "by_priority": stats.by_priority,
        "by_provider": stats.by_provider,
        "by_project": stats.by_project,
        "oldest_pending": stats.oldest_pending.isoformat() if stats.oldest_pending else None,
        "newest_pending": stats.newest_pending.isoformat() if stats.newest_pending else None,
        "avg_wait_time_seconds": stats.avg_wait_time_seconds,
        "queue_depth": stats.queue_depth,
        "timestamp": stats.timestamp.isoformat(),
    }


@router.get("/pending", response_model=dict[str, Any])
async def list_pending_requests(
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider"),
    project_id: uuid.UUID | None = Query(None, description="Filter by project"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List pending requests in the queue.

    Returns pending requests ordered by priority and creation time.
    """
    service = get_request_queue_service(session)

    requests = await service.get_pending_requests(
        provider_id=provider_id,
        project_id=project_id,
        limit=limit,
    )

    return {
        "items": [_request_to_dict(r) for r in requests],
        "total": len(requests),
    }


@router.get("/requests/{request_id}", response_model=dict[str, Any])
async def get_request(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a specific queued request by ID.

    Returns detailed request information including status and retry count.
    """
    from sqlalchemy import select
    from app.models.quota import RequestQueue

    result = await session.execute(
        select(RequestQueue).where(RequestQueue.id == request_id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request not found: {request_id}",
        )

    return _request_to_dict(request)


@router.post("/requests/{request_id}/cancel", response_model=dict[str, Any])
async def cancel_request(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Cancel a pending or processing request.

    Cannot cancel requests that are already completed, failed, or cancelled.
    """
    service = get_request_queue_service(session)

    try:
        request = await service.cancel_request(request_id)
        await session.commit()

        return {
            "message": "Request cancelled successfully",
            "request_id": str(request.id),
            "status": request.status.value,
            "cancelled_at": request.cancelled_at.isoformat() if request.cancelled_at else None,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/requests/{request_id}/retry", response_model=dict[str, Any])
async def retry_request(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retry a failed request.

    Resets the request to pending status for reprocessing.
    Only works for failed requests that haven't exceeded max retries.
    """
    from sqlalchemy import select
    from app.models.quota import RequestQueue

    result = await session.execute(
        select(RequestQueue).where(RequestQueue.id == request_id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request not found: {request_id}",
        )

    if request.status != QueueStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only failed requests can be retried. Current status: {request.status.value}",
        )

    # Reset to pending for retry
    request.status = QueueStatus.PENDING
    request.scheduled_at = datetime.datetime.now(datetime.timezone.utc)
    request.last_error = None

    await session.commit()

    return {
        "message": "Request queued for retry",
        "request_id": str(request.id),
        "status": request.status.value,
        "retry_count": request.retry_count,
        "max_retries": request.max_retries,
    }


@router.delete("/requests/{request_id}", response_model=dict[str, Any])
async def delete_request(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete a request from the queue.

    Permanently removes a request. Use with caution.
    """
    from sqlalchemy import delete
    from app.models.quota import RequestQueue

    # Check if request exists
    result = await session.execute(
        select(RequestQueue).where(RequestQueue.id == request_id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request not found: {request_id}",
        )

    # Delete the request
    delete_stmt = delete(RequestQueue).where(RequestQueue.id == request_id)
    await session.execute(delete_stmt)
    await session.commit()

    return {
        "message": "Request deleted successfully",
        "request_id": str(request_id),
    }


@router.post("/flush", response_model=dict[str, Any])
async def flush_queue(
    status_filter: list[QueueStatus] | None = Query(None, description="Statuses to delete"),
    provider_id: uuid.UUID | None = Query(None, description="Filter by provider"),
    project_id: uuid.UUID | None = Query(None, description="Filter by project"),
    older_than: datetime.datetime | None = Query(None, description="Delete requests older than this"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Flush (remove) requests from the queue.

    By default, removes completed, failed, and cancelled requests older than 7 days.

    Can be used to:
    - Clean up old completed requests
    - Clear failed requests
    - Purge cancelled requests
    """
    service = get_request_queue_service(session)

    # Default to cleaning up old terminal-state requests
    if status_filter is None:
        status_filter = [QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED]

    if older_than is None:
        # Default to 7 days ago
        older_than = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)

    counts = await service.flush_queue(
        status_filter=status_filter,
        provider_id=provider_id,
        project_id=project_id,
        older_than=older_than,
    )

    await session.commit()

    return {
        "message": "Queue flushed successfully",
        "deleted_count": counts.get("total", 0),
        "details": counts,
    }


@router.post("/check", response_model=dict[str, Any])
async def check_should_queue(
    provider_id: uuid.UUID,
    project_id: uuid.UUID | None = Query(None, description="Optional project ID"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Check if a request should be queued based on quota.

    Returns whether the request should be queued and the reason.
    """
    service = get_request_queue_service(session)

    should_queue, reason = await service.should_queue_request(
        provider_id=provider_id,
        project_id=project_id,
    )

    return {
        "should_queue": should_queue,
        "reason": reason,
        "provider_id": str(provider_id),
        "project_id": str(project_id) if project_id else None,
    }


# ========== Helper Functions ==========


def _request_to_dict(request: Any) -> dict[str, Any]:
    """Convert RequestQueue model to dictionary.

    Args:
        request: RequestQueue instance

    Returns:
        Dictionary representation
    """
    return {
        "id": str(request.id),
        "provider_id": str(request.provider_id),
        "project_id": str(request.project_id) if request.project_id else None,
        "session_id": str(request.session_id) if request.session_id else None,
        "endpoint": request.endpoint,
        "method": request.method,
        "priority": request.priority.value,
        "status": request.status.value,
        "scheduled_at": request.scheduled_at.isoformat() if request.scheduled_at else None,
        "retry_count": request.retry_count,
        "max_retries": request.max_retries,
        "last_error": request.last_error,
        "created_at": request.created_at.isoformat(),
        "updated_at": request.updated_at.isoformat(),
        "processing_started_at": request.processing_started_at.isoformat() if request.processing_started_at else None,
        "completed_at": request.completed_at.isoformat() if request.completed_at else None,
        "failed_at": request.failed_at.isoformat() if request.failed_at else None,
        "cancelled_at": request.cancelled_at.isoformat() if request.cancelled_at else None,
        # Computed properties
        "priority_weight": request.priority_weight,
        "is_ready": request.is_ready,
        "should_retry": request.should_retry,
        "wait_time_seconds": request.wait_time_seconds,
    }
