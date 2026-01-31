"""Reports API endpoints for report generation and scheduling.

Provides endpoints for generating reports, managing report history,
and handling scheduled report generation.
"""
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session

from app.models.report import (
    Report,
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportConfig,
    ReportSchedule,
    ReportScheduleCreate,
    ReportScheduleUpdate,
    ReportScheduleResponse,
    ReportScheduleConfig,
    ReportStatus,
    ScheduleFrequency,
)
from app.lib.report_generator import generate_report


router = APIRouter(prefix="/api/reports", tags=["reports"])

# Configuration for report storage
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
REPORTS_DIR.mkdir(exist_ok=True)

# Default retention period (days)
DEFAULT_RETENTION_DAYS = int(os.getenv("REPORT_RETENTION_DAYS", "30"))


def calculate_next_run(frequency: ScheduleFrequency) -> datetime | None:
    """Calculate next run time based on frequency."""
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


async def cleanup_old_reports(
    session: AsyncSession,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> int:
    """Clean up reports older than retention period.

    Args:
        session: Database session
        retention_days: Number of days to retain reports

    Returns:
        Number of reports deleted
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    # Delete old reports from database
    delete_query = delete(Report).where(Report.created_at < cutoff_date)
    result = await session.execute(delete_query)
    deleted_count = result.rowcount

    # Delete old report files
    for file_path in REPORTS_DIR.glob("report-*."):
        if file_path.suffix != ".meta.json" and file_path.stat().st_mtime < cutoff_date.timestamp():
            try:
                file_path.unlink()
                # Also delete metadata file
                metadata_file = file_path.with_suffix(".meta.json")
                if metadata_file.exists():
                    metadata_file.unlink()
            except Exception:
                pass

    await session.commit()
    return deleted_count


@router.post("/generate")
async def generate_report_endpoint(
    config: ReportConfig,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Generate a new report.

    This endpoint creates a report record and initiates report generation.

    Args:
        config: Report configuration
        db_session: Database session

    Returns:
        Report metadata including ID and status
    """
    # Create report record
    report = Report(
        title=config.title,
        type=config.type,
        format=config.format,
        status=ReportStatus.GENERATING,
        config=config.model_dump(),
    )

    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    try:
        # Generate the report content
        report_id_str = str(report.id)
        file_ext, content, content_type = await generate_report(config, report_id_str, db_session)

        # Determine file path
        report_file = REPORTS_DIR / f"report-{report_id_str}{file_ext}"

        # Write content to file
        if isinstance(content, bytes):
            with open(report_file, "wb") as f:
                f.write(content)
        else:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(content)

        # Update report with file path and completed status
        report.file_path = str(report_file)

        # Store text content in database for JSON format
        if config.format == ReportFormat.JSON:
            report.content = content

        report.status = ReportStatus.COMPLETED

        await db_session.commit()
        await db_session.refresh(report)

        return {
            "id": str(report.id),
            "title": report.title,
            "type": report.type.value,
            "format": report.format.value,
            "status": report.status.value,
            "createdAt": report.created_at.isoformat(),
            "downloadUrl": f"/api/reports/download/{report.id}",
        }

    except Exception as e:
        # Update report status to failed
        report.status = ReportStatus.FAILED
        await db_session.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("")
async def list_reports(
    type: str | None = Query(None, description="Filter by report type"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List all reports with optional filters.

    Args:
        type: Filter by report type
        status: Filter by status
        limit: Maximum number of reports to return
        offset: Offset for pagination
        db_session: Database session

    Returns:
        Dictionary with reports list and pagination info
    """
    query = select(Report)

    # Apply filters
    conditions = []
    if type:
        conditions.append(Report.type == type)
    if status:
        conditions.append(Report.status == status)

    if conditions:
        query = query.where(and_(*conditions))

    # Order by created_at descending
    query = query.order_by(Report.created_at.desc())

    # Get total count
    count_query = select(Report.id)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db_session.execute(count_query)
    total = len(count_result.all())

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db_session.execute(query)
    reports = result.scalars().all()

    return {
        "reports": [
            {
                "id": str(report.id),
                "title": report.title,
                "type": report.type.value,
                "format": report.format.value,
                "status": report.status.value,
                "config": report.config,
                "filePath": report.file_path,
                "createdAt": report.created_at.isoformat(),
                "updatedAt": report.updated_at.isoformat(),
            }
            for report in reports
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a specific report.

    Args:
        report_id: Report UUID
        db_session: Database session

    Returns:
        Report details
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    query = select(Report).where(Report.id == report_uuid)
    result = await db_session.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": str(report.id),
        "title": report.title,
        "type": report.type.value,
        "format": report.format.value,
        "status": report.status.value,
        "config": report.config,
        "content": report.content,
        "filePath": report.file_path,
        "createdAt": report.created_at.isoformat(),
        "updatedAt": report.updated_at.isoformat(),
        "downloadUrl": f"/api/reports/download/{report.id}",
    }


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Download a report file.

    Args:
        report_id: Report UUID
        db_session: Database session

    Returns:
        File response with the report content
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    query = select(Report).where(Report.id == report_uuid)
    result = await db_session.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.file_path:
        raise HTTPException(status_code=404, detail="Report file not available")

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    # Determine content type based on format
    content_type_map = {
        "pdf": "application/pdf",
        "markdown": "text/markdown",
        "md": "text/markdown",
        "json": "application/json",
        "html": "text/html",
    }

    content_type = content_type_map.get(report.format.value, "application/octet-stream")

    # Create filename with title and extension
    safe_title = "".join(c for c in report.title if c.isalnum() or c in (" ", "-", "_")).strip()
    filename = f"{safe_title or 'report'}-{report_id[:8]}{file_path.suffix}"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete a report.

    Args:
        report_id: Report UUID
        db_session: Database session

    Returns:
        Deletion status
    """
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id format")

    query = select(Report).where(Report.id == report_uuid)
    result = await db_session.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete file if it exists
    if report.file_path:
        file_path = Path(report.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
                # Also delete metadata file
                metadata_file = file_path.with_suffix(".meta.json")
                if metadata_file.exists():
                    metadata_file.unlink()
            except Exception:
                pass

    # Delete database record
    await db_session.delete(report)
    await db_session.commit()

    return {"status": "deleted", "reportId": report_id}


# Schedule endpoints
@router.post("/schedules")
async def create_schedule(
    config: ReportScheduleCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new report schedule.

    Args:
        config: Schedule configuration
        db_session: Database session

    Returns:
        Created schedule details
    """
    next_run = calculate_next_run(config.frequency)

    schedule = ReportSchedule(
        name=config.name,
        enabled=config.enabled,
        frequency=config.frequency,
        report_types={"types": [rt.value for rt in config.report_types]},
        format=config.format,
        retention_days=config.retention_days,
        next_run_at=next_run.isoformat() if next_run else None,
    )

    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)

    return {
        "id": str(schedule.id),
        "name": schedule.name,
        "enabled": schedule.enabled,
        "frequency": schedule.frequency.value,
        "reportTypes": schedule.report_types.get("types", []),
        "format": schedule.format.value,
        "retentionDays": schedule.retention_days,
        "config": schedule.config,
        "lastRunAt": schedule.last_run_at,
        "nextRunAt": schedule.next_run_at,
        "createdAt": schedule.created_at.isoformat(),
        "updatedAt": schedule.updated_at.isoformat(),
    }


@router.get("/schedules")
async def list_schedules(
    enabled_only: bool = Query(False, description="Filter by enabled status"),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List all report schedules.

    Args:
        enabled_only: Only return enabled schedules
        db_session: Database session

    Returns:
        List of schedules
    """
    query = select(ReportSchedule)

    if enabled_only:
        query = query.where(ReportSchedule.enabled == True)

    query = query.order_by(ReportSchedule.created_at.desc())

    result = await db_session.execute(query)
    schedules = result.scalars().all()

    return {
        "schedules": [
            {
                "id": str(schedule.id),
                "name": schedule.name,
                "enabled": schedule.enabled,
                "frequency": schedule.frequency.value,
                "reportTypes": schedule.report_types.get("types", []),
                "format": schedule.format.value,
                "retentionDays": schedule.retention_days,
                "config": schedule.config,
                "lastRunAt": schedule.last_run_at,
                "nextRunAt": schedule.next_run_at,
                "createdAt": schedule.created_at.isoformat(),
                "updatedAt": schedule.updated_at.isoformat(),
            }
            for schedule in schedules
        ]
    }


@router.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    config: ReportScheduleUpdate,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update a report schedule.

    Args:
        schedule_id: Schedule UUID
        config: Update configuration
        db_session: Database session

    Returns:
        Updated schedule details
    """
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule_id format")

    query = select(ReportSchedule).where(ReportSchedule.id == schedule_uuid)
    result = await db_session.execute(query)
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    if config.name is not None:
        schedule.name = config.name
    if config.enabled is not None:
        schedule.enabled = config.enabled
    if config.frequency is not None:
        schedule.frequency = config.frequency
    if config.report_types is not None:
        schedule.report_types = {"types": [rt.value for rt in config.report_types]}
    if config.format is not None:
        schedule.format = config.format
    if config.retention_days is not None:
        schedule.retention_days = config.retention_days
    if config.config is not None:
        schedule.config = config.config
    if config.next_run_at is not None:
        schedule.next_run_at = config.next_run_at

    # Recalculate next run if frequency changed
    if config.frequency is not None or config.enabled is not None:
        next_run = calculate_next_run(schedule.frequency)
        schedule.next_run_at = next_run.isoformat() if next_run else None

    await db_session.commit()
    await db_session.refresh(schedule)

    return {
        "id": str(schedule.id),
        "name": schedule.name,
        "enabled": schedule.enabled,
        "frequency": schedule.frequency.value,
        "reportTypes": schedule.report_types.get("types", []),
        "format": schedule.format.value,
        "retentionDays": schedule.retention_days,
        "config": schedule.config,
        "lastRunAt": schedule.last_run_at,
        "nextRunAt": schedule.next_run_at,
        "createdAt": schedule.created_at.isoformat(),
        "updatedAt": schedule.updated_at.isoformat(),
    }


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete a report schedule.

    Args:
        schedule_id: Schedule UUID
        db_session: Database session

    Returns:
        Deletion status
    """
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule_id format")

    query = select(ReportSchedule).where(ReportSchedule.id == schedule_uuid)
    result = await db_session.execute(query)
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await db_session.delete(schedule)
    await db_session.commit()

    return {"status": "deleted", "scheduleId": schedule_id}


@router.post("/schedules/{schedule_id}/test")
async def test_schedule(
    schedule_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Test a report schedule by running it immediately.

    Args:
        schedule_id: Schedule UUID
        db_session: Database session

    Returns:
        Test run results
    """
    try:
        schedule_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule_id format")

    query = select(ReportSchedule).where(ReportSchedule.id == schedule_uuid)
    result = await db_session.execute(query)
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Generate reports for each configured type
    generated_reports = []
    report_types_list = schedule.report_types.get("types", [])

    from app.models.report import ReportType, ReportConfig as ReportConfigModel

    for report_type_str in report_types_list:
        try:
            report_type = ReportType(report_type_str)
            report_config = ReportConfigModel(
                type=report_type,
                format=schedule.format,
                title=f"Test {report_type.value} Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                include_charts=True,
            )

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

            # Generate actual report content
            report_id_str = str(report.id)
            try:
                file_ext, content, content_type = await generate_report(
                    report_config, report_id_str, db_session
                )
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

                generated_reports.append({
                    "id": str(report.id),
                    "title": report.title,
                    "type": report.type.value,
                    "format": report.format.value,
                    "status": report.status.value,
                })
            except Exception as gen_error:
                report.status = ReportStatus.FAILED
                generated_reports.append({
                    "type": report_type_str,
                    "status": "failed",
                    "error": str(gen_error),
                })

            await db_session.commit()
            await db_session.refresh(report)

        except Exception as e:
            generated_reports.append({
                "type": report_type_str,
                "status": "failed",
                "error": str(e),
            })

    # Update last run time
    schedule.last_run_at = datetime.now().isoformat()
    await db_session.commit()

    return {
        "scheduleId": str(schedule.id),
        "scheduleName": schedule.name,
        "generatedReports": generated_reports,
        "testRunAt": schedule.last_run_at,
    }


@router.post("/cleanup")
async def cleanup_reports(
    retentionDays: int = Query(DEFAULT_RETENTION_DAYS, ge=1, le=365, description="Retention period in days"),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Clean up old reports based on retention policy.

    Args:
        retentionDays: Number of days to retain reports
        db_session: Database session

    Returns:
        Cleanup results
    """
    deleted_count = await cleanup_old_reports(db_session, retentionDays)

    return {
        "status": "completed",
        "deletedCount": deleted_count,
        "retentionDays": retentionDays,
    }
