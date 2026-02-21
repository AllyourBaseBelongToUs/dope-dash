"""Auto-pause API endpoints.

Provides endpoints for:
- Getting/setting auto-pause settings per project
- Getting auto-pause status
- Manual override
- Auto-pause history
"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session
from app.models.auto_pause import (
    AutoPauseSettings,
    AutoPauseLogResponse,
    AutoPauseLogListResponse,
    AutoPauseStatusResponse,
)
from app.services.auto_pause import AutoPauseService, get_auto_pause_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auto-pause", tags=["auto-pause"])


@router.get("/projects/{project_id}/settings")
async def get_auto_pause_settings(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get auto-pause settings for a project.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Auto-pause settings for the project
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    service = get_auto_pause_service(session)

    # Get project
    from app.models.project import Project
    from sqlalchemy import select

    result = await session.execute(
        select(Project).where(Project.id == project_uuid)
    )
    project = result.scalars().first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    settings = service.get_project_settings(project)

    return {
        "project_id": str(project_uuid),
        "project_name": project.name,
        "settings": {
            "enabled": settings.enabled,
            "threshold_percent": settings.threshold_percent,
            "auto_resume": settings.auto_resume,
            "warning_threshold": settings.warning_threshold,
        },
    }


@router.patch("/projects/{project_id}/settings")
async def update_auto_pause_settings(
    project_id: str,
    settings: AutoPauseSettings,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update auto-pause settings for a project.

    Args:
        project_id: Project UUID
        settings: New settings to apply
        session: Database session

    Returns:
        Updated auto-pause settings
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    service = get_auto_pause_service(session)

    project = await service.update_project_settings(project_uuid, settings)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await session.commit()

    return {
        "project_id": str(project_uuid),
        "project_name": project.name,
        "settings": {
            "enabled": settings.enabled,
            "threshold_percent": settings.threshold_percent,
            "auto_resume": settings.auto_resume,
            "warning_threshold": settings.warning_threshold,
        },
        "message": "Auto-pause settings updated successfully",
    }


@router.get("/projects/{project_id}/status")
async def get_auto_pause_status(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AutoPauseStatusResponse:
    """Get auto-pause status for a project.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Auto-pause status including statistics
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    service = get_auto_pause_service(session)
    status = await service.get_status(project_uuid)

    if not status:
        raise HTTPException(status_code=404, detail="Project not found")

    return status


@router.post("/projects/{project_id}/override")
async def apply_manual_override(
    project_id: str,
    resume: bool = Query(True, description="Whether to resume the project"),
    override_by: str = Query("user", description="User applying the override"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Apply a manual override to an auto-paused project.

    This allows a user to resume an auto-paused project before quota resets.

    Args:
        project_id: Project UUID
        resume: Whether to resume the project
        override_by: User applying the override
        session: Database session

    Returns:
        Override result
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    service = get_auto_pause_service(session)

    log_entry = await service.apply_manual_override(
        project_id=project_uuid,
        override_by=override_by,
        resume=resume,
    )

    if not log_entry:
        raise HTTPException(
            status_code=400,
            detail="No auto-pause found for this project or override failed"
        )

    await session.commit()

    return {
        "project_id": str(project_uuid),
        "override_applied": True,
        "resumed": resume,
        "override_by": override_by,
        "override_at": log_entry.override_at.isoformat() if log_entry.override_at else None,
        "message": "Manual override applied successfully",
    }


@router.get("/projects/{project_id}/history")
async def get_auto_pause_history(
    project_id: str,
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> AutoPauseLogListResponse:
    """Get auto-pause history for a project.

    Args:
        project_id: Project UUID
        limit: Maximum number of results
        offset: Pagination offset
        session: Database session

    Returns:
        List of auto-pause log entries
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    service = get_auto_pause_service(session)
    return await service.get_pause_history(project_id=project_uuid, limit=limit, offset=offset)


@router.get("/history")
async def get_all_auto_pause_history(
    limit: int = Query(100, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> AutoPauseLogListResponse:
    """Get auto-pause history for all projects.

    Args:
        limit: Maximum number of results
        offset: Pagination offset
        session: Database session

    Returns:
        List of auto-pause log entries
    """
    service = get_auto_pause_service(session)
    return await service.get_pause_history(project_id=None, limit=limit, offset=offset)


@router.post("/check")
async def trigger_quota_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Manually trigger a quota check and auto-pause if needed.

    This endpoint allows manual triggering of the auto-pause check.
    Normally this would be called by a scheduled task.

    Args:
        session: Database session

    Returns:
        Results of the check
    """
    service = get_auto_pause_service(session)

    # Check quotas and pause if needed
    paused_logs = await service.check_quotas_and_pause()

    await session.commit()

    return {
        "checked": True,
        "projects_paused": len(paused_logs),
        "paused_projects": [
            {
                "project_id": str(log.project_id),
                "threshold_percent": log.threshold_percent,
                "trigger": log.trigger.value,
            }
            for log in paused_logs
        ],
    }


@router.post("/check-resume")
async def trigger_resume_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Manually trigger a check for auto-resume after quota reset.

    This endpoint allows manual triggering of the auto-resume check.
    Normally this would be called after quota reset detection.

    Args:
        session: Database session

    Returns:
        Results of the check
    """
    service = get_auto_pause_service(session)

    # Check for projects to resume
    resumed_logs = await service.check_and_auto_resume()

    await session.commit()

    return {
        "checked": True,
        "projects_resumed": len(resumed_logs),
        "resumed_projects": [
            {
                "project_id": str(log.project_id),
            }
            for log in resumed_logs
        ],
    }
