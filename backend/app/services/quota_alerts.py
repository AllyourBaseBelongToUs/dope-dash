"""Quota alert service for multi-channel alerting and escalation.

This service provides:
- Multi-channel alert dispatch (dashboard, desktop, audio)
- Alert threshold monitoring (80%, 90%, 95%)
- Alert cooldown management (prevent spam)
- Alert escalation for unacknowledged alerts
- Per-provider alert configuration
"""
from __future__ import annotations

import datetime
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quota import (
    AlertChannel,
    AlertConfig,
    AlertConfigCreate,
    AlertConfigUpdate,
    AlertConfigResponse,
    AlertConfigListResponse,
    QuotaAlert,
    QuotaAlertResponse,
    QuotaAlertListResponse,
    QuotaAlertType,
    QuotaAlertStatus,
    QuotaUsage,
    Provider,
)


logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_WARNING_THRESHOLD = 80
DEFAULT_CRITICAL_THRESHOLD = 90
DEFAULT_EMERGENCY_THRESHOLD = 95

# Default cooldown in minutes
DEFAULT_COOLDOWN_MINUTES = 30

# Default escalation settings
DEFAULT_ESCALATION_MINUTES = 15
DEFAULT_MAX_ESCALATIONS = 3


class QuotaAlertService:
    """Service for managing quota alerts with multi-channel support.

    Provides:
    - Alert configuration CRUD operations
    - Multi-channel alert dispatch
    - Cooldown enforcement
    - Alert escalation
    - WebSocket broadcasts for real-time alerts
    """

    def __init__(self, session: AsyncSession):
        """Initialize the quota alert service.

        Args:
            session: Database session for queries
        """
        self._session = session

    # ========== Alert Configuration Operations ==========

    async def get_alert_configs(
        self,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
        active_only: bool = True,
    ) -> AlertConfigListResponse:
        """Get alert configurations.

        Args:
            provider_id: Optional provider filter
            project_id: Optional project filter
            active_only: If True, only return active configs

        Returns:
            List of alert configurations
        """
        query = select(AlertConfig)

        if provider_id is not None:
            query = query.where(AlertConfig.provider_id == provider_id)
        if project_id is not None:
            query = query.where(AlertConfig.project_id == project_id)
        if active_only:
            query = query.where(AlertConfig.is_active == True)

        result = await self._session.execute(query)
        configs = list(result.scalars().all())

        return AlertConfigListResponse(
            items=[self._config_to_response(c) for c in configs],
            total=len(configs),
        )

    async def get_alert_config(
        self,
        config_id: UUID,
    ) -> AlertConfig | None:
        """Get an alert configuration by ID.

        Args:
            config_id: Configuration UUID

        Returns:
            AlertConfig instance or None
        """
        result = await self._session.execute(
            select(AlertConfig).where(AlertConfig.id == config_id)
        )
        return result.scalars().first()

    async def get_or_create_alert_config(
        self,
        provider_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> AlertConfig:
        """Get or create alert configuration for a provider/project.

        Falls back to global config if no specific config exists.

        Args:
            provider_id: Provider UUID (optional)
            project_id: Project UUID (optional)

        Returns:
            AlertConfig instance
        """
        # Try to get specific config
        if provider_id or project_id:
            query = select(AlertConfig).where(
                and_(
                    AlertConfig.provider_id == provider_id,
                    AlertConfig.project_id == project_id,
                    AlertConfig.is_active == True,
                )
            )
            result = await self._session.execute(query)
            config = result.scalars().first()
            if config:
                return config

        # Fall back to global config
        query = select(AlertConfig).where(
            and_(
                AlertConfig.provider_id == None,
                AlertConfig.project_id == None,
                AlertConfig.is_active == True,
            )
        )
        result = await self._session.execute(query)
        config = result.scalars().first()

        if config:
            return config

        # Create default global config
        config = AlertConfig(
            provider_id=None,
            project_id=None,
            warning_threshold=DEFAULT_WARNING_THRESHOLD,
            critical_threshold=DEFAULT_CRITICAL_THRESHOLD,
            emergency_threshold=DEFAULT_EMERGENCY_THRESHOLD,
            channels=[AlertChannel.DASHBOARD.value, AlertChannel.DESKTOP.value, AlertChannel.AUDIO.value],
            dashboard_enabled=True,
            desktop_enabled=True,
            audio_enabled=True,
            cooldown_minutes=DEFAULT_COOLDOWN_MINUTES,
            escalation_enabled=True,
            escalation_minutes=DEFAULT_ESCALATION_MINUTES,
            max_escalations=DEFAULT_MAX_ESCALATIONS,
            is_active=True,
        )
        self._session.add(config)
        await self._session.flush()

        return config

    async def create_alert_config(
        self,
        config_data: AlertConfigCreate,
    ) -> AlertConfig:
        """Create a new alert configuration.

        Args:
            config_data: Configuration creation data

        Returns:
            Created AlertConfig instance
        """
        config = AlertConfig(
            provider_id=config_data.provider_id,
            project_id=config_data.project_id,
            warning_threshold=config_data.warning_threshold,
            critical_threshold=config_data.critical_threshold,
            emergency_threshold=config_data.emergency_threshold,
            channels=config_data.channels,
            dashboard_enabled=config_data.dashboard_enabled,
            desktop_enabled=config_data.desktop_enabled,
            audio_enabled=config_data.audio_enabled,
            cooldown_minutes=config_data.cooldown_minutes,
            escalation_enabled=config_data.escalation_enabled,
            escalation_minutes=config_data.escalation_minutes,
            max_escalations=config_data.max_escalations,
            is_active=config_data.is_active,
            meta_data=config_data.metadata,
        )
        self._session.add(config)
        await self._session.flush()

        logger.info(
            f"Created alert config {config.id} for "
            f"provider={config.provider_id}, project={config.project_id}"
        )

        return config

    async def update_alert_config(
        self,
        config_id: UUID,
        config_data: AlertConfigUpdate,
    ) -> AlertConfig | None:
        """Update an alert configuration.

        Args:
            config_id: Configuration UUID
            config_data: Update data

        Returns:
            Updated AlertConfig or None
        """
        config = await self.get_alert_config(config_id)
        if not config:
            return None

        update_data = config_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "metadata":
                setattr(config, "meta_data", value)
            else:
                setattr(config, field, value)

        await self._session.flush()

        logger.info(f"Updated alert config {config_id}")

        return config

    # ========== Alert Operations ==========

    async def get_alerts(
        self,
        status: QuotaAlertStatus | None = None,
        provider_id: UUID | None = None,
        alert_type: QuotaAlertType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> QuotaAlertListResponse:
        """Get quota alerts.

        Args:
            status: Optional status filter
            provider_id: Optional provider filter
            alert_type: Optional alert type filter
            limit: Maximum number of alerts to return
            offset: Offset for pagination

        Returns:
            List of quota alerts
        """
        query = (
            select(QuotaAlert)
            .options(
                selectinload(QuotaAlert.quota_usage).selectinload(QuotaUsage.provider)
            )
            .order_by(QuotaAlert.created_at.desc())
        )

        if status:
            query = query.where(QuotaAlert.status == status)
        if alert_type:
            query = query.where(QuotaAlert.alert_type == alert_type)
        if provider_id:
            query = query.join(QuotaUsage).where(
                QuotaUsage.provider_id == provider_id
            )

        # Get total count
        count_query = select(QuotaAlert)
        if status:
            count_query = count_query.where(QuotaAlert.status == status)
        if alert_type:
            count_query = count_query.where(QuotaAlert.alert_type == alert_type)
        if provider_id:
            count_query = count_query.join(QuotaUsage).where(
                QuotaUsage.provider_id == provider_id
            )

        count_result = await self._session.execute(count_query)
        total = len(list(count_result.scalars().all()))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        alerts = list(result.scalars().all())

        return QuotaAlertListResponse(
            items=[self._alert_to_response(a) for a in alerts],
            total=total,
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

            # Broadcast acknowledgment
            await self._broadcast_alert_acknowledged(alert)

            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")

        return alert

    async def resolve_alert(
        self,
        alert_id: UUID,
    ) -> QuotaAlert | None:
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

    async def bulk_acknowledge(
        self,
        alert_ids: list[UUID],
        acknowledged_by: str | None = None,
    ) -> int:
        """Bulk acknowledge multiple alerts.

        Args:
            alert_ids: List of alert UUIDs
            acknowledged_by: User who acknowledged

        Returns:
            Number of alerts acknowledged
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        result = await self._session.execute(
            update(QuotaAlert)
            .where(QuotaAlert.id.in_(alert_ids))
            .where(QuotaAlert.status == QuotaAlertStatus.ACTIVE)
            .values(
                status=QuotaAlertStatus.ACKNOWLEDGED,
                acknowledged_by=acknowledged_by,
                acknowledged_at=now,
            )
        )

        count = result.rowcount
        await self._session.flush()

        logger.info(f"Bulk acknowledged {count} alerts")

        return count

    # ========== Alert Dispatch and Escalation ==========

    async def check_and_send_alert(
        self,
        usage: QuotaUsage,
    ) -> QuotaAlert | None:
        """Check usage thresholds and send alert if needed.

        Args:
            usage: QuotaUsage instance

        Returns:
            Created or updated alert, or None if no alert needed
        """
        # Get alert config
        config = await self.get_or_create_alert_config(
            provider_id=usage.provider_id,
            project_id=usage.project_id,
        )

        percent = usage.usage_percent

        # Determine alert type and threshold
        alert_type = None
        threshold = 0

        if percent >= 100:
            alert_type = QuotaAlertType.OVERAGE
            threshold = 100
        elif percent >= config.emergency_threshold:
            alert_type = QuotaAlertType.OVERAGE
            threshold = config.emergency_threshold
        elif percent >= config.critical_threshold:
            alert_type = QuotaAlertType.CRITICAL
            threshold = config.critical_threshold
        elif percent >= config.warning_threshold:
            alert_type = QuotaAlertType.WARNING
            threshold = config.warning_threshold

        if not alert_type:
            return None

        # Check cooldown
        if not await self._check_cooldown(usage, config):
            logger.debug(
                f"Alert on cooldown for usage {usage.id}, "
                f"threshold {threshold}%"
            )
            return None

        # Check for existing active alert
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
            await self._session.flush()
            return existing

        # Create new alert
        alert = QuotaAlert(
            quota_usage_id=usage.id,
            alert_type=alert_type,
            status=QuotaAlertStatus.ACTIVE,
            threshold_percent=int(percent),
            current_usage=usage.current_requests,
            quota_limit=usage.quota_limit,
            message=self._generate_alert_message(alert_type, usage, percent),
            alert_channels=[],
            escalation_count=0,
        )
        self._session.add(alert)
        await self._session.flush()

        # Update last_alert_at on usage
        usage.last_alert_at = datetime.datetime.now(datetime.timezone.utc)

        # Dispatch to channels
        await self._dispatch_alert(alert, usage, config)

        logger.info(
            f"Created {alert_type.value} alert {alert.id} for "
            f"provider {usage.provider_id}: {percent:.1f}% usage"
        )

        return alert

    async def check_escalations(self) -> list[QuotaAlert]:
        """Check for alerts that need escalation.

        Escalates alerts that have been active longer than the
        escalation period without acknowledgment.

        Returns:
            List of escalated alerts
        """
        # Get global config for escalation settings
        config = await self.get_or_create_alert_config()

        if not config.escalation_enabled:
            return []

        now = datetime.datetime.now(datetime.timezone.utc)
        escalation_threshold = now - datetime.timedelta(
            minutes=config.escalation_minutes
        )

        # Find alerts that need escalation
        result = await self._session.execute(
            select(QuotaAlert)
            .options(
                selectinload(QuotaAlert.quota_usage).selectinload(QuotaUsage.provider)
            )
            .where(
                and_(
                    QuotaAlert.status == QuotaAlertStatus.ACTIVE,
                    QuotaAlert.escalation_count < config.max_escalations,
                    QuotaAlert.created_at < escalation_threshold,
                    (
                        QuotaAlert.escalation_at == None
                        | (
                            QuotaAlert.escalation_at < escalation_threshold
                        )
                    ),
                )
            )
        )

        alerts_to_escalate = list(result.scalars().all())
        escalated = []

        for alert in alerts_to_escalate:
            alert.escalate()
            escalated.append(alert)

            # Re-dispatch alert with higher priority
            usage = alert.quota_usage
            await self._dispatch_alert(alert, usage, config, is_escalation=True)

            logger.info(
                f"Escalated alert {alert.id} "
                f"(escalation #{alert.escalation_count})"
            )

        if escalated:
            await self._session.flush()

        return escalated

    # ========== Private Helpers ==========

    async def _check_cooldown(
        self,
        usage: QuotaUsage,
        config: AlertConfig,
    ) -> bool:
        """Check if cooldown period has elapsed.

        Args:
            usage: QuotaUsage instance
            config: AlertConfig instance

        Returns:
            True if alert can be sent, False if on cooldown
        """
        if not usage.last_alert_at:
            return True

        now = datetime.datetime.now(datetime.timezone.utc)
        cooldown_end = usage.last_alert_at + datetime.timedelta(
            minutes=config.cooldown_minutes
        )

        return now >= cooldown_end

    async def _dispatch_alert(
        self,
        alert: QuotaAlert,
        usage: QuotaUsage,
        config: AlertConfig,
        is_escalation: bool = False,
    ) -> None:
        """Dispatch alert to configured channels.

        Args:
            alert: QuotaAlert instance
            usage: QuotaUsage instance
            config: AlertConfig instance
            is_escalation: Whether this is an escalation
        """
        provider_name = (
            usage.provider.name.value if usage.provider else "unknown"
        )

        channels_sent = []

        # Always send to dashboard
        if config.dashboard_enabled:
            await self._broadcast_quota_alert(alert, usage, is_escalation)
            channels_sent.append(AlertChannel.DASHBOARD.value)

        # Send desktop notification
        if config.desktop_enabled:
            await self._broadcast_desktop_alert(alert, usage, is_escalation)
            channels_sent.append(AlertChannel.DESKTOP.value)

        # Send audio alert for emergency threshold (95%+)
        if (
            config.audio_enabled
            and alert.threshold_percent >= config.emergency_threshold
        ):
            await self._broadcast_audio_alert(alert, usage)
            channels_sent.append(AlertChannel.AUDIO.value)

        # Update alert channels
        for channel in channels_sent:
            alert.add_channel(channel)

        await self._session.flush()

    async def _broadcast_quota_alert(
        self,
        alert: QuotaAlert,
        usage: QuotaUsage,
        is_escalation: bool = False,
    ) -> None:
        """Broadcast quota alert via WebSocket.

        Args:
            alert: QuotaAlert instance
            usage: QuotaUsage instance
            is_escalation: Whether this is an escalation
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
                    "is_escalation": is_escalation,
                    "escalation_count": alert.escalation_count,
                    "timestamp": alert.created_at.isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast quota alert: {e}")

    async def _broadcast_desktop_alert(
        self,
        alert: QuotaAlert,
        usage: QuotaUsage,
        is_escalation: bool = False,
    ) -> None:
        """Broadcast desktop notification trigger via WebSocket.

        Args:
            alert: QuotaAlert instance
            usage: QuotaUsage instance
            is_escalation: Whether this is an escalation
        """
        try:
            from server.websocket import manager

            provider_name = (
                usage.provider.name.value if usage.provider else "unknown"
            )

            title = "Quota Alert"
            if is_escalation:
                title = f"[ESCALATION #{alert.escalation_count}] Quota Alert"

            message = {
                "type": "desktop_notification",
                "data": {
                    "title": title,
                    "body": alert.message,
                    "tag": f"quota-{str(usage.provider_id)}",
                    "requireInteraction": True,
                    "alert_id": str(alert.id),
                    "provider_name": provider_name,
                    "threshold_percent": alert.threshold_percent,
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast desktop alert: {e}")

    async def _broadcast_audio_alert(
        self,
        alert: QuotaAlert,
        usage: QuotaUsage,
    ) -> None:
        """Broadcast audio alert trigger via WebSocket.

        Args:
            alert: QuotaAlert instance
            usage: QuotaUsage instance
        """
        try:
            from server.websocket import manager

            message = {
                "type": "audio_alert",
                "data": {
                    "alert_id": str(alert.id),
                    "sound_type": "emergency",  # 95%+ threshold
                    "provider_id": str(usage.provider_id),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast audio alert: {e}")

    async def _broadcast_alert_acknowledged(
        self,
        alert: QuotaAlert,
    ) -> None:
        """Broadcast alert acknowledgment via WebSocket.

        Args:
            alert: QuotaAlert instance
        """
        try:
            from server.websocket import manager

            message = {
                "type": "alert_acknowledged",
                "data": {
                    "alert_id": str(alert.id),
                    "acknowledged_by": alert.acknowledged_by,
                    "acknowledged_at": (
                        alert.acknowledged_at.isoformat()
                        if alert.acknowledged_at
                        else None
                    ),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast alert acknowledgment: {e}")

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
            if percent >= 100:
                return (
                    f"Quota exceeded for {provider_name}: "
                    f"{usage.current_requests}/{usage.quota_limit} requests ({percent:.1f}%)"
                )
            return (
                f"Emergency quota warning for {provider_name}: "
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
            select(QuotaAlert)
            .options(selectinload(QuotaAlert.quota_usage))
            .where(QuotaAlert.id == alert_id)
        )
        return result.scalars().first()

    def _config_to_response(self, config: AlertConfig) -> AlertConfigResponse:
        """Convert AlertConfig to response schema."""
        return AlertConfigResponse(
            id=config.id,
            provider_id=config.provider_id,
            project_id=config.project_id,
            warning_threshold=config.warning_threshold,
            critical_threshold=config.critical_threshold,
            emergency_threshold=config.emergency_threshold,
            channels=config.channels,
            dashboard_enabled=config.dashboard_enabled,
            desktop_enabled=config.desktop_enabled,
            audio_enabled=config.audio_enabled,
            cooldown_minutes=config.cooldown_minutes,
            escalation_enabled=config.escalation_enabled,
            escalation_minutes=config.escalation_minutes,
            max_escalations=config.max_escalations,
            is_active=config.is_active,
            meta_data=config.meta_data,
            created_at=config.created_at,
            updated_at=config.updated_at,
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
            alert_channels=alert.alert_channels or [],
            escalation_count=alert.escalation_count or 0,
            escalation_at=alert.escalation_at,
        )


# ========== Dependency ==========

def get_quota_alert_service(session: AsyncSession) -> QuotaAlertService:
    """Get quota alert service instance.

    Args:
        session: Database session

    Returns:
        QuotaAlertService instance
    """
    return QuotaAlertService(session)
