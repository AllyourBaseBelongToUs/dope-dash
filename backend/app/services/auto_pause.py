"""Auto-pause service for managing automatic project pauses based on quota.

This service provides:
- Priority-based project pausing at quota thresholds
- Auto-resume when quota resets
- Manual override capabilities
- Pre-pause warning notifications
- Auto-pause history logging
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectStatus, ProjectPriority
from app.models.auto_pause import (
    AutoPauseLog,
    AutoPauseTrigger,
    AutoPauseStatus,
    AutoPauseSettings,
    AutoPauseLogResponse,
    AutoPauseLogListResponse,
    AutoPauseStatusResponse,
)
from app.models.state_transition import StateTransitionSource
from app.services.quota import QuotaService, CRITICAL_THRESHOLD, WARNING_THRESHOLD


logger = logging.getLogger(__name__)

# Default auto-pause settings
DEFAULT_AUTO_PAUSE_THRESHOLD = 95  # 95% - pause at this threshold
DEFAULT_WARNING_THRESHOLD = 80    # 80% - send warning at this threshold


class AutoPauseService:
    """Service for managing automatic project pauses based on quota thresholds.

    Features:
    - Pauses projects at configurable quota thresholds (default 95%)
    - Pauses lowest priority projects first
    - Sends warnings before pause (at 80% by default)
    - Auto-resumes projects after quota reset
    - Supports manual override
    - Maintains audit log of all auto-pause actions
    """

    def __init__(self, session: AsyncSession):
        """Initialize the auto-pause service.

        Args:
            session: Database session for queries
        """
        self._session = session
        self._quota_service = QuotaService(session)

    # ========== Settings Management ==========

    def get_project_settings(self, project: Project) -> AutoPauseSettings:
        """Get auto-pause settings for a project.

        Settings are stored in project metadata.

        Args:
            project: Project instance

        Returns:
            AutoPauseSettings instance
        """
        metadata = project.meta_data or {}
        settings_dict = metadata.get("auto_pause", {})

        return AutoPauseSettings(
            enabled=settings_dict.get("enabled", True),
            threshold_percent=settings_dict.get("threshold_percent", DEFAULT_AUTO_PAUSE_THRESHOLD),
            auto_resume=settings_dict.get("auto_resume", True),
            warning_threshold=settings_dict.get("warning_threshold", DEFAULT_WARNING_THRESHOLD),
        )

    async def update_project_settings(
        self,
        project_id: UUID,
        settings: AutoPauseSettings,
    ) -> Project | None:
        """Update auto-pause settings for a project.

        Args:
            project_id: Project UUID
            settings: New settings to apply

        Returns:
            Updated project or None if not found
        """
        result = await self._session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalars().first()

        if not project:
            return None

        # Update metadata
        metadata = project.meta_data or {}
        metadata["auto_pause"] = {
            "enabled": settings.enabled,
            "threshold_percent": settings.threshold_percent,
            "auto_resume": settings.auto_resume,
            "warning_threshold": settings.warning_threshold,
        }
        project.meta_data = metadata

        await self._session.flush()
        return project

    # ========== Threshold Monitoring ==========

    async def check_quotas_and_pause(self, provider_id: UUID | None = None) -> list[AutoPauseLog]:
        """Check quota thresholds and auto-pause projects if needed.

        This is the main entry point for auto-pause logic. It:
        1. Gets current quota usage
        2. Checks if any quotas exceed thresholds
        3. Pauses lowest priority projects first

        Args:
            provider_id: Optional specific provider to check (None = all)

        Returns:
            List of AutoPauseLog entries for paused projects
        """
        paused_logs: list[AutoPauseLog] = []

        # Get quota usage
        usage_response = await self._quota_service.get_quota_usage(provider_id=provider_id)

        for usage in usage_response.items:
            usage_percent = usage.usage_percent

            # Get all running projects for this provider
            running_projects = await self._get_running_projects()

            for project in running_projects:
                settings = self.get_project_settings(project)

                # Skip if auto-pause disabled for this project
                if not settings.enabled:
                    continue

                # Check if threshold exceeded
                if usage_percent >= settings.threshold_percent:
                    # Check if project already has pending/recent auto-pause
                    if await self._has_recent_auto_pause(project.id):
                        continue

                    # Pause the project
                    log_entry = await self._pause_project(
                        project=project,
                        trigger=AutoPauseTrigger.QUOTA_THRESHOLD,
                        threshold_percent=usage_percent,
                    )
                    if log_entry:
                        paused_logs.append(log_entry)

                # Send warning at warning threshold (if not already paused)
                elif usage_percent >= settings.warning_threshold:
                    await self._send_warning(project, usage_percent)

        return paused_logs

    async def check_and_auto_resume(self, provider_id: UUID | None = None) -> list[AutoPauseLog]:
        """Check if quota has reset and auto-resume paused projects.

        Called after quota reset detection.

        Args:
            provider_id: Optional specific provider to check

        Returns:
            List of AutoPauseLog entries for resumed projects
        """
        resumed_logs: list[AutoPauseLog] = []

        # Get quota usage - if usage is low enough, resume projects
        usage_response = await self._quota_service.get_quota_usage(provider_id=provider_id)

        for usage in usage_response.items:
            # Only resume if usage is below 70% (gives some buffer)
            if usage.usage_percent < 70:
                # Get auto-paused projects that have auto-resume enabled
                paused_logs = await self._get_auto_paused_projects()

                for log_entry in paused_logs:
                    project = await self._get_project(log_entry.project_id)
                    if not project:
                        continue

                    settings = self.get_project_settings(project)

                    # Skip if auto-resume disabled
                    if not settings.auto_resume:
                        continue

                    # Resume the project
                    resumed = await self._resume_project(log_entry)
                    if resumed:
                        resumed_logs.append(log_entry)

        return resumed_logs

    # ========== Project Operations ==========

    async def _pause_project(
        self,
        project: Project,
        trigger: AutoPauseTrigger,
        threshold_percent: float,
    ) -> AutoPauseLog | None:
        """Pause a project and log the action.

        Args:
            project: Project to pause
            trigger: What triggered the pause
            threshold_percent: Current quota percentage

        Returns:
            AutoPauseLog entry or None if pause failed
        """
        if project.status not in (ProjectStatus.RUNNING, ProjectStatus.IDLE):
            logger.warning(
                f"Cannot auto-pause project {project.name}: "
                f"status is {project.status.value}"
            )
            return None

        # Create log entry
        log_entry = AutoPauseLog(
            project_id=project.id,
            trigger=trigger,
            status=AutoPauseStatus.PENDING,
            threshold_percent=int(threshold_percent),
            priority_at_pause=project.priority.value,
            meta_data={
                "previous_status": project.status.value,
                "quota_percent": threshold_percent,
            },
        )
        self._session.add(log_entry)

        # Update project status
        previous_status = project.status
        project.status = ProjectStatus.PAUSED
        project.last_activity_at = datetime.now(timezone.utc)

        # Update metadata to track auto-paused state
        metadata = project.meta_data or {}
        metadata["auto_paused"] = True
        metadata["auto_paused_at"] = datetime.now(timezone.utc).isoformat()
        project.meta_data = metadata

        # Mark log as paused
        log_entry.mark_paused()

        await self._session.flush()

        # Broadcast auto-pause notification
        await self._broadcast_auto_pause(project, log_entry)

        logger.info(
            f"Auto-paused project {project.name} (priority: {project.priority.value}) "
            f"at {threshold_percent:.1f}% quota"
        )

        return log_entry

    async def _resume_project(self, log_entry: AutoPauseLog) -> bool:
        """Resume an auto-paused project.

        Args:
            log_entry: AutoPauseLog entry for the paused project

        Returns:
            True if resumed successfully
        """
        project = await self._get_project(log_entry.project_id)
        if not project:
            return False

        if project.status != ProjectStatus.PAUSED:
            logger.warning(
                f"Cannot auto-resume project {project.name}: "
                f"status is {project.status.value}, not PAUSED"
            )
            return False

        # Update project status
        if project.active_agents > 0:
            project.status = ProjectStatus.RUNNING
        else:
            project.status = ProjectStatus.IDLE

        project.last_activity_at = datetime.now(timezone.utc)

        # Update metadata
        metadata = project.meta_data or {}
        metadata["auto_paused"] = False
        metadata["auto_resumed_at"] = datetime.now(timezone.utc).isoformat()
        project.meta_data = metadata

        # Mark log as resumed
        log_entry.mark_resumed()

        await self._session.flush()

        # Broadcast auto-resume notification
        await self._broadcast_auto_resume(project, log_entry)

        logger.info(
            f"Auto-resumed project {project.name} after quota reset"
        )

        return True

    # ========== Manual Override ==========

    async def apply_manual_override(
        self,
        project_id: UUID,
        override_by: str,
        resume: bool = True,
    ) -> AutoPauseLog | None:
        """Apply a manual override to an auto-paused project.

        Args:
            project_id: Project UUID
            override_by: User applying the override
            resume: Whether to resume the project

        Returns:
            Updated AutoPauseLog or None
        """
        project = await self._get_project(project_id)
        if not project:
            return None

        # Get the most recent auto-pause log
        result = await self._session.execute(
            select(AutoPauseLog)
            .where(
                and_(
                    AutoPauseLog.project_id == project_id,
                    AutoPauseLog.status == AutoPauseStatus.PAUSED,
                )
            )
            .order_by(desc(AutoPauseLog.created_at))
            .limit(1)
        )
        log_entry = result.scalars().first()

        if not log_entry:
            logger.warning(f"No auto-pause log found for project {project_id}")
            return None

        # Mark as overridden
        log_entry.mark_overridden(override_by)

        if resume:
            # Resume the project
            if project.active_agents > 0:
                project.status = ProjectStatus.RUNNING
            else:
                project.status = ProjectStatus.IDLE

            # Update metadata
            metadata = project.meta_data or {}
            metadata["auto_paused"] = False
            metadata["override_by"] = override_by
            metadata["override_at"] = datetime.now(timezone.utc).isoformat()
            project.meta_data = metadata

        await self._session.flush()

        logger.info(
            f"Manual override applied to project {project.name} by {override_by}"
        )

        return log_entry

    # ========== Query Helpers ==========

    async def _get_running_projects(self) -> list[Project]:
        """Get all running projects sorted by priority (lowest first).

        Returns:
            List of projects sorted for pausing priority
        """
        result = await self._session.execute(
            select(Project)
            .where(
                and_(
                    Project.status.in_([ProjectStatus.RUNNING, ProjectStatus.IDLE]),
                    Project.deleted_at.is_(None),
                )
            )
            .order_by(
                # Order by priority: LOW=0, MEDIUM=1, HIGH=2, CRITICAL=3
                # Pause LOW priority first
                Project.priority,
            )
        )
        return list(result.scalars().all())

    async def _get_auto_paused_projects(self) -> list[AutoPauseLog]:
        """Get projects that were auto-paused and can be resumed.

        Returns:
            List of AutoPauseLog entries for paused projects
        """
        result = await self._session.execute(
            select(AutoPauseLog)
            .where(AutoPauseLog.status == AutoPauseStatus.PAUSED)
            .order_by(desc(AutoPauseLog.priority_at_pause))
        )
        return list(result.scalars().all())

    async def _has_recent_auto_pause(self, project_id: UUID) -> bool:
        """Check if project has a recent auto-pause within the last hour.

        Args:
            project_id: Project UUID

        Returns:
            True if recent auto-pause exists
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await self._session.execute(
            select(AutoPauseLog)
            .where(
                and_(
                    AutoPauseLog.project_id == project_id,
                    AutoPauseLog.status.in_([
                        AutoPauseStatus.PENDING,
                        AutoPauseStatus.PAUSED,
                    ]),
                    AutoPauseLog.created_at >= cutoff,
                )
            )
            .limit(1)
        )
        return result.scalars().first() is not None

    async def _get_project(self, project_id: UUID) -> Project | None:
        """Get a project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project or None
        """
        result = await self._session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalars().first()

    # ========== Notifications ==========

    async def _send_warning(self, project: Project, usage_percent: float) -> None:
        """Send a warning notification before auto-pause.

        Args:
            project: Project to warn about
            usage_percent: Current quota percentage
        """
        settings = self.get_project_settings(project)

        # Check if warning already sent recently
        metadata = project.meta_data or {}
        last_warning = metadata.get("last_warning_at")

        if last_warning:
            # Only send warning every 30 minutes
            from datetime import timedelta
            last_warning_dt = datetime.fromisoformat(last_warning)
            if datetime.now(timezone.utc) - last_warning_dt < timedelta(minutes=30):
                return

        # Update last warning time
        metadata["last_warning_at"] = datetime.now(timezone.utc).isoformat()
        project.meta_data = metadata
        await self._session.flush()

        # Broadcast warning
        await self._broadcast_warning(project, usage_percent, settings.threshold_percent)

        logger.info(
            f"Sent auto-pause warning for project {project.name} "
            f"at {usage_percent:.1f}% (will pause at {settings.threshold_percent}%)"
        )

    async def _broadcast_warning(
        self,
        project: Project,
        usage_percent: float,
        threshold: float,
    ) -> None:
        """Broadcast auto-pause warning via WebSocket."""
        try:
            from server.websocket import manager

            message = {
                "type": "auto_pause_warning",
                "data": {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "priority": project.priority.value,
                    "usage_percent": usage_percent,
                    "threshold_percent": threshold,
                    "message": f"Project {project.name} will auto-pause at {threshold}% quota",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast auto-pause warning: {e}")

    async def _broadcast_auto_pause(
        self,
        project: Project,
        log_entry: AutoPauseLog,
    ) -> None:
        """Broadcast auto-pause event via WebSocket."""
        try:
            from server.websocket import manager

            message = {
                "type": "auto_pause_triggered",
                "data": {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "priority": project.priority.value,
                    "trigger": log_entry.trigger.value,
                    "threshold_percent": log_entry.threshold_percent,
                    "message": f"Project {project.name} auto-paused at {log_entry.threshold_percent}% quota",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast auto-pause: {e}")

    async def _broadcast_auto_resume(
        self,
        project: Project,
        log_entry: AutoPauseLog,
    ) -> None:
        """Broadcast auto-resume event via WebSocket."""
        try:
            from server.websocket import manager

            message = {
                "type": "auto_resume_triggered",
                "data": {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "priority": project.priority.value,
                    "message": f"Project {project.name} auto-resumed after quota reset",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            await manager.broadcast(message)
        except Exception as e:
            logger.warning(f"Failed to broadcast auto-resume: {e}")

    # ========== API Response Helpers ==========

    async def get_pause_history(
        self,
        project_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AutoPauseLogListResponse:
        """Get auto-pause history.

        Args:
            project_id: Optional project filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of auto-pause log entries
        """
        query = select(AutoPauseLog).order_by(desc(AutoPauseLog.created_at))

        if project_id:
            query = query.where(AutoPauseLog.project_id == project_id)

        # Get total count
        count_query = select(AutoPauseLog)
        if project_id:
            count_query = count_query.where(AutoPauseLog.project_id == project_id)

        # This is a simplified count - in production would use func.count
        result = await self._session.execute(query.limit(limit).offset(offset))
        logs = list(result.scalars().all())

        return AutoPauseLogListResponse(
            items=[AutoPauseLogResponse.model_validate(log) for log in logs],
            total=len(logs),  # Simplified - would do proper count in production
        )

    async def get_status(self, project_id: UUID) -> AutoPauseStatusResponse | None:
        """Get auto-pause status for a project.

        Args:
            project_id: Project UUID

        Returns:
            AutoPauseStatusResponse or None
        """
        project = await self._get_project(project_id)
        if not project:
            return None

        settings = self.get_project_settings(project)

        # Get statistics
        result = await self._session.execute(
            select(AutoPauseLog)
            .where(AutoPauseLog.project_id == project_id)
            .order_by(desc(AutoPauseLog.created_at))
        )
        logs = list(result.scalars().all())

        last_pause = next(
            (l.paused_at for l in logs if l.paused_at),
            None
        )
        last_resume = next(
            (l.resumed_at for l in logs if l.resumed_at),
            None
        )
        total_pauses = sum(1 for l in logs if l.status == AutoPauseStatus.PAUSED)
        total_resumes = sum(1 for l in logs if l.status == AutoPauseStatus.RESUMED)

        return AutoPauseStatusResponse(
            enabled=settings.enabled,
            current_threshold=settings.threshold_percent,
            warning_threshold=settings.warning_threshold,
            auto_resume_enabled=settings.auto_resume,
            last_pause_at=last_pause,
            last_resume_at=last_resume,
            total_pauses=total_pauses,
            total_resumes=total_resumes,
        )


# ========== Dependency ==========

def get_auto_pause_service(session: AsyncSession) -> AutoPauseService:
    """Get auto-pause service instance.

    Args:
        session: Database session

    Returns:
        AutoPauseService instance
    """
    return AutoPauseService(session)
