"""Quota alerts API endpoints.

Provides REST API endpoints for:
- Alert configuration management
- Alert history with filtering
- Alert acknowledgment and resolution
- Bulk alert operations
- Alert escalation
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session as get_db
from app.models.quota import (
    QuotaAlertStatus,
    QuotaAlertType,
    AlertConfigCreate,
    AlertConfigUpdate,
    AlertConfigResponse,
    AlertConfigListResponse,
    QuotaAlertResponse,
    QuotaAlertListResponse,
)
from app.services.quota_alerts import QuotaAlertService, get_quota_alert_service


router = APIRouter(prefix="/quota/alerts", tags=["quota-alerts"])


# ========== Alert Configuration Endpoints ==========


@router.get("/config", response_model=AlertConfigListResponse)
async def list_alert_configs(
    provider_id: UUID | None = Query(None, description="Filter by provider ID"),
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    active_only: bool = Query(True, description="Only return active configs"),
    db: AsyncSession = Depends(get_db),
) -> AlertConfigListResponse:
    """List alert configurations.

    Args:
        provider_id: Optional provider filter
        project_id: Optional project filter
        active_only: If True, only return active configs
        db: Database session

    Returns:
        List of alert configurations
    """
    service = get_quota_alert_service(db)
    return await service.get_alert_configs(
        provider_id=provider_id,
        project_id=project_id,
        active_only=active_only,
    )


@router.get("/config/{config_id}", response_model=AlertConfigResponse)
async def get_alert_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AlertConfigResponse:
    """Get an alert configuration by ID.

    Args:
        config_id: Configuration UUID
        db: Database session

    Returns:
        Alert configuration

    Raises:
        HTTPException: 404 if config not found
    """
    service = get_quota_alert_service(db)
    config = await service.get_alert_config(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="Alert configuration not found")

    return service._config_to_response(config)


@router.post("/config", response_model=AlertConfigResponse, status_code=201)
async def create_alert_config(
    config_data: AlertConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> AlertConfigResponse:
    """Create a new alert configuration.

    Args:
        config_data: Configuration creation data
        db: Database session

    Returns:
        Created alert configuration
    """
    service = get_quota_alert_service(db)
    config = await service.create_alert_config(config_data)
    await db.commit()

    return service._config_to_response(config)


@router.patch("/config/{config_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    config_id: UUID,
    config_data: AlertConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> AlertConfigResponse:
    """Update an alert configuration.

    Args:
        config_id: Configuration UUID
        config_data: Update data
        db: Database session

    Returns:
        Updated alert configuration

    Raises:
        HTTPException: 404 if config not found
    """
    service = get_quota_alert_service(db)
    config = await service.update_alert_config(config_id, config_data)

    if not config:
        raise HTTPException(status_code=404, detail="Alert configuration not found")

    await db.commit()

    return service._config_to_response(config)


# ========== Alert History Endpoints ==========


@router.get("/history", response_model=QuotaAlertListResponse)
async def list_alert_history(
    status: QuotaAlertStatus | None = Query(None, description="Filter by status"),
    provider_id: UUID | None = Query(None, description="Filter by provider ID"),
    alert_type: QuotaAlertType | None = Query(None, description="Filter by alert type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertListResponse:
    """List quota alert history with filtering.

    Args:
        status: Optional status filter (active, acknowledged, resolved)
        provider_id: Optional provider filter
        alert_type: Optional alert type filter (warning, critical, overage)
        limit: Maximum number of alerts to return
        offset: Offset for pagination
        db: Database session

    Returns:
        Paginated list of quota alerts
    """
    service = get_quota_alert_service(db)
    return await service.get_alerts(
        status=status,
        provider_id=provider_id,
        alert_type=alert_type,
        limit=limit,
        offset=offset,
    )


@router.get("/active", response_model=QuotaAlertListResponse)
async def list_active_alerts(
    provider_id: UUID | None = Query(None, description="Filter by provider ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return"),
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertListResponse:
    """List active (unacknowledged) alerts.

    Convenience endpoint for getting alerts that need attention.

    Args:
        provider_id: Optional provider filter
        limit: Maximum number of alerts to return
        db: Database session

    Returns:
        List of active alerts
    """
    service = get_quota_alert_service(db)
    return await service.get_alerts(
        status=QuotaAlertStatus.ACTIVE,
        provider_id=provider_id,
        limit=limit,
    )


# ========== Alert Action Endpoints ==========


@router.post("/{alert_id}/acknowledge", response_model=QuotaAlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    acknowledged_by: str | None = Body(None, embed=True, description="User who acknowledged"),
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertResponse:
    """Acknowledge a quota alert.

    Acknowledging an alert stops escalation for that alert.

    Args:
        alert_id: Alert UUID
        acknowledged_by: User who acknowledged the alert
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: 404 if alert not found
    """
    service = get_quota_alert_service(db)
    alert = await service.acknowledge_alert(alert_id, acknowledged_by)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()

    return service._alert_to_response(alert)


@router.post("/{alert_id}/resolve", response_model=QuotaAlertResponse)
async def resolve_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertResponse:
    """Resolve a quota alert.

    Resolved alerts are removed from active monitoring.

    Args:
        alert_id: Alert UUID
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: 404 if alert not found
    """
    service = get_quota_alert_service(db)
    alert = await service.resolve_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()

    return service._alert_to_response(alert)


@router.post("/bulk/acknowledge")
async def bulk_acknowledge_alerts(
    alert_ids: list[UUID] = Body(..., description="List of alert IDs to acknowledge"),
    acknowledged_by: str | None = Body(None, description="User who acknowledged"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk acknowledge multiple alerts.

    Args:
        alert_ids: List of alert UUIDs to acknowledge
        acknowledged_by: User who acknowledged the alerts
        db: Database session

    Returns:
        Count of acknowledged alerts
    """
    service = get_quota_alert_service(db)
    count = await service.bulk_acknowledge(alert_ids, acknowledged_by)
    await db.commit()

    return {
        "acknowledged_count": count,
        "requested_count": len(alert_ids),
    }


# ========== Escalation Endpoints ==========


@router.post("/escalate/check")
async def check_escalations(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check and escalate unacknowledged alerts.

    This endpoint is typically called by a scheduler/cron job.

    Args:
        db: Database session

    Returns:
        Count of escalated alerts
    """
    service = get_quota_alert_service(db)
    escalated = await service.check_escalations()
    await db.commit()

    return {
        "escalated_count": len(escalated),
        "escalated_alert_ids": [str(a.id) for a in escalated],
    }
