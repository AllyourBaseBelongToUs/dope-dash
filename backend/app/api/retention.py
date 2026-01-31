"""Retention API endpoints for data lifecycle management.

Provides endpoints for triggering cleanup, checking retention status,
extending retention, and managing retention warnings.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session
from app.services.retention import RetentionPolicyService
from app.services.notifications import (
    get_notification_service,
    NotificationService,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retention", tags=["retention"])


@router.get("/summary")
async def get_retention_summary(
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get retention summary including counts, dates, and warnings.

    Returns:
        Dictionary with retention summary for events and sessions
    """
    try:
        service = RetentionPolicyService(db_session)
        summary = await service.get_retention_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting retention summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get retention summary: {e}")


@router.post("/cleanup")
async def trigger_cleanup(
    dry_run: bool = Query(False, description="If true, only report what would be deleted"),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Manually trigger retention cleanup.

    Args:
        dry_run: If True, only report what would be deleted without actually deleting
        db_session: Database session

    Returns:
        Dictionary with cleanup results
    """
    try:
        service = RetentionPolicyService(db_session)

        # Notify that cleanup was triggered
        notification_service = get_notification_service()
        notification_service.manual_cleanup_triggered(dry_run=dry_run)

        # Run cleanup
        result = await service.run_cleanup(dry_run=dry_run)

        # Notify completion
        if not dry_run:
            notification_service.cleanup_completed(
                events_deleted=result["events"]["deleted_count"],
                sessions_deleted=result["sessions"]["deleted_count"],
                duration_seconds=result["total_duration_seconds"],
            )

        return result
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)

        # Notify failure
        notification_service = get_notification_service()
        notification_service.cleanup_failed(str(e))

        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")


@router.post("/extend/{entity_type}/{entity_id}")
async def extend_retention(
    entity_type: str,
    entity_id: str,
    additional_days: int = Query(30, ge=1, le=365, description="Additional days of retention"),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Extend retention for a specific event or session.

    Args:
        entity_type: Either "event" or "session"
        entity_id: UUID of the entity
        additional_days: Number of days to extend retention
        db_session: Database session

    Returns:
        Dictionary with extension result
    """
    try:
        if entity_type not in ["event", "session"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity_type: {entity_type}. Must be 'event' or 'session'"
            )

        service = RetentionPolicyService(db_session)
        result = await service.extend_retention(entity_type, entity_id, additional_days)

        # Notify extension
        notification_service = get_notification_service()
        notification_service.retention_extended(entity_type, entity_id, additional_days)

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error extending retention: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extend retention: {e}")


@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False, description="If true, only return unread notifications"),
) -> dict[str, Any]:
    """Get all retention-related notifications.

    Args:
        unread_only: If True, only return unread notifications

    Returns:
        Dictionary with list of notifications
    """
    try:
        notification_service = get_notification_service()
        notifications = notification_service.get_all_notifications(unread_only=unread_only)

        return {
            "notifications": [n.model_dump() for n in notifications],
            "count": len(notifications),
        }
    except Exception as e:
        logger.error(f"Error getting notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {e}")


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
) -> dict[str, Any]:
    """Mark a notification as read.

    Args:
        notification_id: Notification ID

    Returns:
        Dictionary with success status
    """
    try:
        notification_service = get_notification_service()
        success = notification_service.mark_as_read(notification_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Notification not found: {notification_id}")

        return {"success": True, "message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {e}")


@router.post("/notifications/read-all")
async def mark_all_notifications_read() -> dict[str, Any]:
    """Mark all notifications as read.

    Returns:
        Dictionary with success status and count
    """
    try:
        notification_service = get_notification_service()
        count = notification_service.mark_all_as_read()

        return {"success": True, "marked_count": count}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark all as read: {e}")


@router.delete("/notifications")
async def clear_notifications(
    older_than_hours: int = Query(24, ge=1, description="Clear notifications older than this many hours"),
) -> dict[str, Any]:
    """Clear old notifications.

    Args:
        older_than_hours: Age in hours for notifications to clear

    Returns:
        Dictionary with success status and count
    """
    try:
        notification_service = get_notification_service()
        count = notification_service.clear_old_notifications(older_than_hours=older_than_hours)

        return {"success": True, "cleared_count": count}
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear notifications: {e}")


@router.delete("/notifications/all")
async def clear_all_notifications() -> dict[str, Any]:
    """Clear all notifications.

    Returns:
        Dictionary with success status and count
    """
    try:
        notification_service = get_notification_service()
        count = notification_service.clear_all()

        return {"success": True, "cleared_count": count}
    except Exception as e:
        logger.error(f"Error clearing all notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear all notifications: {e}")


@router.get("/stats")
async def get_retention_stats(
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get detailed retention statistics.

    Returns:
        Dictionary with detailed retention statistics
    """
    try:
        service = RetentionPolicyService(db_session)
        summary = await service.get_retention_summary()

        # Add additional stats
        notification_service = get_notification_service()
        notifications = notification_service.get_all_notifications()
        unread_notifications = notification_service.get_all_notifications(unread_only=True)

        return {
            **summary,
            "notifications": {
                "total": len(notifications),
                "unread": len(unread_notifications),
            },
            "configuration": {
                "events_retention_days": summary["events"]["retention_days"],
                "sessions_retention_days": summary["sessions"]["retention_days"],
            },
        }
    except Exception as e:
        logger.error(f"Error getting retention stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get retention stats: {e}")
