"""Rate limit detection and exponential backoff retry service.

This service provides:
- 429 error detection from HTTP responses
- Retry-After header parsing (seconds and HTTP-date formats)
- Exponential backoff calculation with jitter
- Automatic retry queue management
- Rate limit event logging and tracking
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import random
import re
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quota import (
    Provider,
    ProviderType,
    RateLimitEvent,
    RateLimitEventStatus,
    RateLimitEventCreate,
    RateLimitEventResponse,
    RateLimitEventSummary,
)


logger = logging.getLogger(__name__)


# Constants
MAX_RETRY_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 1  # First retry waits 1 second
MAX_BACKOFF_SECONDS = 32  # Cap at 32 seconds
JITTER_RATIO = 0.25  # Add +/- 25% jitter to prevent thundering herd


class ExponentialBackoffCalculator:
    """Calculates exponential backoff with jitter for rate limit retries.

    Implements the following pattern:
    - Attempt 1: 1 second (base)
    - Attempt 2: 2 seconds (2^1)
    - Attempt 3: 4 seconds (2^2)
    - Attempt 4: 8 seconds (2^3)
    - Attempt 5: 16 seconds (2^4)

    Each delay includes random jitter to prevent thundering herd.
    """

    @staticmethod
    def calculate_backoff(attempt_number: int) -> int:
        """Calculate exponential backoff delay in seconds.

        Args:
            attempt_number: Current attempt number (1-based)

        Returns:
            Backoff delay in seconds (capped at MAX_BACKOFF_SECONDS)

        Examples:
            >>> ExponentialBackoffCalculator.calculate_backoff(1)
            1
            >>> ExponentialBackoffCalculator.calculate_backoff(2)
            2
            >>> ExponentialBackoffCalculator.calculate_backoff(3)
            4
        """
        if attempt_number < 1:
            attempt_number = 1

        # Calculate exponential backoff: 2^(attempt_number - 1)
        # Attempt 1: 2^0 = 1s
        # Attempt 2: 2^1 = 2s
        # Attempt 3: 2^2 = 4s
        # etc.
        backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt_number - 1))

        # Cap at maximum
        return min(backoff, MAX_BACKOFF_SECONDS)

    @staticmethod
    def calculate_backoff_with_jitter(attempt_number: int) -> tuple[int, int]:
        """Calculate backoff with random jitter to prevent thundering herd.

        Args:
            attempt_number: Current attempt number (1-based)

        Returns:
            Tuple of (base_backoff_seconds, jitter_seconds)

        The jitter is +/- JITTER_RATIO (25%) of the base backoff.
        """
        base = ExponentialBackoffCalculator.calculate_backoff(attempt_number)

        # Calculate jitter: +/- 10% of base
        jitter_range = int(base * JITTER_RATIO)
        jitter = random.randint(-jitter_range, jitter_range)

        # Ensure final delay is at least 0
        final_jitter = max(0, base + jitter - base)

        return base, final_jitter

    @staticmethod
    def get_total_delay(attempt_number: int) -> int:
        """Get total delay including jitter.

        Args:
            attempt_number: Current attempt number (1-based)

        Returns:
            Total delay in seconds (base + jitter)
        """
        base, jitter = ExponentialBackoffCalculator.calculate_backoff_with_jitter(attempt_number)
        return base + jitter


class RetryAfterParser:
    """Parser for Retry-After HTTP headers.

    Supports two formats per RFC 7231:
    1. Delay-seconds: "Retry-After: 120" (integer seconds)
    2. HTTP-date: "Retry-After: Fri, 31 Dec 2026 23:59:59 GMT"
    """

    # RFC 7231 HTTP-date format
    HTTP_DATE_PATTERN = re.compile(
        r"^\w{3},\s+\d{2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+GMT$"
    )

    @staticmethod
    def parse(retry_after_header: str | None) -> tuple[int | None, datetime.datetime | None]:
        """Parse Retry-After header.

        Args:
            retry_after_header: Value of Retry-After header

        Returns:
            Tuple of (retry_after_seconds, retry_after_date)
            Only one will be set depending on header format
        """
        if not retry_after_header:
            return None, None

        retry_after_header = retry_after_header.strip()

        # Try parsing as delay-seconds (integer)
        if retry_after_header.isdigit():
            return int(retry_after_header), None

        # Try parsing as HTTP-date
        if RetryAfterParser.HTTP_DATE_PATTERN.match(retry_after_header):
            try:
                retry_date = parsedate_to_datetime(retry_after_header)
                if retry_date:
                    # Calculate seconds until retry date
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if retry_date.tzinfo is None:
                        retry_date = retry_date.replace(tzinfo=datetime.timezone.utc)

                    seconds = max(0, int((retry_date - now).total_seconds()))
                    return seconds, retry_date
            except Exception as e:
                logger.debug(f"Failed to parse Retry-After HTTP-date: {e}")

        logger.warning(f"Unable to parse Retry-After header: {retry_after_header}")
        return None, None

    @staticmethod
    def get_effective_delay(
        retry_after_header: str | None,
        attempt_number: int,
    ) -> int:
        """Get the effective delay to wait before retry.

        Uses the Retry-After header if present and valid,
        otherwise falls back to exponential backoff.

        Args:
            retry_after_header: Value of Retry-After header
            attempt_number: Current attempt number

        Returns:
            Delay in seconds to wait before retry
        """
        retry_after_seconds, _ = RetryAfterParser.parse(retry_after_header)

        # Use Retry-After if provided and positive
        if retry_after_seconds and retry_after_seconds > 0:
            return retry_after_seconds

        # Fall back to exponential backoff
        return ExponentialBackoffCalculator.get_total_delay(attempt_number)


class RateLimitDetector:
    """Detects rate limit errors from HTTP responses.

    Checks for:
    - HTTP 429 status code
    - Rate limit related error messages in response body
    - Common rate limit headers
    """

    # Common rate limit headers to check
    RATE_LIMIT_HEADERS = [
        "retry-after",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
        "x-rate-limit-exceeded",
        "ratelimit-remaining",
        "ratelimit-reset",
    ]

    # Common rate limit error patterns
    RATE_LIMIT_PATTERNS = [
        r"rate limit",
        r"rate-limit",
        r"ratelimit",
        r"too many requests",
        r"quota exceeded",
        r"throttl",
        r"429",
    ]

    @staticmethod
    def is_rate_limit_error(
        status_code: int,
        response_headers: dict[str, str] | None = None,
        response_body: dict[str, Any] | str | None = None,
    ) -> bool:
        """Check if response indicates a rate limit error.

        Args:
            status_code: HTTP status code
            response_headers: Response headers dict
            response_body: Response body (dict or string)

        Returns:
            True if this is a rate limit error
        """
        # Check status code
        if status_code == 429:
            return True

        # Check headers for rate limit indicators
        if response_headers:
            for header in response_headers:
                if header.lower() in RateLimitDetector.RATE_LIMIT_HEADERS:
                    return True

        # Check response body for rate limit patterns
        if response_body:
            # Convert to string if needed
            body_str = (
                str(response_body)
                if not isinstance(response_body, str)
                else response_body
            ).lower()

            for pattern in RateLimitDetector.RATE_LIMIT_PATTERNS:
                if re.search(pattern, body_str):
                    return True

        return False

    @staticmethod
    def extract_retry_after(
        response_headers: dict[str, str] | None = None,
    ) -> tuple[int | None, datetime.datetime | None]:
        """Extract and parse Retry-After header.

        Args:
            response_headers: Response headers dict

        Returns:
            Tuple of (retry_after_seconds, retry_after_date)
        """
        if not response_headers:
            return None, None

        # Check various case variations of the header name
        for key, value in response_headers.items():
            if key.lower() == "retry-after":
                return RetryAfterParser.parse(value)

        return None, None


class RateLimitService:
    """Service for managing rate limit events and retries.

    Provides:
    - Rate limit event recording and tracking
    - Retry queue management
    - Event history and summary
    - WebSocket broadcasts for rate limit alerts
    """

    def __init__(self, session: AsyncSession):
        """Initialize the rate limit service.

        Args:
            session: Database session for queries
        """
        self._session = session
        self._retry_queue: asyncio.Queue[RateLimitEvent] = asyncio.Queue()

    # ========== Event Recording ==========

    async def record_rate_limit_event(
        self,
        request: RateLimitEventCreate,
    ) -> RateLimitEvent:
        """Record a rate limit event.

        Args:
            request: Rate limit event creation request

        Returns:
            Created RateLimitEvent instance
        """
        # Verify provider exists
        provider = await self._get_provider(request.provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {request.provider_id}")

        # Extract retry-after from headers
        retry_after_seconds, retry_after_date = RetryAfterParser.extract_retry_after(
            request.response_headers
        )

        # Create event
        event = RateLimitEvent(
            provider_id=request.provider_id,
            project_id=request.project_id,
            session_id=request.session_id,
            http_status_code=request.http_status_code,
            request_endpoint=request.request_endpoint,
            request_method=request.request_method,
            response_headers=request.response_headers,
            retry_after_seconds=retry_after_seconds or request.retry_after_seconds,
            retry_after_date=retry_after_date or request.retry_after_date,
            attempt_number=request.metadata.get("attempt_number", 1),
            max_attempts=request.metadata.get("max_attempts", MAX_RETRY_ATTEMPTS),
            status=RateLimitEventStatus.DETECTED,
            error_details=request.error_details,
            metadata=request.metadata,
        )
        self._session.add(event)
        await self._session.flush()

        logger.warning(
            f"Rate limit event recorded: {event.id} for provider {provider.name.value} "
            f"at {request.request_endpoint} (attempt {event.attempt_number}/{event.max_attempts})"
        )

        # Broadcast event via WebSocket
        await self._broadcast_rate_limit_event(event, provider)

        return event

    async def update_event_retrying(
        self,
        event_id: UUID,
        backoff_seconds: int,
        jitter_seconds: int,
    ) -> RateLimitEvent | None:
        """Mark an event as retrying with backoff info.

        Args:
            event_id: Event UUID
            backoff_seconds: Calculated backoff delay
            jitter_seconds: Applied jitter

        Returns:
            Updated event or None
        """
        event = await self._get_event(event_id)
        if event and event.should_retry:
            event.mark_retrying(backoff_seconds, jitter_seconds)
            await self._session.flush()

            logger.info(
                f"Rate limit event {event_id} retrying: "
                f"attempt {event.attempt_number}/{event.max_attempts} "
                f"after {backoff_seconds + jitter_seconds}s delay"
            )

        return event

    async def mark_event_resolved(self, event_id: UUID) -> RateLimitEvent | None:
        """Mark an event as successfully resolved.

        Args:
            event_id: Event UUID

        Returns:
            Updated event or None
        """
        event = await self._get_event(event_id)
        if event:
            event.mark_resolved()
            await self._session.flush()

            logger.info(f"Rate limit event {event_id} resolved after {event.attempt_number} attempts")

            # Broadcast resolution
            await self._broadcast_rate_limit_resolution(event)

        return event

    async def mark_event_failed(self, event_id: UUID) -> RateLimitEvent | None:
        """Mark an event as failed after max retries.

        Args:
            event_id: Event UUID

        Returns:
            Updated event or None
        """
        event = await self._get_event(event_id)
        if event:
            event.mark_failed()
            await self._session.flush()

            logger.error(
                f"Rate limit event {event_id} failed after "
                f"{event.max_attempts} retry attempts"
            )

            # Broadcast failure
            await self._broadcast_rate_limit_failure(event)

        return event

    # ========== Event Queries ==========

    async def get_event(self, event_id: UUID) -> RateLimitEventResponse | None:
        """Get a rate limit event by ID.

        Args:
            event_id: Event UUID

        Returns:
            Event response or None
        """
        event = await self._get_event(event_id)
        if not event:
            return None

        return self._event_to_response(event)

    async def get_events(
        self,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
        status: RateLimitEventStatus | None = None,
        limit: int = 100,
    ) -> list[RateLimitEventResponse]:
        """Get rate limit events with filters.

        Args:
            provider_id: Optional provider filter
            project_id: Optional project filter
            status: Optional status filter
            limit: Maximum number of events to return

        Returns:
            List of event responses
        """
        query = select(RateLimitEvent).order_by(
            RateLimitEvent.detected_at.desc()
        )

        if provider_id:
            query = query.where(RateLimitEvent.provider_id == provider_id)
        if project_id:
            query = query.where(RateLimitEvent.project_id == project_id)
        if status:
            query = query.where(RateLimitEvent.status == status)

        query = query.limit(limit)

        result = await self._session.execute(query)
        events = result.scalars().all()

        return [self._event_to_response(e) for e in events]

    async def get_active_events(
        self,
        provider_id: UUID | None = None,
    ) -> list[RateLimitEvent]:
        """Get all active (detected/retrying) events.

        Args:
            provider_id: Optional provider filter

        Returns:
            List of active RateLimitEvent instances
        """
        query = select(RateLimitEvent).where(
            and_(
                RateLimitEvent.status.in_([
                    RateLimitEventStatus.DETECTED,
                    RateLimitEventStatus.RETRYING,
                ]),
                RateLimitEvent.should_retry == True,  # type: ignore
            )
        ).order_by(RateLimitEvent.detected_at.desc())

        if provider_id:
            query = query.where(RateLimitEvent.provider_id == provider_id)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_event_summary(
        self,
        provider_id: UUID | None = None,
    ) -> RateLimitEventSummary:
        """Get summary of rate limit events.

        Args:
            provider_id: Optional provider filter

        Returns:
            Event summary
        """
        # Get base query
        query = select(RateLimitEvent)
        if provider_id:
            query = query.where(RateLimitEvent.provider_id == provider_id)

        # Get all events
        result = await self._session.execute(query.order_by(RateLimitEvent.detected_at.desc()).limit(100))
        events = list(result.scalars().all())

        # Calculate summary
        total = len(events)
        active = sum(1 for e in events if e.status == RateLimitEventStatus.DETECTED)
        retrying = sum(1 for e in events if e.status == RateLimitEventStatus.RETRYING)
        resolved = sum(1 for e in events if e.status == RateLimitEventStatus.RESOLVED)
        failed = sum(1 for e in events if e.status == RateLimitEventStatus.FAILED)

        # Count by provider
        by_provider: dict[str, int] = {}
        for event in events:
            provider = await self._get_provider(event.provider_id)
            if provider:
                name = provider.name.value
                by_provider[name] = by_provider.get(name, 0) + 1

        return RateLimitEventSummary(
            total_events=total,
            active_events=active + retrying,
            resolved_events=resolved,
            failed_events=failed,
            by_provider=by_provider,
            recent_events=[self._event_to_response(e) for e in events[:10]],
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    # ========== Helpers ==========

    def _calculate_retry_backoff(self, attempt_number: int) -> tuple[int, int]:
        """Calculate backoff with jitter for a retry attempt.

        Args:
            attempt_number: Current attempt number (1-based)

        Returns:
            Tuple of (base_backoff_seconds, jitter_seconds)
        """
        return ExponentialBackoffCalculator.calculate_backoff_with_jitter(attempt_number)

    async def _get_provider(self, provider_id: UUID) -> Provider | None:
        """Get provider by ID."""
        result = await self._session.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        return result.scalars().first()

    async def _get_event(self, event_id: UUID) -> RateLimitEvent | None:
        """Get event by ID."""
        result = await self._session.execute(
            select(RateLimitEvent).where(RateLimitEvent.id == event_id)
        )
        return result.scalars().first()

    def _event_to_response(self, event: RateLimitEvent) -> RateLimitEventResponse:
        """Convert event to response schema."""
        return RateLimitEventResponse(
            id=event.id,
            provider_id=event.provider_id,
            project_id=event.project_id,
            session_id=event.session_id,
            http_status_code=event.http_status_code,
            request_endpoint=event.request_endpoint,
            request_method=event.request_method,
            response_headers=event.response_headers,
            retry_after_seconds=event.retry_after_seconds,
            retry_after_date=event.retry_after_date,
            attempt_number=event.attempt_number,
            max_attempts=event.max_attempts,
            status=event.status.value,
            calculated_backoff_seconds=event.calculated_backoff_seconds,
            jitter_seconds=event.jitter_seconds,
            error_details=event.error_details,
            resolved_at=event.resolved_at,
            failed_at=event.failed_at,
            metadata=event.metadata,
            detected_at=event.detected_at,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    # ========== WebSocket Broadcasts ==========

    async def _broadcast_rate_limit_event(
        self,
        event: RateLimitEvent,
        provider: Provider,
    ) -> None:
        """Broadcast rate limit event via WebSocket.

        Args:
            event: RateLimitEvent instance
            provider: Provider instance
        """
        try:
            from server.websocket import manager

            message = {
                "type": "rate_limit_detected",
                "data": {
                    "event_id": str(event.id),
                    "provider_id": str(event.provider_id),
                    "provider_name": provider.name.value,
                    "project_id": str(event.project_id) if event.project_id else None,
                    "http_status_code": event.http_status_code,
                    "request_endpoint": event.request_endpoint,
                    "retry_after_seconds": event.retry_after_seconds,
                    "attempt_number": event.attempt_number,
                    "max_attempts": event.max_attempts,
                    "timestamp": event.detected_at.isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast rate limit event: {e}")

    async def _broadcast_rate_limit_resolution(
        self,
        event: RateLimitEvent,
    ) -> None:
        """Broadcast rate limit resolution via WebSocket.

        Args:
            event: RateLimitEvent instance
        """
        try:
            from server.websocket import manager

            message = {
                "type": "rate_limit_resolved",
                "data": {
                    "event_id": str(event.id),
                    "provider_id": str(event.provider_id),
                    "attempt_number": event.attempt_number,
                    "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast rate limit resolution: {e}")

    async def _broadcast_rate_limit_failure(
        self,
        event: RateLimitEvent,
    ) -> None:
        """Broadcast rate limit failure via WebSocket.

        Args:
            event: RateLimitEvent instance
        """
        try:
            from server.websocket import manager

            message = {
                "type": "rate_limit_failed",
                "data": {
                    "event_id": str(event.id),
                    "provider_id": str(event.provider_id),
                    "max_attempts": event.max_attempts,
                    "failed_at": event.failed_at.isoformat() if event.failed_at else None,
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast rate limit failure: {e}")


# ========== Dependency ==========

def get_rate_limit_service(session: AsyncSession) -> RateLimitService:
    """Get rate limit service instance.

    Args:
        session: Database session

    Returns:
        RateLimitService instance
    """
    return RateLimitService(session)
