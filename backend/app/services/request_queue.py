"""Request queue service for throttling and delayed request processing.

This service provides:
- Request queuing when quota limits are reached
- Priority-based request processing (high, medium, low)
- Queue persistence across service restarts
- Automatic retry with exponential backoff
- Queue depth monitoring and statistics
- Request cancellation and flush capabilities
"""
from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any
from uuid import UUID

import aiohttp
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quota import (
    Provider,
    Project,
    QuotaUsage,
    RequestQueue,
    QueuePriority,
    QueueStatsResponse,
    QueueStatus,
    RequestQueueCreate,
    RequestQueueResponse,
)


logger = logging.getLogger(__name__)


# Constants
QUEUE_POLL_INTERVAL = 1.0  # Seconds between queue checks
MAX_CONCURRENT_PROCESSING = 5  # Max requests to process simultaneously
QUEUE_RETENTION_DAYS = 7  # Days to keep completed/failed requests


class RequestQueueService:
    """Service for managing the request queue.

    Handles queuing of requests when quota is limited,
    priority-based processing, and queue monitoring.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the request queue service.

        Args:
            session: Database session
        """
        self.session = session
        self._processing_lock = asyncio.Lock()
        self._active_tasks: set[asyncio.Task] = set()

    # ================================================================
    # QUEUE MANAGEMENT
    # ================================================================

    async def enqueue_request(
        self,
        request: RequestQueueCreate,
    ) -> RequestQueue:
        """Add a request to the queue.

        Args:
            request: Request details to queue

        Returns:
            Created RequestQueue instance

        Raises:
            ValueError: If provider not found
        """
        # Verify provider exists
        provider_result = await self.session.execute(
            select(Provider).where(Provider.id == request.provider_id)
        )
        provider = provider_result.scalar_one_or_none()
        if not provider:
            raise ValueError(f"Provider not found: {request.provider_id}")

        # Verify project exists if specified
        if request.project_id:
            project_result = await self.session.execute(
                select(Project).where(Project.id == request.project_id)
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project not found: {request.project_id}")

        # Create queued request
        queued_request = RequestQueue(
            provider_id=request.provider_id,
            project_id=request.project_id,
            session_id=request.session_id,
            endpoint=request.endpoint,
            method=request.method,
            payload=request.payload,
            headers=request.headers,
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            max_retries=request.max_retries,
            metadata=request.metadata,
            status=QueueStatus.PENDING,
        )

        self.session.add(queued_request)
        await self.session.flush()
        await self.session.refresh(queued_request)

        logger.info(
            f"Queued request {queued_request.id}: {queued_request.method} {queued_request.endpoint} "
            f"(priority={queued_request.priority.value}, provider={provider.name.value})"
        )

        return queued_request

    async def dequeue_requests(
        self,
        provider_id: UUID | None = None,
        limit: int = 10,
    ) -> list[RequestQueue]:
        """Get next pending requests from the queue.

        Requests are ordered by priority (high first) and creation time (oldest first).

        Args:
            provider_id: Optional provider filter
            limit: Maximum number of requests to return

        Returns:
            List of RequestQueue instances ready for processing
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        # Build query with priority ordering
        # PostgreSQL's enum ordering matches definition: low < medium < high
        # We want descending priority, so we use CASE in ORDER BY
        query = (
            select(RequestQueue)
            .where(
                and_(
                    RequestQueue.status == QueueStatus.PENDING,
                    or_(
                        RequestQueue.scheduled_at.is_(None),
                        RequestQueue.scheduled_at <= now,
                    ),
                )
            )
            .order_by(
                # High priority first (using CASE for enum ordering)
                func.case(
                    (RequestQueue.priority == QueuePriority.HIGH, 3),
                    (RequestQueue.priority == QueuePriority.MEDIUM, 2),
                    (RequestQueue.priority == QueuePriority.LOW, 1),
                    else_=0,
                ).desc(),
                RequestQueue.created_at.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)  # Skip locked rows for concurrent processing
        )

        if provider_id:
            query = query.where(RequestQueue.provider_id == provider_id)

        result = await self.session.execute(query)
        requests = list(result.scalars().all())

        # Mark as processing
        for request in requests:
            request.mark_processing()

        await self.session.flush()

        if requests:
            logger.info(f"Dequeued {len(requests)} request(s) for processing")

        return requests

    async def mark_completed(
        self,
        request_id: UUID,
    ) -> RequestQueue:
        """Mark a request as completed.

        Args:
            request_id: Request ID

        Returns:
            Updated RequestQueue instance

        Raises:
            ValueError: If request not found
        """
        request = await self._get_request(request_id)
        request.mark_completed()
        await self.session.flush()
        await self.session.refresh(request)

        logger.info(f"Request {request_id} marked as completed")
        return request

    async def mark_failed(
        self,
        request_id: UUID,
        error: str,
        error_details: dict[str, Any] | None = None,
    ) -> RequestQueue:
        """Mark a request as failed.

        If max retries not reached, request is rescheduled for retry.

        Args:
            request_id: Request ID
            error: Error message
            error_details: Optional detailed error information

        Returns:
            Updated RequestQueue instance

        Raises:
            ValueError: If request not found
        """
        request = await self._get_request(request_id)

        if request.should_retry:
            # Reschedule for retry
            request.increment_retry()
            request.status = QueueStatus.PENDING
            request.last_error = error
            if error_details:
                request.error_details.update(error_details)

            logger.info(
                f"Request {request_id} failed (attempt {request.retry_count}/{request.max_retries}), "
                f"rescheduling with backoff"
            )
        else:
            # Mark as permanently failed
            request.mark_failed(error, error_details)
            logger.warning(f"Request {request_id} marked as failed: {error}")

        await self.session.flush()
        await self.session.refresh(request)
        return request

    async def cancel_request(
        self,
        request_id: UUID,
    ) -> RequestQueue:
        """Cancel a pending or processing request.

        Args:
            request_id: Request ID

        Returns:
            Updated RequestQueue instance

        Raises:
            ValueError: If request not found or in terminal state
        """
        request = await self._get_request(request_id)

        if request.is_terminal:
            raise ValueError(
                f"Cannot cancel request in terminal state: {request.status.value}"
            )

        request.mark_cancelled()
        await self.session.flush()
        await self.session.refresh(request)

        logger.info(f"Request {request_id} cancelled")
        return request

    async def flush_queue(
        self,
        status_filter: list[QueueStatus] | None = None,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
        older_than: datetime.datetime | None = None,
    ) -> dict[str, int]:
        """Remove requests from the queue.

        Args:
            status_filter: Optional list of statuses to delete (default: completed, failed, cancelled)
            provider_id: Optional provider filter
            project_id: Optional project filter
            older_than: Optional datetime filter (delete requests older than this)

        Returns:
            Dictionary with deletion counts by status
        """
        if status_filter is None:
            status_filter = [QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED]

        # Build conditions
        conditions = [RequestQueue.status.in_(status_filter)]

        if provider_id:
            conditions.append(RequestQueue.provider_id == provider_id)

        if project_id:
            conditions.append(RequestQueue.project_id == project_id)

        if older_than:
            conditions.append(RequestQueue.created_at < older_than)

        # Get counts before deletion
        count_query = (
            select(RequestQueue.status, func.count(RequestQueue.id))
            .where(and_(*conditions))
            .group_by(RequestQueue.status)
        )
        count_result = await self.session.execute(count_query)
        counts = {status.value: count for status, count in count_result.all()}

        # Delete requests
        delete_stmt = delete(RequestQueue).where(and_(*conditions))
        result = await self.session.execute(delete_stmt)
        deleted_count = result.rowcount

        logger.info(f"Flushed {deleted_count} requests from queue: {counts}")
        return {**counts, "total": deleted_count}

    # ================================================================
    # QUEUE STATISTICS
    # ================================================================

    async def get_queue_stats(
        self,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> QueueStatsResponse:
        """Get queue statistics.

        Args:
            provider_id: Optional provider filter
            project_id: Optional project filter

        Returns:
            QueueStatsResponse with current queue state
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        # Build base conditions
        conditions = []
        if provider_id:
            conditions.append(RequestQueue.provider_id == provider_id)
        if project_id:
            conditions.append(RequestQueue.project_id == project_id)

        base_query = select(RequestQueue)
        if conditions:
            base_query = base_query.where(and_(*conditions))

        # Count by status
        status_counts = await self.session.execute(
            select(
                RequestQueue.status,
                func.count(RequestQueue.id),
            ).select_from(base_query.subquery())
            .group_by(RequestQueue.status)
        )
        status_dict = {status.value: count for status, count in status_counts.all()}

        # Count by priority
        priority_counts = await self.session.execute(
            select(
                RequestQueue.priority,
                func.count(RequestQueue.id),
            ).select_from(
                base_query.where(RequestQueue.status == QueueStatus.PENDING).subquery()
            )
            .group_by(RequestQueue.priority)
        )
        priority_dict = {priority.value: count for priority, count in priority_counts.all()}

        # Count by provider (if not filtered)
        by_provider = {}
        if not provider_id:
            provider_counts = await self.session.execute(
                select(RequestQueue.provider_id, func.count(RequestQueue.id))
                .select_from(
                    base_query.where(RequestQueue.status == QueueStatus.PENDING).subquery()
                )
                .group_by(RequestQueue.provider_id)
            )
            by_provider = {str(pid): count for pid, count in provider_counts.all()}

        # Count by project (if not filtered)
        by_project = {}
        if not project_id:
            project_counts = await self.session.execute(
                select(RequestQueue.project_id, func.count(RequestQueue.id))
                .select_from(
                    base_query.where(RequestQueue.status == QueueStatus.PENDING).subquery()
                )
                .group_by(RequestQueue.project_id)
            )
            by_project = {
                str(pid) if pid else "null": count for pid, count in project_counts.all()
            }

        # Get oldest and newest pending requests
        pending_times = await self.session.execute(
            select(
                func.min(RequestQueue.created_at),
                func.max(RequestQueue.created_at),
            ).select_from(
                base_query.where(RequestQueue.status == QueueStatus.PENDING).subquery()
            )
        )
        oldest, newest = pending_times.one()

        # Calculate average wait time for pending requests
        avg_wait_result = await self.session.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        now - RequestQueue.created_at,
                    )
                )
            ).select_from(
                base_query.where(RequestQueue.status == QueueStatus.PENDING).subquery()
            )
        )
        avg_wait = avg_wait_result.scalar()

        return QueueStatsResponse(
            total_pending=status_dict.get("pending", 0),
            total_processing=status_dict.get("processing", 0),
            total_completed=status_dict.get("completed", 0),
            total_failed=status_dict.get("failed", 0),
            total_cancelled=status_dict.get("cancelled", 0),
            by_priority=priority_dict,
            by_provider=by_provider,
            by_project=by_project,
            oldest_pending=oldest,
            newest_pending=newest,
            avg_wait_time_seconds=float(avg_wait) if avg_wait else None,
            queue_depth=status_dict.get("pending", 0) + status_dict.get("processing", 0),
            timestamp=now,
        )

    async def get_pending_requests(
        self,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
        limit: int = 100,
    ) -> list[RequestQueue]:
        """Get pending requests for display.

        Args:
            provider_id: Optional provider filter
            project_id: Optional project filter
            limit: Maximum number of requests to return

        Returns:
            List of pending RequestQueue instances
        """
        query = (
            select(RequestQueue)
            .where(RequestQueue.status == QueueStatus.PENDING)
            .order_by(
                func.case(
                    (RequestQueue.priority == QueuePriority.HIGH, 3),
                    (RequestQueue.priority == QueuePriority.MEDIUM, 2),
                    (RequestQueue.priority == QueuePriority.LOW, 1),
                    else_=0,
                ).desc(),
                RequestQueue.created_at.asc(),
            )
            .limit(limit)
        )

        if provider_id:
            query = query.where(RequestQueue.provider_id == provider_id)
        if project_id:
            query = query.where(RequestQueue.project_id == project_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ================================================================
    # QUOTA CHECKING
    # ================================================================

    async def should_queue_request(
        self,
        provider_id: UUID,
        project_id: UUID | None = None,
    ) -> tuple[bool, str | None]:
        """Check if a request should be queued based on quota.

        Args:
            provider_id: Provider ID
            project_id: Optional project ID

        Returns:
            Tuple of (should_queue, reason)
        """
        # Get quota usage for provider/project
        quota_query = select(QuotaUsage).where(
            and_(
                QuotaUsage.provider_id == provider_id,
                QuotaUsage.project_id == project_id if project_id else QuotaUsage.project_id.is_(None),
            )
        )
        quota_result = await self.session.execute(quota_query)
        quota = quota_result.scalar_one_or_none()

        if not quota:
            # No quota tracking, don't queue
            return False, None

        if quota.is_over_limit:
            return True, f"Quota exceeded: {quota.current_requests}/{quota.quota_limit}"

        # Check if usage is above threshold (e.g., 90%)
        if quota.usage_percent >= 90:
            return True, f"Quota near limit: {quota.usage_percent:.1f}%"

        return False, None

    # ================================================================
    # REQUEST PROCESSING
    # ================================================================

    async def process_request(
        self,
        request: RequestQueue,
        http_session: aiohttp.ClientSession,
    ) -> dict[str, Any]:
        """Process a single queued request.

        Args:
            request: RequestQueue instance to process
            http_session: aiohttp ClientSession for making requests

        Returns:
            Response data from the API

        Raises:
            aiohttp.ClientError: If request fails
        """
        logger.info(
            f"Processing request {request.id}: {request.method} {request.endpoint}"
        )

        try:
            async with http_session.request(
                method=request.method,
                url=request.endpoint,
                json=request.payload,
                headers=request.headers,
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Mark as completed
                await self.mark_completed(request.id)

                return data

        except aiohttp.ClientError as e:
            # Handle failure with retry logic
            error_msg = str(e)
            error_details = {"error_type": type(e).__name__}

            if isinstance(e, aiohttp.ClientResponseError):
                error_details.update({
                    "status": e.status,
                    "message": e.message,
                })

            await self.mark_failed(request.id, error_msg, error_details)

            raise

    async def start_queue_processor(
        self,
        http_session_factory: callable,
    ) -> asyncio.Task:
        """Start the background queue processor.

        Args:
            http_session_factory: Callable that returns an aiohttp ClientSession

        Returns:
            asyncio.Task running the processor
        """
        async def processor_loop() -> None:
            """Main processing loop."""
            logger.info("Starting request queue processor")

            while True:
                try:
                    # Check if we're at capacity
                    if len(self._active_tasks) >= MAX_CONCURRENT_PROCESSING:
                        await asyncio.sleep(QUEUE_POLL_INTERVAL)
                        continue

                    # Get next batch of requests
                    requests = await self.dequeue_requests(limit=MAX_CONCURRENT_PROCESSING - len(self._active_tasks))

                    if not requests:
                        await asyncio.sleep(QUEUE_POLL_INTERVAL)
                        continue

                    # Process each request
                    http_session = http_session_factory()
                    for request in requests:
                        task = asyncio.create_task(
                            self._process_with_retry(request, http_session)
                        )
                        self._active_tasks.add(task)
                        task.add_done_callback(self._active_tasks.discard)

                except asyncio.CancelledError:
                    logger.info("Queue processor cancelled")
                    break
                except Exception as e:
                    logger.error(f"Queue processor error: {e}", exc_info=True)
                    await asyncio.sleep(QUEUE_POLL_INTERVAL)

        task = asyncio.create_task(processor_loop())
        logger.info("Queue processor task started")
        return task

    async def _process_with_retry(
        self,
        request: RequestQueue,
        http_session: aiohttp.ClientSession,
    ) -> None:
        """Process request with automatic retry on failure.

        Args:
            request: RequestQueue instance
            http_session: aiohttp ClientSession
        """
        try:
            await self.process_request(request, http_session)
        except Exception as e:
            logger.warning(f"Request {request.id} failed: {e}")

    # ================================================================
    # HELPER METHODS
    # ================================================================

    async def _get_request(self, request_id: UUID) -> RequestQueue:
        """Get a request by ID.

        Args:
            request_id: Request ID

        Returns:
            RequestQueue instance

        Raises:
            ValueError: If request not found
        """
        result = await self.session.execute(
            select(RequestQueue).where(RequestQueue.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError(f"Request not found: {request_id}")

        return request


# ================================================================
# DEPENDENCY
# ================================================================

def get_request_queue_service(session: AsyncSession) -> RequestQueueService:
    """Get request queue service instance.

    Args:
        session: Database session

    Returns:
        RequestQueueService instance
    """
    return RequestQueueService(session)
