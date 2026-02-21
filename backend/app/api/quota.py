"""Quota tracking API endpoints.

Provides REST API endpoints for:
- Provider management
- Quota usage tracking
- Alert management
- Summary statistics
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.quota import (
    QuotaAlertStatus,
    ProviderResponse,
    ProviderListResponse,
    QuotaUsageResponse,
    QuotaUsageListResponse,
    QuotaAlertResponse,
    QuotaAlertListResponse,
    QuotaSummaryResponse,
)
from app.services.quota import QuotaService, get_quota_service


router = APIRouter(prefix="/quota", tags=["quota"])


# ========== Provider Endpoints ==========


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    active_only: bool = Query(False, description="Only return active providers"),
    service: QuotaService = Depends(get_quota_service),
) -> ProviderListResponse:
    """List all API providers.

    Args:
        active_only: If True, only return active providers
        service: Quota service dependency

    Returns:
        List of providers
    """
    return await service.get_providers(active_only=active_only)


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    service: QuotaService = Depends(get_quota_service),
) -> ProviderResponse:
    """Get a specific provider by ID.

    Args:
        provider_id: Provider UUID
        service: Quota service dependency

    Returns:
        Provider details

    Raises:
        HTTPException: 404 if provider not found
    """
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse.model_validate(provider)


# ========== Quota Usage Endpoints ==========


@router.get("/usage", response_model=QuotaUsageListResponse)
async def list_quota_usage(
    provider_id: UUID | None = Query(None, description="Filter by provider ID"),
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
) -> QuotaUsageListResponse:
    """List quota usage records.

    Args:
        provider_id: Optional provider filter
        project_id: Optional project filter
        db: Database session

    Returns:
        List of quota usage records
    """
    service = get_quota_service(db)
    return await service.get_quota_usage(provider_id=provider_id, project_id=project_id)


@router.post("/usage/increment")
async def increment_quota_usage(
    provider_id: UUID,
    requests: int = Query(1, description="Number of requests to add"),
    tokens: int = Query(0, description="Number of tokens to add"),
    project_id: UUID | None = Query(None, description="Project ID (null for global)"),
    db: AsyncSession = Depends(get_db),
) -> QuotaUsageResponse:
    """Increment quota usage for a provider.

    This endpoint is used to track API usage. It will:
    - Create a usage record if one doesn't exist
    - Check for quota reset before incrementing
    - Generate alerts if thresholds are exceeded
    - Broadcast updates via WebSocket

    Args:
        provider_id: Provider UUID
        requests: Number of requests to add (default 1)
        tokens: Number of tokens to add (default 0)
        project_id: Optional project UUID (null for global quota)
        db: Database session

    Returns:
        Updated quota usage record

    Raises:
        HTTPException: 404 if provider not found
    """
    service = get_quota_service(db)

    try:
        usage = await service.increment_usage(
            provider_id=provider_id,
            requests=requests,
            tokens=tokens,
            project_id=project_id,
        )
        await db.commit()

        # Convert to response
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        time_until_reset = None
        if usage.period_end:
            delta = usage.period_end - now
            time_until_reset = max(0, int(delta.total_seconds()))

        return QuotaUsageResponse(
            id=usage.id,
            provider_id=usage.provider_id,
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
            provider_name=usage.provider.name.value if usage.provider else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========== Alert Endpoints ==========


@router.get("/alerts", response_model=QuotaAlertListResponse)
async def list_alerts(
    status: QuotaAlertStatus | None = Query(None, description="Filter by status"),
    provider_id: UUID | None = Query(None, description="Filter by provider ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return"),
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertListResponse:
    """List quota alerts.

    Args:
        status: Optional status filter (active, acknowledged, resolved)
        provider_id: Optional provider filter
        limit: Maximum number of alerts to return
        db: Database session

    Returns:
        List of quota alerts
    """
    service = get_quota_service(db)
    return await service.get_alerts(
        status=status,
        provider_id=provider_id,
        limit=limit,
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=QuotaAlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    acknowledged_by: str | None = Query(None, description="User who acknowledged"),
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertResponse:
    """Acknowledge a quota alert.

    Args:
        alert_id: Alert UUID
        acknowledged_by: User who acknowledged the alert
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: 404 if alert not found
    """
    service = get_quota_service(db)
    alert = await service.acknowledge_alert(alert_id, acknowledged_by)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()

    # Get provider info for response
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


@router.post("/alerts/{alert_id}/resolve", response_model=QuotaAlertResponse)
async def resolve_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> QuotaAlertResponse:
    """Resolve a quota alert.

    Args:
        alert_id: Alert UUID
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: 404 if alert not found
    """
    service = get_quota_service(db)
    alert = await service.resolve_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()

    # Get provider info for response
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


# ========== Summary Endpoint ==========


@router.get("/summary", response_model=QuotaSummaryResponse)
async def get_quota_summary(
    db: AsyncSession = Depends(get_db),
) -> QuotaSummaryResponse:
    """Get quota summary statistics.

    Returns aggregate statistics across all providers:
    - Total providers and active providers
    - Total requests and tokens used
    - Average usage percentage
    - Alert counts (total and critical)
    - Number of providers over limit

    Args:
        db: Database session

    Returns:
        Quota summary statistics
    """
    service = get_quota_service(db)
    return await service.get_summary()
