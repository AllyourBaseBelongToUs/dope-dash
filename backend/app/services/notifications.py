"""Notification service for retention warnings and alerts.

This module provides notification functionality for retention-related events,
including warnings before data deletion and cleanup completion notifications.
"""
import logging
from datetime import datetime
from typing import Any
from enum import Enum

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class NotificationSeverity(str, Enum):
    """Severity levels for notifications."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationType(str, Enum):
    """Types of retention-related notifications."""

    EVENTS_EXPIRING_SOON = "events_expiring_soon"
    SESSIONS_EXPIRING_SOON = "sessions_expiring_soon"
    CLEANUP_COMPLETED = "cleanup_completed"
    CLEANUP_FAILED = "cleanup_failed"
    RETENTION_EXTENDED = "retention_extended"
    MANUAL_CLEANUP_TRIGGERED = "manual_cleanup_triggered"


class Notification(BaseModel):
    """Notification model."""

    id: str
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    data: dict[str, Any] | None = None
    created_at: str
    read: bool = False


class NotificationService:
    """Service for managing retention-related notifications."""

    def __init__(self):
        """Initialize notification service."""
        self._notifications: list[Notification] = []
        self._id_counter = 0

    def _generate_id(self) -> str:
        """Generate unique notification ID."""
        self._id_counter += 1
        return f"notif_{self._id_counter}_{datetime.now().timestamp()}"

    def create_notification(
        self,
        notification_type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        """Create a new notification.

        Args:
            notification_type: Type of notification
            severity: Severity level
            title: Notification title
            message: Notification message
            data: Additional data associated with the notification

        Returns:
            Created notification
        """
        notification = Notification(
            id=self._generate_id(),
            type=notification_type,
            severity=severity,
            title=title,
            message=message,
            data=data or {},
            created_at=datetime.now().isoformat(),
        )

        self._notifications.append(notification)
        logger.info(
            f"Created notification: {notification_type.value} - {title}"
        )

        return notification

    def events_expiring_soon(self, count: int, days_until_deletion: int) -> Notification:
        """Create notification for events expiring soon.

        Args:
            count: Number of events expiring
            days_until_deletion: Days until deletion

        Returns:
            Created notification
        """
        return self.create_notification(
            notification_type=NotificationType.EVENTS_EXPIRING_SOON,
            severity=NotificationSeverity.WARNING,
            title=f"{count} Events Expiring Soon",
            message=f"{count} events will be deleted in {days_until_deletion} days. "
            f"Consider extending retention if needed.",
            data={
                "count": count,
                "days_until_deletion": days_until_deletion,
            },
        )

    def sessions_expiring_soon(self, count: int, days_until_deletion: int) -> Notification:
        """Create notification for sessions expiring soon.

        Args:
            count: Number of sessions expiring
            days_until_deletion: Days until deletion

        Returns:
            Created notification
        """
        return self.create_notification(
            notification_type=NotificationType.SESSIONS_EXPIRING_SOON,
            severity=NotificationSeverity.WARNING,
            title=f"{count} Sessions Expiring Soon",
            message=f"{count} sessions will be deleted in {days_until_deletion} days. "
            f"Consider extending retention if needed.",
            data={
                "count": count,
                "days_until_deletion": days_until_deletion,
            },
        )

    def cleanup_completed(
        self,
        events_deleted: int,
        sessions_deleted: int,
        duration_seconds: float,
    ) -> Notification:
        """Create notification for completed cleanup.

        Args:
            events_deleted: Number of events deleted
            sessions_deleted: Number of sessions deleted
            duration_seconds: Duration of cleanup operation

        Returns:
            Created notification
        """
        return self.create_notification(
            notification_type=NotificationType.CLEANUP_COMPLETED,
            severity=NotificationSeverity.SUCCESS,
            title="Retention Cleanup Completed",
            message=f"Deleted {events_deleted} events and {sessions_deleted} sessions "
            f"in {duration_seconds:.2f} seconds.",
            data={
                "events_deleted": events_deleted,
                "sessions_deleted": sessions_deleted,
                "duration_seconds": duration_seconds,
            },
        )

    def cleanup_failed(self, error_message: str) -> Notification:
        """Create notification for failed cleanup.

        Args:
            error_message: Error message

        Returns:
            Created notification
        """
        return self.create_notification(
            notification_type=NotificationType.CLEANUP_FAILED,
            severity=NotificationSeverity.ERROR,
            title="Retention Cleanup Failed",
            message=f"Cleanup operation failed: {error_message}",
            data={"error": error_message},
        )

    def retention_extended(
        self,
        entity_type: str,
        entity_id: str,
        additional_days: int,
    ) -> Notification:
        """Create notification for retention extension.

        Args:
            entity_type: Type of entity (event/session)
            entity_id: ID of the entity
            additional_days: Number of days extended

        Returns:
            Created notification
        """
        return self.create_notification(
            notification_type=NotificationType.RETENTION_EXTENDED,
            severity=NotificationSeverity.INFO,
            title=f"{entity_type.capitalize()} Retention Extended",
            message=f"Extended retention for {entity_type} {entity_id} by {additional_days} days.",
            data={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "additional_days": additional_days,
            },
        )

    def manual_cleanup_triggered(self, dry_run: bool) -> Notification:
        """Create notification for manually triggered cleanup.

        Args:
            dry_run: Whether this was a dry run

        Returns:
            Created notification
        """
        mode = "Dry Run" if dry_run else "Cleanup"
        return self.create_notification(
            notification_type=NotificationType.MANUAL_CLEANUP_TRIGGERED,
            severity=NotificationSeverity.INFO,
            title=f"Manual {mode} Triggered",
            message=f"Manual {mode.lower()} has been initiated.",
            data={"dry_run": dry_run},
        )

    def get_all_notifications(self, unread_only: bool = False) -> list[Notification]:
        """Get all notifications.

        Args:
            unread_only: If True, only return unread notifications

        Returns:
            List of notifications
        """
        if unread_only:
            return [n for n in self._notifications if not n.read]
        return self._notifications

    def get_notification(self, notification_id: str) -> Notification | None:
        """Get a specific notification by ID.

        Args:
            notification_id: Notification ID

        Returns:
            Notification if found, None otherwise
        """
        for notification in self._notifications:
            if notification.id == notification_id:
                return notification
        return None

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            True if notification was found and marked as read, False otherwise
        """
        notification = self.get_notification(notification_id)
        if notification:
            notification.read = True
            return True
        return False

    def mark_all_as_read(self) -> int:
        """Mark all notifications as read.

        Returns:
            Number of notifications marked as read
        """
        count = 0
        for notification in self._notifications:
            if not notification.read:
                notification.read = True
                count += 1
        return count

    def clear_old_notifications(self, older_than_hours: int = 24) -> int:
        """Clear notifications older than specified hours.

        Args:
            older_than_hours: Age in hours for notifications to clear

        Returns:
            Number of notifications cleared
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        original_count = len(self._notifications)

        self._notifications = [
            n for n in self._notifications
            if datetime.fromisoformat(n.created_at) > cutoff
        ]

        return original_count - len(self._notifications)

    def clear_all(self) -> int:
        """Clear all notifications.

        Returns:
            Number of notifications cleared
        """
        count = len(self._notifications)
        self._notifications.clear()
        return count


# Global notification service instance
_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service instance.

    Returns:
        Notification service instance
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
        logger.info("Created new notification service instance")
    return _notification_service
