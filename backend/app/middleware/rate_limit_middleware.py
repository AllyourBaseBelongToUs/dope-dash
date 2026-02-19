"""Rate limit detection middleware for HTTP clients.

This module provides an aiohttp client session wrapper that:
1. Detects 429 responses
2. Parses Retry-After headers
3. Records rate limit events
4. Implements exponential backoff retry
5. Emits WebSocket alerts

The middleware integrates with the rate limit service to provide
automatic retry with exponential backoff for rate-limited requests.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rate_limit import (
    RateLimitDetector,
    RetryAfterParser,
    ExponentialBackoffCalculator,
    MAX_RETRY_ATTEMPTS,
)
from app.models.quota import (
    RateLimitEventCreate,
    ProviderType,
)
from db.connection import get_db_session


logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Middleware for detecting and handling rate limits in HTTP requests.

    Wraps aiohttp requests to automatically detect 429 errors,
    record rate limit events, and implement exponential backoff retry.
    """

    def __init__(
        self,
        provider_type: ProviderType,
        project_name: str,
        session_id: uuid.UUID,
        provider_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        max_retries: int = MAX_RETRY_ATTEMPTS,
    ) -> None:
        """Initialize the rate limit middleware.

        Args:
            provider_type: Type of API provider (claude, openai, gemini, cursor)
            project_name: Name of the project
            session_id: Session UUID for tracking
            provider_id: Provider ID in database (optional, will be fetched if not provided)
            project_id: Project ID in database (optional)
            max_retries: Maximum number of retry attempts
        """
        self.provider_type = provider_type
        self.project_name = project_name
        self.session_id = session_id
        self.provider_id = provider_id
        self.project_id = project_id
        self.max_retries = max_retries
        self._rate_limit_detected = False

    async def _get_provider_id(self) -> uuid.UUID:
        """Get or fetch the provider ID from database.

        Returns:
            Provider UUID
        """
        if self.provider_id:
            return self.provider_id

        async with get_db_session() as db_session:
            from sqlalchemy import select
            from app.models.quota import Provider

            result = await db_session.execute(
                select(Provider).where(
                    Provider.provider_type == self.provider_type
                ).limit(1)
            )
            provider = result.scalar_one_or_none()

            if not provider:
                # Create provider if it doesn't exist
                provider = Provider(
                    provider_type=self.provider_type,
                    name=self.provider_type.value,
                    config={},
                )
                db_session.add(provider)
                await db_session.flush()
                await db_session.refresh(provider)

            self.provider_id = provider.id
            return provider.id

    async def _record_rate_limit_event(
        self,
        status_code: int,
        request_endpoint: str,
        request_method: str,
        response_headers: dict[str, str] | None = None,
        response_body: dict[str, Any] | str | None = None,
        attempt_number: int = 1,
    ) -> None:
        """Record a rate limit event to the database.

        Args:
            status_code: HTTP status code
            request_endpoint: Request URL/endpoint
            request_method: HTTP method
            response_headers: Response headers
            response_body: Response body
            attempt_number: Current attempt number
        """
        provider_id = await self._get_provider_id()

        # Parse retry-after header
        retry_after_seconds, retry_after_date = RetryAfterParser.extract_retry_after(
            response_headers
        )

        # Calculate backoff
        base_backoff = ExponentialBackoffCalculator.calculate_backoff(attempt_number)
        _, jitter_seconds = ExponentialBackoffCalculator.calculate_backoff_with_jitter(
            attempt_number
        )

        event_data = RateLimitEventCreate(
            provider_id=provider_id,
            project_id=self.project_id,
            session_id=self.session_id,
            http_status_code=status_code,
            request_endpoint=request_endpoint,
            request_method=request_method,
            response_headers=response_headers,
            error_details=str(response_body) if response_body else None,
            attempt_number=attempt_number,
            max_attempts=self.max_retries,
            retry_after_seconds=retry_after_seconds,
            calculated_backoff_seconds=base_backoff,
            jitter_seconds=jitter_seconds,
        )

        async with get_db_session() as db_session:
            from app.api.rate_limit import get_rate_limit_service

            rate_limit_service = get_rate_limit_service(db_session)
            await rate_limit_service.record_rate_limit_event(event_data)

        logger.warning(
            f"Rate limit detected for {self.provider_type.value} "
            f"(attempt {attempt_number}/{self.max_retries}): {request_method} {request_endpoint}"
        )
        self._rate_limit_detected = True

    def _get_retry_after_delay(
        self,
        response_headers: dict[str, str] | None = None,
        attempt_number: int = 1,
    ) -> float:
        """Get the delay before next retry.

        Args:
            response_headers: Response headers to check for Retry-After
            attempt_number: Current attempt number for exponential backoff

        Returns:
            Delay in seconds
        """
        return RetryAfterParser.get_effective_delay(
            response_headers,
            attempt_number,
        )

    async def should_retry_request(
        self,
        status_code: int,
        response_headers: dict[str, str] | None = None,
        response_body: dict[str, Any] | str | None = None,
        attempt_number: int = 1,
    ) -> bool:
        """Check if a request should be retried due to rate limiting.

        Args:
            status_code: HTTP status code
            response_headers: Response headers
            response_body: Response body
            attempt_number: Current attempt number

        Returns:
            True if request should be retried
        """
        if attempt_number > self.max_retries:
            return False

        return RateLimitDetector.is_rate_limit_error(
            status_code=status_code,
            response_headers=response_headers,
            response_body=response_body,
        )


class RateLimitAwareClient:
    """Aiohttp-like client session with automatic rate limit handling.

    Wraps aiohttp.ClientSession to provide automatic 429 detection,
    rate limit event recording, and exponential backoff retry.

    Usage:
        client = RateLimitAwareClient(
            provider_type=ProviderType.CLAUDE,
            project_name="my-project",
            session_id=session_id,
        )

        async with client.get("https://api.example.com/endpoint") as response:
            data = await response.json()

        await client.close()
    """

    def __init__(
        self,
        provider_type: ProviderType,
        project_name: str,
        session_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        max_retries: int = MAX_RETRY_ATTEMPTS,
        base_session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the rate limit aware client.

        Args:
            provider_type: Type of API provider
            project_name: Name of the project
            session_id: Session UUID
            project_id: Project UUID (optional)
            max_retries: Maximum retry attempts
            base_session: Existing aiohttp session to wrap (optional)
        """
        self.middleware = RateLimitMiddleware(
            provider_type=provider_type,
            project_name=project_name,
            session_id=session_id,
            project_id=project_id,
            max_retries=max_retries,
        )

        if base_session:
            self._session = base_session
            self._own_session = False
        else:
            self._session = aiohttp.ClientSession()
            self._own_session = True

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> RateLimitAwareClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        attempt_number: int = 1,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse | None:
        """Make HTTP request with automatic rate limit retry.

        Args:
            method: HTTP method
            url: Request URL
            attempt_number: Current attempt number
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse or None if max retries exceeded

        Raises:
            aiohttp.ClientError: For non-rate-limit errors
        """
        response = await self._session.request(method, url, **kwargs)

        # Get response headers and body for rate limit detection
        response_headers = dict(response.headers)
        response_body = None

        # Try to read response body for error details
        if response.status >= 400:
            try:
                content_type = response_headers.get("Content-Type", "")
                if "application/json" in content_type:
                    response_body = await response.json()
                else:
                    response_body = await response.text()
            except Exception:
                response_body = None

        # Check if this is a rate limit error
        is_rate_limited = await self.middleware.should_retry_request(
            status_code=response.status,
            response_headers=response_headers,
            response_body=response_body,
            attempt_number=attempt_number,
        )

        if not is_rate_limited:
            return response

        # Record the rate limit event
        await self.middleware._record_rate_limit_event(
            status_code=response.status,
            request_endpoint=url,
            request_method=method,
            response_headers=response_headers,
            response_body=response_body,
            attempt_number=attempt_number,
        )

        # Close the current response
        response.close()

        # Check if we should retry
        if attempt_number >= self.middleware.max_retries:
            logger.error(
                f"Max retries ({self.middleware.max_retries}) exceeded "
                f"for {method} {url}"
            )
            return None

        # Get retry delay
        retry_delay = self.middleware._get_retry_after_delay(
            response_headers=response_headers,
            attempt_number=attempt_number,
        )

        logger.info(
            f"Retrying {method} {url} after {retry_delay:.2f}s "
            f"(attempt {attempt_number + 1}/{self.middleware.max_retries})"
        )

        # Wait before retry
        await asyncio.sleep(retry_delay)

        # Retry request
        return await self._make_request_with_retry(
            method,
            url,
            attempt_number=attempt_number + 1,
            **kwargs,
        )

    async def get(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make GET request with rate limit handling.

        Args:
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse
        """
        response = await self._make_request_with_retry("GET", url, **kwargs)
        if response is None:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore
                history=None,
                status=429,
                message=f"Rate limit: max retries ({self.middleware.max_retries}) exceeded",
            )
        return response

    async def post(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make POST request with rate limit handling.

        Args:
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse
        """
        response = await self._make_request_with_retry("POST", url, **kwargs)
        if response is None:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore
                history=None,
                status=429,
                message=f"Rate limit: max retries ({self.middleware.max_retries}) exceeded",
            )
        return response

    async def put(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make PUT request with rate limit handling.

        Args:
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse
        """
        response = await self._make_request_with_retry("PUT", url, **kwargs)
        if response is None:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore
                history=None,
                status=429,
                message=f"Rate limit: max retries ({self.middleware.max_retries}) exceeded",
            )
        return response

    async def delete(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make DELETE request with rate limit handling.

        Args:
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse
        """
        response = await self._make_request_with_retry("DELETE", url, **kwargs)
        if response is None:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore
                history=None,
                status=429,
                message=f"Rate limit: max retries ({self.middleware.max_retries}) exceeded",
            )
        return response

    async def patch(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make PATCH request with rate limit handling.

        Args:
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse
        """
        response = await self._make_request_with_retry("PATCH", url, **kwargs)
        if response is None:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore
                history=None,
                status=429,
                message=f"Rate limit: max retries ({self.middleware.max_retries}) exceeded",
            )
        return response

    async def request(self, method: str, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make HTTP request with rate limit handling.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            aiohttp.ClientResponse
        """
        response = await self._make_request_with_retry(method, url, **kwargs)
        if response is None:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore
                history=None,
                status=429,
                message=f"Rate limit: max retries ({self.middleware.max_retries}) exceeded",
            )
        return response


async def create_rate_limit_aware_client(
    provider_type: ProviderType,
    project_name: str,
    session_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    max_retries: int = MAX_RETRY_ATTEMPTS,
) -> RateLimitAwareClient:
    """Factory function to create a rate limit aware client.

    Args:
        provider_type: Type of API provider
        project_name: Name of the project
        session_id: Session UUID
        project_id: Project UUID (optional)
        max_retries: Maximum retry attempts

    Returns:
        RateLimitAwareClient instance

    Example:
        client = await create_rate_limit_aware_client(
            provider_type=ProviderType.CLAUDE,
            project_name="my-project",
            session_id=session_id,
        )

        async with client.get("https://api.example.com/data") as response:
            data = await response.json()

        await client.close()
    """
    return RateLimitAwareClient(
        provider_type=provider_type,
        project_name=project_name,
        session_id=session_id,
        project_id=project_id,
        max_retries=max_retries,
    )
