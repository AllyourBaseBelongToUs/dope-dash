"""Commands API endpoints for custom command history.

Provides endpoints for managing custom commands sent to agents,
including command history, replay functionality, favorites, and templates.
"""
import logging
import csv
import uuid
import io
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, func, select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session

from app.models.project import Project
from app.models.command_history import (
    CommandHistory,
    CommandStatus,
    CommandHistoryCreate,
    CommandHistoryUpdate,
    CommandHistoryEntry,
    CommandTemplate,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/commands", tags=["commands"])


# Default command templates
DEFAULT_TEMPLATES = [
    CommandTemplate(
        id="t-1",
        name="List Files",
        description="List all files in the current directory",
        command="ls -la",
        category="files",
        tags=["list", "files"],
    ),
    CommandTemplate(
        id="t-2",
        name="Git Status",
        description="Show git repository status",
        command="git status",
        category="git",
        tags=["git", "status"],
    ),
    CommandTemplate(
        id="t-3",
        name="Git Log",
        description="Show recent git commits",
        command="git log --oneline -10",
        category="git",
        tags=["git", "log", "history"],
    ),
    CommandTemplate(
        id="t-4",
        name="Process List",
        description="List running processes",
        command="ps aux",
        category="system",
        tags=["processes", "system"],
    ),
    CommandTemplate(
        id="t-5",
        name="Disk Usage",
        description="Check disk usage",
        command="df -h",
        category="system",
        tags=["disk", "storage"],
    ),
    CommandTemplate(
        id="t-6",
        name="Memory Usage",
        description="Check memory usage",
        command="free -h",
        category="system",
        tags=["memory", "ram"],
    ),
    CommandTemplate(
        id="t-7",
        name="Network Connections",
        description="List network connections",
        command="netstat -tuln",
        category="network",
        tags=["network", "connections"],
    ),
    CommandTemplate(
        id="t-8",
        name="Test Connection",
        description="Test network connectivity to a host",
        command="ping -c 4 {{host}}",
        category="network",
        tags=["ping", "network", "test"],
    ),
    CommandTemplate(
        id="t-9",
        name="Find Files",
        description="Find files by name pattern",
        command="find . -name '{{pattern}}' -type f",
        category="files",
        tags=["find", "search", "files"],
    ),
    CommandTemplate(
        id="t-10",
        name="Grep Search",
        description="Search for text in files",
        command="grep -r '{{search_term}}' .",
        category="search",
        tags=["grep", "search", "text"],
    ),
]


class SendCommandRequest(BaseModel):
    """Request body for sending a custom command."""

    command: str = Field(..., description="Command to send")
    project_id: str | None = Field(None, description="Project ID (optional)")
    session_id: str | None = Field(None, description="Session ID (optional)")
    template_name: str | None = Field(None, description="Template name if from template")


class ReplayCommandRequest(BaseModel):
    """Request body for replaying a command."""

    command_id: str = Field(..., description="Command ID to replay")


class ToggleFavoriteRequest(BaseModel):
    """Request body for toggling favorite status."""

    is_favorite: bool = Field(..., description="New favorite status")


@router.get("/history")
async def get_command_history(
    project_id: str | None = Query(None, description="Filter by project ID"),
    session_id: str | None = Query(None, description="Filter by session ID"),
    status: CommandStatus | None = Query(None, description="Filter by command status"),
    is_favorite: bool | None = Query(None, description="Filter by favorite status"),
    search: str | None = Query(None, description="Search in command text"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get command history with optional filters.

    Args:
        project_id: Filter by project ID
        session_id: Filter by session ID
        status: Filter by command status
        is_favorite: Filter by favorite status
        search: Search in command text
        limit: Maximum number of results
        offset: Pagination offset
        session: Database session

    Returns:
        Command history entries with metadata
    """
    query: Select[tuple[CommandHistory]] = select(CommandHistory).order_by(
        desc(CommandHistory.created_at)
    )

    # Apply filters
    if project_id:
        try:
            project_uuid = uuid.UUID(project_id)
            query = query.where(CommandHistory.project_id == project_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format")

    if session_id:
        query = query.where(CommandHistory.session_id == session_id)

    if status:
        query = query.where(CommandHistory.status == status)

    if is_favorite is not None:
        query = query.where(CommandHistory.is_favorite == is_favorite)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(CommandHistory.command.ilike(search_pattern))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(query)
    commands = result.scalars().all()

    return {
        "commands": [
            CommandHistoryEntry.from_model(c).model_dump(by_alias=True, exclude_none=True)
            for c in commands
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/history/{command_id}")
async def get_command(
    command_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a single command by ID.

    Args:
        command_id: Command UUID
        db_session: Database session

    Returns:
        Command details
    """
    try:
        command_uuid = uuid.UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid command_id format")

    query = select(CommandHistory).where(CommandHistory.id == command_uuid)
    result = await db_session.execute(query)
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    return CommandHistoryEntry.from_model(command).model_dump(by_alias=True, exclude_none=True)


@router.get("/projects/{project_id}/history")
async def get_project_command_history(
    project_id: str,
    status: CommandStatus | None = Query(None, description="Filter by command status"),
    is_favorite: bool | None = Query(None, description="Filter by favorite status"),
    search: str | None = Query(None, description="Search in command text"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get command history for a specific project.

    Args:
        project_id: Project UUID
        status: Filter by command status
        is_favorite: Filter by favorite status
        search: Search in command text
        limit: Maximum number of results
        offset: Pagination offset
        session: Database session

    Returns:
        Command history entries for the project
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Verify project exists
    project_query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get command history for this project
    query = select(CommandHistory).where(
        CommandHistory.project_id == project_uuid
    ).order_by(
        desc(CommandHistory.created_at)
    )

    # Apply additional filters
    if status:
        query = query.where(CommandHistory.status == status)

    if is_favorite is not None:
        query = query.where(CommandHistory.is_favorite == is_favorite)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(CommandHistory.command.ilike(search_pattern))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    commands = result.scalars().all()

    return {
        "commands": [
            CommandHistoryEntry.from_model(c).model_dump(by_alias=True, exclude_none=True)
            for c in commands
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/recent")
async def get_recent_commands(
    project_id: str | None = Query(None, description="Filter by project ID"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get recent commands for typeahead functionality.

    Args:
        project_id: Optional project ID filter
        limit: Maximum number of results
        session: Database session

    Returns:
        List of recent commands (command text only)
    """
    query = select(CommandHistory.command).distinct().order_by(
        desc(CommandHistory.created_at)
    ).limit(limit)

    if project_id:
        try:
            project_uuid = uuid.UUID(project_id)
            query = query.where(CommandHistory.project_id == project_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format")

    result = await session.execute(query)
    commands = result.scalars().all()

    return {
        "commands": list(commands),
    }


@router.get("/favorites")
async def get_favorite_commands(
    project_id: str | None = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get favorite commands.

    Args:
        project_id: Optional project ID filter
        limit: Maximum number of results
        offset: Pagination offset
        session: Database session

    Returns:
        List of favorite commands
    """
    query = select(CommandHistory).where(
        CommandHistory.is_favorite == True
    ).order_by(
        desc(CommandHistory.created_at)
    )

    if project_id:
        try:
            project_uuid = uuid.UUID(project_id)
            query = query.where(CommandHistory.project_id == project_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    commands = result.scalars().all()

    return {
        "commands": [
            CommandHistoryEntry.from_model(c).model_dump(by_alias=True, exclude_none=True)
            for c in commands
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/templates")
async def get_command_templates() -> dict[str, Any]:
    """Get available command templates.

    Returns:
        List of command templates
    """
    return {
        "templates": [t.model_dump() for t in DEFAULT_TEMPLATES],
    }


@router.post("/send")
async def send_command(
    request: SendCommandRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Send a custom command and record it in history.

    Args:
        request: Command send request
        session: Database session

    Returns:
        Created command record
    """
    # Validate project_id if provided
    project_uuid = None
    if request.project_id:
        try:
            project_uuid = uuid.UUID(request.project_id)
            # Verify project exists
            project_query = select(Project).where(
                and_(
                    Project.id == project_uuid,
                    Project.deleted_at.is_(None)
                )
            )
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Create command history entry
    command = CommandHistory(
        project_id=project_uuid,
        session_id=request.session_id,
        command=request.command,
        status=CommandStatus.SENT,
        template_name=request.template_name,
        meta_data={},
    )

    session.add(command)
    await session.commit()
    await session.refresh(command)

    # TODO: Actually send the command to the agent/session
    # This would integrate with the agent control system

    return CommandHistoryEntry.from_model(command).model_dump(by_alias=True, exclude_none=True)


@router.post("/replay")
async def replay_command(
    request: ReplayCommandRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Replay a previous command.

    Args:
        request: Replay request with command ID
        session: Database session

    Returns:
        New command record created from replay
    """
    try:
        command_uuid = uuid.UUID(request.command_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid command_id format")

    # Get original command
    query = select(CommandHistory).where(CommandHistory.id == command_uuid)
    result = await session.execute(query)
    original_command = result.scalar_one_or_none()

    if not original_command:
        raise HTTPException(status_code=404, detail="Command not found")

    # Create new command entry from original
    new_command = CommandHistory(
        project_id=original_command.project_id,
        session_id=original_command.session_id,
        command=original_command.command,
        status=CommandStatus.SENT,
        template_name=original_command.template_name,
        meta_data={
            "replayed_from": str(original_command.id),
            "original_created_at": original_command.created_at.isoformat(),
        },
    )

    session.add(new_command)
    await session.commit()
    await session.refresh(new_command)

    # TODO: Actually send the command to the agent/session
    # This would integrate with the agent control system

    return CommandHistoryEntry.from_model(new_command).model_dump(by_alias=True, exclude_none=True)


@router.patch("/history/{command_id}")
async def update_command(
    command_id: str,
    updates: CommandHistoryUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update a command record (status, result, favorite, etc.).

    Args:
        command_id: Command UUID
        updates: Fields to update
        session: Database session

    Returns:
        Updated command record
    """
    try:
        command_uuid = uuid.UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid command_id format")

    query = select(CommandHistory).where(CommandHistory.id == command_uuid)
    result = await session.execute(query)
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(command, key):
            setattr(command, key, value)

    await session.commit()
    await session.refresh(command)

    return CommandHistoryEntry.from_model(command).model_dump(by_alias=True, exclude_none=True)


@router.patch("/history/{command_id}/favorite")
async def toggle_command_favorite(
    command_id: str,
    request: ToggleFavoriteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Toggle favorite status of a command.

    Args:
        command_id: Command UUID
        request: Favorite status
        session: Database session

    Returns:
        Updated command record
    """
    try:
        command_uuid = uuid.UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid command_id format")

    query = select(CommandHistory).where(CommandHistory.id == command_uuid)
    result = await session.execute(query)
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    command.is_favorite = request.is_favorite
    await session.commit()
    await session.refresh(command)

    return CommandHistoryEntry.from_model(command).model_dump(by_alias=True, exclude_none=True)


@router.delete("/history/{command_id}")
async def delete_command(
    command_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete a command record.

    Args:
        command_id: Command UUID
        session: Database session

    Returns:
        Success message
    """
    try:
        command_uuid = uuid.UUID(command_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid command_id format")

    query = select(CommandHistory).where(CommandHistory.id == command_uuid)
    result = await session.execute(query)
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    await session.delete(command)
    await session.commit()

    return {"message": "Command deleted successfully"}


@router.get("/history/{project_id}/export")
async def export_command_history(
    project_id: str,
    status: CommandStatus | None = Query(None, description="Filter by command status"),
    is_favorite: bool | None = Query(None, description="Filter by favorite status"),
    format: str = Query("csv", description="Export format (csv)"),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Export command history to CSV.

    Args:
        project_id: Project UUID
        status: Optional filter by command status
        is_favorite: Optional filter by favorite status
        format: Export format (currently only CSV supported)
        session: Database session

    Returns:
        CSV file download
    """
    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Only CSV format is currently supported")

    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Verify project exists
    project_query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get command history
    query = select(CommandHistory).where(
        CommandHistory.project_id == project_uuid
    ).order_by(
        desc(CommandHistory.created_at)
    )

    # Apply filters
    if status:
        query = query.where(CommandHistory.status == status)

    if is_favorite is not None:
        query = query.where(CommandHistory.is_favorite == is_favorite)

    result = await session.execute(query)
    commands = result.scalars().all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "ID",
        "Command",
        "Status",
        "Result",
        "Error Message",
        "Exit Code",
        "Duration (ms)",
        "Is Favorite",
        "Template Name",
        "Session ID",
        "Created At",
        "Updated At",
    ])

    # Write rows
    for cmd in commands:
        writer.writerow([
            str(cmd.id),
            cmd.command,
            cmd.status.value,
            cmd.result or "",
            cmd.error_message or "",
            cmd.exit_code or "",
            cmd.duration_ms or "",
            cmd.is_favorite,
            cmd.template_name or "",
            cmd.session_id or "",
            cmd.created_at.isoformat() if cmd.created_at else "",
            cmd.updated_at.isoformat() if cmd.updated_at else "",
        ])

    # Prepare response
    output.seek(0)
    filename = f"command_history_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/stats/summary")
async def get_commands_summary(
    project_id: str | None = Query(None, description="Filter by project ID"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get command statistics summary.

    Args:
        project_id: Optional project ID filter
        session: Database session

    Returns:
        Command statistics
    """
    # Base query
    base_conditions = []
    if project_id:
        try:
            project_uuid = uuid.UUID(project_id)
            base_conditions.append(CommandHistory.project_id == project_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Total commands
    total_query = select(func.count()).select_from(
        select(CommandHistory).where(and_(*base_conditions)).subquery()
    )
    total_result = await session.execute(total_query)
    total_commands = total_result.scalar() or 0

    # Commands by status
    status_counts = {}
    for status in CommandStatus:
        status_query = select(func.count()).select_from(
            select(CommandHistory).where(
                and_(*base_conditions, CommandHistory.status == status)
            ).subquery()
        )
        status_result = await session.execute(status_query)
        status_counts[status.value] = status_result.scalar() or 0

    # Favorite commands count
    favorite_query = select(func.count()).select_from(
        select(CommandHistory).where(
            and_(*base_conditions, CommandHistory.is_favorite == True)
        ).subquery()
    )
    favorite_result = await session.execute(favorite_query)
    total_favorites = favorite_result.scalar() or 0

    # Commands in last 24 hours
    recent_threshold = datetime.now() - timedelta(hours=24)
    recent_query = select(func.count()).select_from(
        select(CommandHistory).where(
            and_(*base_conditions, CommandHistory.created_at >= recent_threshold)
        ).subquery()
    )
    recent_result = await session.execute(recent_query)
    recent_commands = recent_result.scalar() or 0

    # Average duration for completed commands
    avg_duration_query = select(func.avg(CommandHistory.duration_ms)).select_from(
        select(CommandHistory).where(
            and_(
                *base_conditions,
                CommandHistory.status == CommandStatus.COMPLETED,
                CommandHistory.duration_ms.isnot(None)
            )
        ).subquery()
    )
    avg_duration_result = await session.execute(avg_duration_query)
    avg_duration_ms = avg_duration_result.scalar() or 0

    return {
        "total_commands": total_commands,
        "by_status": status_counts,
        "total_favorites": total_favorites,
        "recent_commands_24h": recent_commands,
        "avg_duration_ms": round(avg_duration_ms, 2),
    }
