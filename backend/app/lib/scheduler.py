"""Background scheduler for automated report generation and retention cleanup.

This module provides APScheduler-based background task scheduling
for generating reports on a periodic basis and cleaning up old data.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import (
    ReportSchedule,
    Report,
    ReportStatus,
    ScheduleFrequency,
    ReportConfig,
)
from app.lib.report_generator import generate_report
from app.services.retention import RetentionPolicyService
from db.connection import get_db_session


logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        logger.info("Created new APScheduler instance")
    return _scheduler


async def run_scheduled_reports() -> None:
    """Check and run all pending scheduled reports.

    This function is called periodically to check if any scheduled
    reports need to run based on their next_run_at timestamp.
    """
    logger.info("Checking for scheduled reports to run")

    async for db_session in get_db_session():
        try:
            # Get all enabled schedules that are due to run
            now = datetime.now()
            query = select(ReportSchedule).where(
                ReportSchedule.enabled == True,
                ReportSchedule.next_run_at.isnot(None),
            )

            result = await db_session.execute(query)
            schedules = result.scalars().all()

            for schedule in schedules:
                try:
                    # Parse next_run_at
                    next_run_str = schedule.next_run_at
                    if not next_run_str:
                        continue

                    try:
                        next_run = datetime.fromisoformat(next_run_str)
                    except ValueError:
                        logger.warning(f"Invalid next_run_at format for schedule {schedule.id}: {next_run_str}")
                        continue

                    # Check if schedule is due
                    if next_run <= now:
                        logger.info(f"Running scheduled report: {schedule.name}")

                        await execute_schedule(schedule, db_session)

                except Exception as e:
                    logger.error(f"Error processing schedule {schedule.id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in run_scheduled_reports: {e}", exc_info=True)


async def execute_schedule(schedule: ReportSchedule, db_session: AsyncSession) -> None:
    """Execute a report schedule and generate all configured reports.

    Args:
        schedule: The report schedule to execute
        db_session: Database session
    """
    from app.models.report import ReportType, ReportFormat

    report_types_list = schedule.report_types.get("types", [])
    generated_count = 0
    failed_count = 0

    for report_type_str in report_types_list:
        try:
            report_type = ReportType(report_type_str)

            # Create report config
            report_config = ReportConfig(
                type=report_type,
                format=ReportFormat(schedule.format.value),
                title=f"Scheduled {report_type.value} Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                include_charts=True,
            )

            # Create report record
            report = Report(
                title=report_config.title,
                type=report_config.type,
                format=report_config.format,
                status=ReportStatus.GENERATING,
                config=report_config.model_dump(),
            )

            db_session.add(report)
            await db_session.commit()
            await db_session.refresh(report)

            # Generate report content
            report_id_str = str(report.id)
            file_ext, content, content_type = await generate_report(
                report_config, report_id_str, db_session
            )

            from pathlib import Path
            import os

            REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
            report_file = REPORTS_DIR / f"report-{report_id_str}{file_ext}"

            if isinstance(content, bytes):
                with open(report_file, "wb") as f:
                    f.write(content)
            else:
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(content)

            report.file_path = str(report_file)

            if schedule.format == ReportFormat.JSON:
                report.content = content

            report.status = ReportStatus.COMPLETED
            generated_count += 1

        except Exception as e:
            logger.error(f"Failed to generate report for schedule {schedule.name}, type {report_type_str}: {e}")
            if report:
                report.status = ReportStatus.FAILED
            failed_count += 1

    # Update schedule with last run time and calculate next run
    schedule.last_run_at = datetime.now().isoformat()

    # Calculate next run time based on frequency
    next_run = calculate_next_run(schedule.frequency)
    schedule.next_run_at = next_run.isoformat() if next_run else None

    await db_session.commit()

    logger.info(
        f"Schedule '{schedule.name}' completed: "
        f"{generated_count} generated, {failed_count} failed. "
        f"Next run: {schedule.next_run_at}"
    )


def calculate_next_run(frequency: ScheduleFrequency) -> datetime | None:
    """Calculate next run time based on frequency."""
    from datetime import timedelta

    if frequency == ScheduleFrequency.NONE:
        return None

    now = datetime.now()

    if frequency == ScheduleFrequency.DAILY:
        # Next day at 9 AM
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run

    if frequency == ScheduleFrequency.WEEKLY:
        # Next Monday at 9 AM
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        days_ahead = 0 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run += timedelta(days=days_ahead)
        if next_run <= now:
            next_run += timedelta(weeks=1)
        return next_run

    if frequency == ScheduleFrequency.MONTHLY:
        # First day of next month at 9 AM
        next_run = now.replace(day=1, hour=9, minute=0, second=0, microsecond=0)
        if next_run <= now:
            # Move to next month
            if next_run.month == 12:
                next_run = next_run.replace(year=next_run.year + 1, month=1)
            else:
                next_run = next_run.replace(month=next_run.month + 1)
        return next_run

    return None


def start_scheduler() -> None:
    """Start the background scheduler for scheduled reports, retention cleanup, and agent detection.

    This adds jobs that:
    - Check for scheduled reports every minute
    - Run retention cleanup daily at 3 AM
    - Run agent detection every 2 minutes
    """
    scheduler = get_scheduler()

    # Add job to check for scheduled reports every minute
    scheduler.add_job(
        run_scheduled_reports,
        "interval",
        minutes=1,
        id="check_scheduled_reports",
        replace_existing=True,
    )

    # Add daily retention cleanup job at 3 AM
    scheduler.add_job(
        run_retention_cleanup,
        "cron",
        hour=3,
        minute=0,
        id="retention_cleanup",
        replace_existing=True,
    )

    # Add periodic agent detection job every 2 minutes
    scheduler.add_job(
        run_agent_detection,
        "interval",
        minutes=2,
        id="agent_detection",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Background scheduler stopped")


async def run_retention_cleanup() -> None:
    """Run daily retention cleanup job.

    This function is called daily to clean up events older than 30 days
    and sessions older than 1 year.
    """
    logger.info("Starting daily retention cleanup")

    async for db_session in get_db_session():
        try:
            service = RetentionPolicyService(db_session)
            result = await service.run_cleanup(dry_run=False)

            logger.info(
                f"Retention cleanup completed: "
                f"{result['events']['total_deleted_count']} events, "
                f"{result['sessions']['total_deleted_count']} sessions deleted "
                f"in {result['total_duration_seconds']:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error in retention cleanup: {e}", exc_info=True)


async def run_agent_detection() -> None:
    """Run periodic agent detection scan.

    This function is called periodically to detect running agents
    and sync them to the database.
    """
    logger.info("Starting periodic agent detection")

    try:
        from app.services.agent_registry import get_agent_registry
        from app.services.agent_pool_sync import get_agent_pool_sync_service

        registry = get_agent_registry()
        sync_service = get_agent_pool_sync_service()

        # Detect all agents
        detected = await registry._detector.detect_all_agents()

        # Register any newly detected agents
        registered_count = 0
        for agent_info in detected:
            existing = registry.get_agent(
                f"{agent_info.agent_type.value}-{agent_info.project_name}"
            )
            if not existing:
                await registry.register_agent(
                    agent_type=agent_info.agent_type,
                    project_name=agent_info.project_name,
                    pid=agent_info.pid,
                    working_dir=agent_info.working_dir,
                    command=agent_info.command,
                    tmux_session=agent_info.tmux_session,
                    metadata=agent_info.metadata,
                )
                registered_count += 1

        # Sync to database
        sync_result = await sync_service.sync_once()

        logger.info(
            f"Agent detection completed: "
            f"{len(detected)} detected, {registered_count} newly registered, "
            f"sync: {sync_result['added']} added, {sync_result['updated']} updated"
        )

    except Exception as e:
        logger.error(f"Error in agent detection: {e}", exc_info=True)


def restart_scheduler() -> None:
    """Restart the background scheduler."""
    stop_scheduler()
    start_scheduler()
