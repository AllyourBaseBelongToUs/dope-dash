"""Retention policy service for automated data cleanup.

This module provides data retention management for events and sessions,
including automated cleanup jobs, deletion logging, and retention warnings.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.event import Event
from app.models.session import Session
from app.models.deletion_log import DeletionLog, DeletionType, EntityType


logger = logging.getLogger(__name__)


class RetentionPolicyService:
    """Service for managing data retention policies and cleanup operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize retention service.

        Args:
            db_session: Database session for operations
        """
        self.db_session = db_session

    async def get_retention_summary(self) -> dict[str, Any]:
        """Get summary of data retention status.

        Returns:
            Dictionary with retention summary including counts, dates, and warnings
        """
        # Get retention thresholds
        events_cutoff = datetime.now() - timedelta(days=settings.events_retention_days)
        sessions_cutoff = datetime.now() - timedelta(days=settings.sessions_retention_days)

        # Count events that will be deleted
        events_to_delete_query = select(func.count()).where(
            Event.created_at < events_cutoff
        )
        events_to_delete_result = await self.db_session.execute(events_to_delete_query)
        events_to_delete = events_to_delete_result.scalar() or 0

        # Count total events
        total_events_query = select(func.count())
        total_events_result = await self.db_session.execute(total_events_query)
        total_events = total_events_result.scalar() or 0

        # Count sessions that will be deleted
        sessions_to_delete_query = select(func.count()).where(
            Session.created_at < sessions_cutoff
        )
        sessions_to_delete_result = await self.db_session.execute(sessions_to_delete_query)
        sessions_to_delete = sessions_to_delete_result.scalar() or 0

        # Count total sessions
        total_sessions_query = select(func.count()).select_from(Session)
        total_sessions_result = await self.db_session.execute(total_sessions_query)
        total_sessions = total_sessions_result.scalar() or 0

        # Calculate retention periods
        events_retention_days = settings.events_retention_days
        sessions_retention_days = settings.sessions_retention_days

        # Get oldest event date
        oldest_event_query = select(func.min(Event.created_at))
        oldest_event_result = await self.db_session.execute(oldest_event_query)
        oldest_event = oldest_event_result.scalar()

        # Get oldest session date
        oldest_session_query = select(func.min(Session.created_at))
        oldest_session_result = await self.db_session.execute(oldest_session_query)
        oldest_session = oldest_session_result.scalar()

        # Generate warnings if approaching retention limit
        warnings = []
        if events_to_delete > 0:
            warnings.append({
                "type": "events_cleanup",
                "message": f"{events_to_delete} events will be deleted on next cleanup",
                "severity": "info",
                "count": events_to_delete,
            })
        if sessions_to_delete > 0:
            warnings.append({
                "type": "sessions_cleanup",
                "message": f"{sessions_to_delete} sessions will be deleted on next cleanup",
                "severity": "info",
                "count": sessions_to_delete,
            })

        # Check for upcoming expirations (within 7 days)
        events_warning_cutoff = datetime.now() - timedelta(days=settings.events_retention_days - 7)
        upcoming_events_expiration_query = select(func.count()).where(
            Event.created_at < events_warning_cutoff,
            Event.created_at >= events_cutoff
        )
        upcoming_events_result = await self.db_session.execute(upcoming_events_expiration_query)
        upcoming_events_expiration = upcoming_events_result.scalar() or 0

        sessions_warning_cutoff = datetime.now() - timedelta(days=settings.sessions_retention_days - 7)
        upcoming_sessions_expiration_query = select(func.count()).where(
            Session.created_at < sessions_warning_cutoff,
            Session.created_at >= sessions_cutoff
        )
        upcoming_sessions_result = await self.db_session.execute(upcoming_sessions_expiration_query)
        upcoming_sessions_expiration = upcoming_sessions_result.scalar() or 0

        if upcoming_events_expiration > 0:
            warnings.append({
                "type": "events_expiring_soon",
                "message": f"{upcoming_events_expiration} events will expire within 7 days",
                "severity": "warning",
                "count": upcoming_events_expiration,
            })
        if upcoming_sessions_expiration > 0:
            warnings.append({
                "type": "sessions_expiring_soon",
                "message": f"{upcoming_sessions_expiration} sessions will expire within 7 days",
                "severity": "warning",
                "count": upcoming_sessions_expiration,
            })

        return {
            "events": {
                "total": total_events,
                "to_delete": events_to_delete,
                "upcoming_expiration": upcoming_events_expiration,
                "retention_days": events_retention_days,
                "cutoff_date": events_cutoff.isoformat(),
                "oldest_date": oldest_event.isoformat() if oldest_event else None,
            },
            "sessions": {
                "total": total_sessions,
                "to_delete": sessions_to_delete,
                "upcoming_expiration": upcoming_sessions_expiration,
                "retention_days": sessions_retention_days,
                "cutoff_date": sessions_cutoff.isoformat(),
                "oldest_date": oldest_session.isoformat() if oldest_session else None,
            },
            "warnings": warnings,
            "generated_at": datetime.now().isoformat(),
        }

    async def cleanup_events(self, dry_run: bool = False) -> dict[str, Any]:
        """Clean up events older than retention period.

        This performs a two-stage deletion:
        1. First, soft delete (mark with deleted_at) if not already marked
        2. Then, permanently delete soft-deleted events

        Args:
            dry_run: If True, only report what would be deleted without actually deleting

        Returns:
            Dictionary with cleanup results including deleted count and duration
        """
        start_time = datetime.now()
        events_cutoff = datetime.now() - timedelta(days=settings.events_retention_days)

        # Count events to soft delete (old events not yet soft deleted)
        soft_delete_count_query = select(func.count()).where(
            Event.created_at < events_cutoff,
            Event.deleted_at.is_(None)
        )
        soft_delete_count_result = await self.db_session.execute(soft_delete_count_query)
        soft_delete_count = soft_delete_count_result.scalar() or 0

        # Count soft-deleted events to permanently delete
        # (permanently delete events that were soft deleted more than 7 days ago)
        permanent_delete_cutoff = datetime.now() - timedelta(days=settings.events_retention_days + 7)
        permanent_delete_count_query = select(func.count()).where(
            Event.deleted_at.isnot(None),
            Event.deleted_at < permanent_delete_cutoff
        )
        permanent_delete_count_result = await self.db_session.execute(permanent_delete_count_query)
        permanent_delete_count = permanent_delete_count_result.scalar() or 0

        soft_deleted = 0
        permanently_deleted = 0

        if not dry_run:
            # Soft delete old events
            if soft_delete_count > 0:
                soft_delete_query = update(Event).where(
                    Event.created_at < events_cutoff,
                    Event.deleted_at.is_(None)
                ).values(deleted_at=datetime.now())
                soft_delete_result = await self.db_session.execute(soft_delete_query)
                soft_deleted = soft_delete_result.rowcount
                logger.info(f"Soft deleted {soft_deleted} events older than {events_cutoff.isoformat()}")

            # Permanently delete soft-deleted events
            if permanent_delete_count > 0:
                # Get events to delete for logging
                events_to_delete_query = select(Event).where(
                    Event.deleted_at.isnot(None),
                    Event.deleted_at < permanent_delete_cutoff
                )
                events_to_delete_result = await self.db_session.execute(events_to_delete_query)
                events_to_delete = events_to_delete_result.scalars().all()

                # Log deletions
                for event in events_to_delete:
                    await self._log_deletion(
                        entity_type="event",
                        entity_id=event.id,
                        deletion_type=DeletionType.RETENTION.value,
                        deleted_by="scheduler",
                        metadata={
                            "event_type": event.event_type,
                            "created_at": event.created_at.isoformat() if event.created_at else None,
                            "soft_deleted_at": event.deleted_at.isoformat() if event.deleted_at else None,
                        },
                        session_id=event.session_id,
                    )

                # Now delete
                permanent_delete_query = delete(Event).where(
                    Event.deleted_at.isnot(None),
                    Event.deleted_at < permanent_delete_cutoff
                )
                permanent_delete_result = await self.db_session.execute(permanent_delete_query)
                permanently_deleted = permanent_delete_result.rowcount
                logger.info(f"Permanently deleted {permanently_deleted} soft-deleted events")

            await self.db_session.commit()

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "type": "events",
            "soft_deleted_count": soft_delete_count if dry_run else soft_deleted,
            "permanently_deleted_count": permanent_delete_count if dry_run else permanently_deleted,
            "total_deleted_count": (soft_delete_count + permanent_delete_count) if dry_run else (soft_deleted + permanently_deleted),
            "dry_run": dry_run,
            "retention_days": settings.events_retention_days,
            "grace_period_days": 7,
            "cutoff_date": events_cutoff.isoformat(),
            "permanent_delete_cutoff_date": permanent_delete_cutoff.isoformat(),
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
        }

    async def cleanup_sessions(self, dry_run: bool = False) -> dict[str, Any]:
        """Clean up sessions older than retention period.

        This performs a two-stage deletion:
        1. First, soft delete (mark with deleted_at) if not already marked
        2. Then, permanently delete soft-deleted sessions

        Note: Session deletion cascades to events, spec_runs, and metric_buckets.

        Args:
            dry_run: If True, only report what would be deleted without actually deleting

        Returns:
            Dictionary with cleanup results including deleted count and duration
        """
        start_time = datetime.now()
        sessions_cutoff = datetime.now() - timedelta(days=settings.sessions_retention_days)

        # Count sessions to soft delete (old sessions not yet soft deleted)
        soft_delete_count_query = select(func.count()).where(
            Session.created_at < sessions_cutoff,
            Session.deleted_at.is_(None)
        )
        soft_delete_count_result = await self.db_session.execute(soft_delete_count_query)
        soft_delete_count = soft_delete_count_result.scalar() or 0

        # Count soft-deleted sessions to permanently delete
        # (permanently delete sessions that were soft deleted more than 30 days ago)
        permanent_delete_cutoff = datetime.now() - timedelta(days=settings.sessions_retention_days + 30)
        permanent_delete_count_query = select(func.count()).where(
            Session.deleted_at.isnot(None),
            Session.deleted_at < permanent_delete_cutoff
        )
        permanent_delete_count_result = await self.db_session.execute(permanent_delete_count_query)
        permanent_delete_count = permanent_delete_count_result.scalar() or 0

        # Also count cascading events that will be deleted
        events_count_query = select(func.count()).select_from(Event).join(
            Session, Event.session_id == Session.id
        ).where(Session.deleted_at.isnot(None), Session.deleted_at < permanent_delete_cutoff)
        events_count_result = await self.db_session.execute(events_count_query)
        events_count = events_count_result.scalar() or 0

        soft_deleted = 0
        permanently_deleted = 0

        if not dry_run:
            # Soft delete old sessions
            if soft_delete_count > 0:
                soft_delete_query = update(Session).where(
                    Session.created_at < sessions_cutoff,
                    Session.deleted_at.is_(None)
                ).values(deleted_at=datetime.now())
                soft_delete_result = await self.db_session.execute(soft_delete_query)
                soft_deleted = soft_delete_result.rowcount
                logger.info(f"Soft deleted {soft_deleted} sessions older than {sessions_cutoff.isoformat()}")

            # Permanently delete soft-deleted sessions
            if permanent_delete_count > 0:
                # Get sessions to delete for logging
                sessions_to_delete_query = select(Session).where(
                    Session.deleted_at.isnot(None),
                    Session.deleted_at < permanent_delete_cutoff
                )
                sessions_to_delete_result = await self.db_session.execute(sessions_to_delete_query)
                sessions_to_delete = sessions_to_delete_result.scalars().all()

                # Log deletions
                for session in sessions_to_delete:
                    await self._log_deletion(
                        entity_type="session",
                        entity_id=session.id,
                        deletion_type=DeletionType.RETENTION.value,
                        deleted_by="scheduler",
                        metadata={
                            "agent_type": session.agent_type.value if session.agent_type else None,
                            "project_name": session.project_name,
                            "status": session.status.value if session.status else None,
                            "created_at": session.created_at.isoformat() if session.created_at else None,
                            "soft_deleted_at": session.deleted_at.isoformat() if session.deleted_at else None,
                        },
                        session_id=session.id,
                        project_name=session.project_name,
                    )

                # Now delete
                permanent_delete_query = delete(Session).where(
                    Session.deleted_at.isnot(None),
                    Session.deleted_at < permanent_delete_cutoff
                )
                permanent_delete_result = await self.db_session.execute(permanent_delete_query)
                permanently_deleted = permanent_delete_result.rowcount
                logger.info(f"Permanently deleted {permanently_deleted} soft-deleted sessions")

            await self.db_session.commit()

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "type": "sessions",
            "soft_deleted_count": soft_delete_count if dry_run else soft_deleted,
            "permanently_deleted_count": permanent_delete_count if dry_run else permanently_deleted,
            "cascaded_events": events_count,
            "total_deleted_count": (soft_delete_count + permanent_delete_count) if dry_run else (soft_deleted + permanently_deleted),
            "dry_run": dry_run,
            "retention_days": settings.sessions_retention_days,
            "grace_period_days": 30,
            "cutoff_date": sessions_cutoff.isoformat(),
            "permanent_delete_cutoff_date": permanent_delete_cutoff.isoformat(),
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
        }

    async def run_cleanup(self, dry_run: bool = False) -> dict[str, Any]:
        """Run full cleanup for both events and sessions.

        Args:
            dry_run: If True, only report what would be deleted without actually deleting

        Returns:
            Dictionary with combined cleanup results
        """
        start_time = datetime.now()

        logger.info(
            f"Starting retention cleanup (dry_run={dry_run}): "
            f"events={settings.events_retention_days} days, "
            f"sessions={settings.sessions_retention_days} days"
        )

        # Clean up events first (since they cascade from sessions)
        events_result = await self.cleanup_events(dry_run=dry_run)

        # Then clean up sessions
        sessions_result = await self.cleanup_sessions(dry_run=dry_run)

        total_duration = (datetime.now() - start_time).total_seconds()

        result = {
            "dry_run": dry_run,
            "events": events_result,
            "sessions": sessions_result,
            "total_deleted": events_result["total_deleted_count"] + sessions_result["total_deleted_count"],
            "total_duration_seconds": total_duration,
            "completed_at": datetime.now().isoformat(),
        }

        if not dry_run:
            logger.info(
                f"Retention cleanup completed: "
                f"{events_result['total_deleted_count']} events, "
                f"{sessions_result['total_deleted_count']} sessions deleted "
                f"in {total_duration:.2f}s"
            )

        return result

    async def extend_retention(
        self,
        entity_type: str,
        entity_id: str,
        additional_days: int,
    ) -> dict[str, Any]:
        """Extend retention for a specific entity by clearing soft delete.

        This allows manual retention extension for important data by
        clearing the deleted_at timestamp if the entity was soft deleted.

        Args:
            entity_type: Either "event" or "session"
            entity_id: UUID of the entity
            additional_days: Number of days to extend retention (for logging purposes)

        Returns:
            Dictionary with extension result

        Raises:
            ValueError: If entity_type is invalid or entity not found
        """
        try:
            entity_uuid = uuid.UUID(entity_id)
        except ValueError:
            raise ValueError(f"Invalid {entity_type}_id format: {entity_id}")

        if entity_type == "event":
            query = select(Event).where(Event.id == entity_uuid)
            result = await self.db_session.execute(query)
            entity = result.scalar_one_or_none()

            if not entity:
                raise ValueError(f"Event not found: {entity_id}")

            was_deleted = entity.deleted_at is not None

            # Clear soft delete to extend retention
            entity.deleted_at = None
            await self.db_session.commit()

            return {
                "type": "event",
                "id": entity_id,
                "was_deleted": was_deleted,
                "restored": True,
                "message": f"Event retention extended by {additional_days} days (soft delete cleared)",
                "additional_days": additional_days,
            }

        elif entity_type == "session":
            query = select(Session).where(Session.id == entity_uuid)
            result = await self.db_session.execute(query)
            entity = result.scalar_one_or_none()

            if not entity:
                raise ValueError(f"Session not found: {entity_id}")

            was_deleted = entity.deleted_at is not None

            # Clear soft delete to extend retention
            entity.deleted_at = None
            await self.db_session.commit()

            return {
                "type": "session",
                "id": entity_id,
                "was_deleted": was_deleted,
                "restored": True,
                "message": f"Session retention extended by {additional_days} days (soft delete cleared)",
                "additional_days": additional_days,
            }

        else:
            raise ValueError(f"Invalid entity_type: {entity_type}. Must be 'event' or 'session'")

    async def get_deletion_log(self, limit: int = 100, entity_type: str | None = None) -> list[dict[str, Any]]:
        """Get log of recent deletion activity.

        Args:
            limit: Maximum number of log entries to return
            entity_type: Filter by entity type (event, session, etc.)

        Returns:
            List of deletion log entries
        """
        query = select(DeletionLog).order_by(DeletionLog.created_at.desc()).limit(limit)

        if entity_type:
            query = query.where(DeletionLog.entity_type == entity_type)

        result = await self.db_session.execute(query)
        log_entries = result.scalars().all()

        return [
            {
                "id": str(entry.id),
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id),
                "deletion_type": entry.deletion_type,
                "deleted_by": entry.deleted_by,
                "deleted_at": entry.created_at.isoformat(),
                "session_id": str(entry.session_id) if entry.session_id else None,
                "project_name": entry.project_name,
                "metadata": entry.metadata,
            }
            for entry in log_entries
        ]

    async def _log_deletion(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        deletion_type: str,
        deleted_by: str,
        metadata: dict[str, Any] | None = None,
        session_id: uuid.UUID | None = None,
        project_name: str | None = None,
    ) -> None:
        """Log a deletion event to the deletion_log table.

        Args:
            entity_type: Type of entity deleted
            entity_id: ID of the deleted entity
            deletion_type: Reason for deletion (retention, manual, cascade)
            deleted_by: Who initiated the deletion
            metadata: Additional context about the deletion
            session_id: Related session ID for cascade tracking
            project_name: Project name for easier querying
        """
        log_entry = DeletionLog(
            entity_type=entity_type,
            entity_id=entity_id,
            deletion_type=deletion_type,
            deleted_by=deleted_by,
            metadata=metadata or {},
            session_id=session_id,
            project_name=project_name,
        )
        self.db_session.add(log_entry)
        await self.db_session.flush()  # Flush but don't commit yet (caller will commit)


async def run_retention_cleanup() -> dict[str, Any]:
    """Run retention cleanup job (called by scheduler).

    This is the entry point for scheduled cleanup jobs.

    Returns:
        Dictionary with cleanup results
    """
    from db.connection import get_db_session

    async for db_session in get_db_session():
        service = RetentionPolicyService(db_session)
        return await service.run_cleanup(dry_run=False)

    return {"error": "No database session available"}
