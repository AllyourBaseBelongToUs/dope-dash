"""Quota tracking service for API provider quota monitoring.

This service provides:
- Provider management (CRUD operations)
- Quota usage tracking and updates
- Quota alert generation and management
- Quota summary and statistics
- Real-time WebSocket broadcasts for quota updates
- Automatic quota reset detection
"""
from __future__ import annotations

import datetime
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quota import (
    Provider,
    ProviderType,
    ProviderResponse,
    ProviderListResponse,
    QuotaUsage,
    QuotaUsageResponse,
    QuotaUsageListResponse,
    QuotaAlert,
    QuotaAlertResponse,
    QuotaAlertListResponse,
    QuotaAlertType,
    QuotaAlertStatus,
    QuotaSummaryResponse,
    QuotaResetType,
)


logger = logging.getLogger(__name__)

# Alert thresholds
WARNING_THRESHOLD = 80  # 80% usage
CRITICAL_THRESHOLD = 95  # 95% usage


class QuotaService:
    """Service for managing API quota tracking and alerts.

    Provides:
    - Provider CRUD operations
    - Quota usage tracking with automatic reset detection
    - Alert generation when thresholds are exceeded
    - Summary statistics
    - WebSocket broadcasts for real-time updates
    """

    def __init__(self, session: AsyncSession):
        """Initialize the quota service.

        Args:
            session: Database session for queries
        """
        self._session = session

    # ========== Provider Operations ==========

    async def get_providers(
        self,
        active_only: bool = False,
    ) -> ProviderListResponse:
        """Get all providers.

        Args:
            active_only: If True, only return active providers

        Returns:
            List of providers
        """
        query = select(Provider)

        if active_only:
            query = query.where(Provider.is_active == True)

        query = query.order_by(Provider.name)

        result = await self._session.execute(query)
        providers = list(result.scalars().all())

        return ProviderListResponse(
            items=[self._provider_to_response(p) for p in providers],
            total=len(providers),
        )

    def _provider_to_response(self, provider: Provider) -> ProviderResponse:
        """Convert Provider to response schema with computed fields."""
        # Get models from metadata if available
        models = provider.meta_data.get("models", [])

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            api_endpoint=provider.api_endpoint,
            rate_limit_rpm=provider.rate_limit_rpm,
            rate_limit_rph=provider.rate_limit_rph,
            rate_limit_tpm=provider.rate_limit_tpm,
            rate_limit_tokens_per_day=provider.rate_limit_tokens_per_day,
            default_quota_limit=provider.default_quota_limit,
            quota_reset_type=provider.quota_reset_type,
            quota_reset_day_of_month=provider.quota_reset_day_of_month,
            quota_reset_hour=provider.quota_reset_hour,
            quota_reset_timezone=provider.quota_reset_timezone,
            is_active=provider.is_active,
            meta_data=provider.meta_data,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
            models=models,
            enabled=provider.is_active,
            priority=0,
        )

    async def get_provider(self, provider_id: UUID) -> Provider | None:
        """Get a provider by ID.

        Args:
            provider_id: Provider UUID

        Returns:
            Provider instance or None
        """
        result = await self._session.execute(
            select(Provider).where(Provider.id == provider_id)
        )
        return result.scalars().first()

    async def get_provider_by_name(self, name: ProviderType) -> Provider | None:
        """Get a provider by name.

        Args:
            name: Provider type name

        Returns:
            Provider instance or None
        """
        result = await self._session.execute(
            select(Provider).where(Provider.name == name)
        )
        return result.scalars().first()

    # ========== Quota Usage Operations ==========

    async def get_quota_usage(
        self,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> QuotaUsageListResponse:
        """Get quota usage records.

        Args:
            provider_id: Optional provider filter
            project_id: Optional project filter (null for global quota)

        Returns:
            List of quota usage records
        """
        query = select(QuotaUsage).options(selectinload(QuotaUsage.provider))

        if provider_id:
            query = query.where(QuotaUsage.provider_id == provider_id)
        if project_id is not None:
            query = query.where(QuotaUsage.project_id == project_id)

        result = await self._session.execute(query)
        usages = list(result.scalars().all())

        # Check for quota resets and update if needed
        updated_usages = []
        for usage in usages:
            if self._should_reset_quota(usage):
                await self._reset_quota(usage)
            updated_usages.append(self._usage_to_response(usage))

        return QuotaUsageListResponse(
            items=updated_usages,
            total=len(updated_usages),
        )

    async def get_or_create_quota_usage(
        self,
        provider_id: UUID,
        project_id: UUID | None = None,
    ) -> QuotaUsage:
        """Get or create quota usage record for a provider/project.

        Args:
            provider_id: Provider UUID
            project_id: Optional project UUID (null for global)

        Returns:
            QuotaUsage instance
        """
        # Try to get existing
        query = select(QuotaUsage).where(
            and_(
                QuotaUsage.provider_id == provider_id,
                QuotaUsage.project_id == project_id,
            )
        )
        result = await self._session.execute(query)
        usage = result.scalars().first()

        if usage:
            # Check for reset
            if self._should_reset_quota(usage):
                await self._reset_quota(usage)
            return usage

        # Get provider for defaults
        provider = await self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        # Calculate period
        now = datetime.datetime.now(datetime.timezone.utc)
        period_start = now
        period_end = self._calculate_period_end(now, provider)

        # Create new usage record
        usage = QuotaUsage(
            provider_id=provider_id,
            project_id=project_id,
            current_requests=0,
            current_tokens=0,
            quota_limit=provider.default_quota_limit,
            quota_limit_tokens=provider.rate_limit_tokens_per_day,
            period_start=period_start,
            period_end=period_end,
            last_reset_at=now,
            overage_count=0,
        )
        self._session.add(usage)
        await self._session.flush()

        return usage

    async def increment_usage(
        self,
        provider_id: UUID,
        requests: int = 1,
        tokens: int = 0,
        project_id: UUID | None = None,
    ) -> QuotaUsage:
        """Increment quota usage for a provider.

        Args:
            provider_id: Provider UUID
            requests: Number of requests to add
            tokens: Number of tokens to add
            project_id: Optional project UUID

        Returns:
            Updated QuotaUsage instance
        """
        usage = await self.get_or_create_quota_usage(provider_id, project_id)

        # Check for reset before incrementing
        if self._should_reset_quota(usage):
            await self._reset_quota(usage)

        # Increment usage
        usage.current_requests += requests
        usage.current_tokens += tokens
        usage.last_request_at = datetime.datetime.now(datetime.timezone.utc)

        # Check for overage
        if usage.is_over_limit:
            usage.overage_count += 1

        await self._session.flush()

        # Check thresholds and create alerts
        await self._check_thresholds(usage)

        # Broadcast update
        await self._broadcast_quota_update(usage)

        return usage

    # ========== Alert Operations ==========

    async def get_alerts(
        self,
        status: QuotaAlertStatus | None = None,
        provider_id: UUID | None = None,
        limit: int = 100,
    ) -> QuotaAlertListResponse:
        """Get quota alerts.

        Args:
            status: Optional status filter
            provider_id: Optional provider filter
            limit: Maximum number of alerts to return

        Returns:
            List of quota alerts
        """
        query = (
            select(QuotaAlert)
            .options(selectinload(QuotaAlert.quota_usage))
            .order_by(QuotaAlert.created_at.desc())
        )

        if status:
            query = query.where(QuotaAlert.status == status)
        if provider_id:
            # Join through quota_usage to filter by provider
            query = query.join(QuotaUsage).where(
                QuotaUsage.provider_id == provider_id
            )

        query = query.limit(limit)

        result = await self._session.execute(query)
        alerts = list(result.scalars().all())

        return QuotaAlertListResponse(
            items=[self._alert_to_response(a) for a in alerts],
            total=len(alerts),
        )

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        acknowledged_by: str | None = None,
    ) -> QuotaAlert | None:
        """Acknowledge an alert.

        Args:
            alert_id: Alert UUID
            acknowledged_by: User who acknowledged

        Returns:
            Updated alert or None
        """
        alert = await self._get_alert(alert_id)
        if alert:
            alert.acknowledge(acknowledged_by)
            await self._session.flush()

            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")

        return alert

    async def resolve_alert(self, alert_id: UUID) -> QuotaAlert | None:
        """Resolve an alert.

        Args:
            alert_id: Alert UUID

        Returns:
            Updated alert or None
        """
        alert = await self._get_alert(alert_id)
        if alert:
            alert.resolve()
            await self._session.flush()

            logger.info(f"Alert {alert_id} resolved")

        return alert

    # ========== Summary Operations ==========

    async def get_summary(self) -> QuotaSummaryResponse:
        """Get quota summary statistics.

        Returns:
            Quota summary
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        # Get all providers
        providers_result = await self._session.execute(
            select(Provider).where(Provider.is_active == True)
        )
        providers = list(providers_result.scalars().all())

        # Get all global quota usages (project_id is null)
        usages_result = await self._session.execute(
            select(QuotaUsage).where(QuotaUsage.project_id == None)
        )
        usages = list(usages_result.scalars().all())

        # Calculate totals
        total_requests = sum(u.current_requests for u in usages)
        total_tokens = sum(u.current_tokens for u in usages)

        # Calculate average usage percent
        if usages:
            total_usage_percent = sum(u.usage_percent for u in usages) / len(usages)
        else:
            total_usage_percent = 0.0

        # Count providers over limit
        providers_over_limit = sum(1 for u in usages if u.is_over_limit)

        # Get alert counts
        alerts_result = await self._session.execute(
            select(QuotaAlert).where(QuotaAlert.status == QuotaAlertStatus.ACTIVE)
        )
        active_alerts = list(alerts_result.scalars().all())

        alerts_critical = sum(
            1 for a in active_alerts
            if a.alert_type in (QuotaAlertType.CRITICAL, QuotaAlertType.OVERAGE)
        )

        return QuotaSummaryResponse(
            total_providers=len(providers),
            active_providers=len(providers),
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_usage_percent=round(total_usage_percent, 1),
            alerts_count=len(active_alerts),
            alerts_critical=alerts_critical,
            providers_over_limit=providers_over_limit,
            last_updated=now,
        )

    # ========== Private Helpers ==========

    def _should_reset_quota(self, usage: QuotaUsage) -> bool:
        """Check if quota should be reset based on period end.

        Args:
            usage: QuotaUsage instance

        Returns:
            True if quota should be reset
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        return now >= usage.period_end

    async def _reset_quota(self, usage: QuotaUsage) -> None:
        """Reset quota for a new period.

        Args:
            usage: QuotaUsage instance to reset
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        # Get provider to calculate new period
        provider = await self.get_provider(usage.provider_id)
        if not provider:
            return

        # Reset usage
        usage.current_requests = 0
        usage.current_tokens = 0
        usage.period_start = now
        usage.period_end = self._calculate_period_end(now, provider)
        usage.last_reset_at = now

        logger.info(
            f"Quota reset for provider {provider.name.value}, "
            f"new period ends at {usage.period_end}"
        )

        # Resolve any active alerts for this usage
        active_alerts_result = await self._session.execute(
            select(QuotaAlert).where(
                and_(
                    QuotaAlert.quota_usage_id == usage.id,
                    QuotaAlert.status == QuotaAlertStatus.ACTIVE,
                )
            )
        )
        for alert in active_alerts_result.scalars().all():
            alert.resolve()

        await self._session.flush()

    def _calculate_period_end(
        self,
        start: datetime.datetime,
        provider: Provider,
    ) -> datetime.datetime:
        """Calculate the end of a quota period.

        Args:
            start: Period start datetime
            provider: Provider instance

        Returns:
            Period end datetime
        """
        if provider.quota_reset_type == QuotaResetType.DAILY:
            # Next day at reset hour
            tomorrow = start + datetime.timedelta(days=1)
            return tomorrow.replace(
                hour=provider.quota_reset_hour,
                minute=0,
                second=0,
                microsecond=0,
            )
        elif provider.quota_reset_type == QuotaResetType.MONTHLY:
            # Next month on specified day
            day = provider.quota_reset_day_of_month or 1
            if start.month == 12:
                next_month = start.replace(
                    year=start.year + 1,
                    month=1,
                    day=day,
                    hour=provider.quota_reset_hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            else:
                next_month = start.replace(
                    month=start.month + 1,
                    day=day,
                    hour=provider.quota_reset_hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            return next_month
        else:
            # Fixed date - default to 30 days
            return start + datetime.timedelta(days=30)

    async def _check_thresholds(self, usage: QuotaUsage) -> None:
        """Check usage thresholds and create alerts if needed.

        Uses the enhanced QuotaAlertService for multi-channel alerting
        with cooldown, escalation, and per-provider configuration.

        Args:
            usage: QuotaUsage instance
        """
        try:
            from app.services.quota_alerts import get_quota_alert_service

            alert_service = get_quota_alert_service(self._session)
            await alert_service.check_and_send_alert(usage)
        except Exception as e:
            logger.warning(f"Failed to send enhanced alert, falling back to basic: {e}")
            # Fallback to basic alerting
            await self._check_thresholds_basic(usage)

    async def _check_thresholds_basic(self, usage: QuotaUsage) -> None:
        """Basic threshold checking without enhanced features.

        Fallback used when QuotaAlertService is unavailable.

        Args:
            usage: QuotaUsage instance
        """
        percent = usage.usage_percent

        # Determine alert type
        alert_type = None
        threshold = 0

        if percent >= 100:
            alert_type = QuotaAlertType.OVERAGE
            threshold = 100
        elif percent >= CRITICAL_THRESHOLD:
            alert_type = QuotaAlertType.CRITICAL
            threshold = CRITICAL_THRESHOLD
        elif percent >= WARNING_THRESHOLD:
            alert_type = QuotaAlertType.WARNING
            threshold = WARNING_THRESHOLD

        if not alert_type:
            return

        # Check if there's already an active alert for this usage
        existing_result = await self._session.execute(
            select(QuotaAlert).where(
                and_(
                    QuotaAlert.quota_usage_id == usage.id,
                    QuotaAlert.status == QuotaAlertStatus.ACTIVE,
                    QuotaAlert.alert_type == alert_type,
                )
            )
        )
        existing = existing_result.scalars().first()

        if existing:
            # Update existing alert
            existing.current_usage = usage.current_requests
            existing.threshold_percent = int(percent)
            existing.message = self._generate_alert_message(
                alert_type, usage, percent
            )
        else:
            # Create new alert
            alert = QuotaAlert(
                quota_usage_id=usage.id,
                alert_type=alert_type,
                status=QuotaAlertStatus.ACTIVE,
                threshold_percent=int(percent),
                current_usage=usage.current_requests,
                quota_limit=usage.quota_limit,
                message=self._generate_alert_message(alert_type, usage, percent),
            )
            self._session.add(alert)
            await self._session.flush()

            # Broadcast alert
            await self._broadcast_quota_alert(alert, usage)

    def _generate_alert_message(
        self,
        alert_type: QuotaAlertType,
        usage: QuotaUsage,
        percent: float,
    ) -> str:
        """Generate an alert message.

        Args:
            alert_type: Type of alert
            usage: QuotaUsage instance
            percent: Usage percentage

        Returns:
            Alert message string
        """
        provider_name = usage.provider.name.value if usage.provider else "Unknown"

        if alert_type == QuotaAlertType.OVERAGE:
            return (
                f"Quota exceeded for {provider_name}: "
                f"{usage.current_requests}/{usage.quota_limit} requests ({percent:.1f}%)"
            )
        elif alert_type == QuotaAlertType.CRITICAL:
            return (
                f"Critical quota warning for {provider_name}: "
                f"{usage.current_requests}/{usage.quota_limit} requests ({percent:.1f}%)"
            )
        else:
            return (
                f"Quota warning for {provider_name}: "
                f"{usage.current_requests}/{usage.quota_limit} requests ({percent:.1f}%)"
            )

    async def _get_alert(self, alert_id: UUID) -> QuotaAlert | None:
        """Get an alert by ID."""
        result = await self._session.execute(
            select(QuotaAlert).where(QuotaAlert.id == alert_id)
        )
        return result.scalars().first()

    def _usage_to_response(self, usage: QuotaUsage) -> QuotaUsageResponse:
        """Convert QuotaUsage to response schema with computed fields."""
        now = datetime.datetime.now(datetime.timezone.utc)

        # Calculate time until reset
        time_until_reset = None
        if usage.period_end:
            delta = usage.period_end - now
            time_until_reset = max(0, int(delta.total_seconds()))

        # Get provider name
        provider_name = usage.provider.name.value if usage.provider else None

        return QuotaUsageResponse(
            id=usage.id,
            provider_id=usage.provider_id,
            provider_name=provider_name,
            project_id=usage.project_id,
            current_requests=usage.current_requests,
            current_tokens=usage.current_tokens,
            quota_limit=usage.quota_limit,
            quota_limit_tokens=usage.quota_limit_tokens,
            period_start=usage.period_start,
            period_end=usage.period_end,
            last_reset_at=usage.last_reset_at,
            last_request_at=usage.last_request_at,
            overage_count=usage.overage_count,
            meta_data=usage.meta_data,
            created_at=usage.created_at,
            updated_at=usage.updated_at,
            usage_percent=usage.usage_percent,
            is_over_limit=usage.is_over_limit,
            remaining_quota=usage.remaining_quota,
            remaining_requests=usage.remaining_quota,
            time_until_reset_seconds=time_until_reset,
        )

    def _alert_to_response(self, alert: QuotaAlert) -> QuotaAlertResponse:
        """Convert QuotaAlert to response schema."""
        provider_id = None
        provider_name = None

        if alert.quota_usage:
            provider_id = alert.quota_usage.provider_id
            if alert.quota_usage.provider:
                provider_name = alert.quota_usage.provider.name.value

        return QuotaAlertResponse(
            id=alert.id,
            quota_usage_id=alert.quota_usage_id,
            provider_id=provider_id,
            provider_name=provider_name,
            alert_type=alert.alert_type,
            status=alert.status,
            threshold_percent=alert.threshold_percent,
            current_usage=alert.current_usage,
            quota_limit=alert.quota_limit,
            message=alert.message,
            acknowledged_by=alert.acknowledged_by,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            meta_data=alert.meta_data,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )

    # ========== WebSocket Broadcasts ==========

    async def _broadcast_quota_update(self, usage: QuotaUsage) -> None:
        """Broadcast quota update via WebSocket.

        Args:
            usage: QuotaUsage instance
        """
        try:
            from server.websocket import manager

            now = datetime.datetime.now(datetime.timezone.utc)
            time_until_reset = None
            if usage.period_end:
                delta = usage.period_end - now
                time_until_reset = max(0, int(delta.total_seconds()))

            provider_name = (
                usage.provider.name.value if usage.provider else "unknown"
            )

            message = {
                "type": "quota_update",
                "data": {
                    "provider_id": str(usage.provider_id),
                    "provider_name": provider_name,
                    "project_id": str(usage.project_id) if usage.project_id else None,
                    "current_requests": usage.current_requests,
                    "current_tokens": usage.current_tokens,
                    "quota_limit": usage.quota_limit,
                    "usage_percent": usage.usage_percent,
                    "is_over_limit": usage.is_over_limit,
                    "remaining_requests": usage.remaining_quota,
                    "time_until_reset_seconds": time_until_reset,
                    "timestamp": now.isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast quota update: {e}")

    async def _broadcast_quota_alert(
        self,
        alert: QuotaAlert,
        usage: QuotaUsage,
    ) -> None:
        """Broadcast quota alert via WebSocket.

        Args:
            alert: QuotaAlert instance
            usage: Associated QuotaUsage instance
        """
        try:
            from server.websocket import manager

            provider_name = (
                usage.provider.name.value if usage.provider else "unknown"
            )

            message = {
                "type": "quota_alert",
                "data": {
                    "id": str(alert.id),
                    "provider_id": str(usage.provider_id),
                    "provider_name": provider_name,
                    "alert_type": alert.alert_type.value,
                    "threshold_percent": alert.threshold_percent,
                    "current_usage": alert.current_usage,
                    "quota_limit": alert.quota_limit,
                    "message": alert.message,
                    "timestamp": alert.created_at.isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast quota alert: {e}")


# ========== Dependency ==========

def get_quota_service(session: AsyncSession) -> QuotaService:
    """Get quota service instance.

    Args:
        session: Database session

    Returns:
        QuotaService instance
    """
    return QuotaService(session)
