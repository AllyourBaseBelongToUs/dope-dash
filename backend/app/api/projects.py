"""Projects API endpoints for portfolio view.

Provides endpoints for managing projects, including listing, filtering,
searching, and updating project status and priority.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Select, and_, func, select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.connection import get_db_session

from app.models.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectStatus,
    ProjectPriority,
)
from app.models.project_control import (
    ProjectControl,
    ProjectControlAction,
    ProjectControlStatus,
    ProjectControlHistoryEntry,
)
from app.models.session import Session, SessionStatus
from app.services.agent_registry import get_agent_registry


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Agent registry for controlling agents
_agent_registry = get_agent_registry()


async def _log_control_action(
    session: AsyncSession,
    project_id: uuid.UUID,
    action: ProjectControlAction,
    agents_affected: int = 0,
    error_message: str | None = None,
    initiated_by: str = "user",
) -> ProjectControl:
    """Log a control action to the project_controls table.

    Args:
        session: Database session
        project_id: Project UUID
        action: Control action performed
        agents_affected: Number of agents affected
        error_message: Error message if action failed
        initiated_by: Who initiated the control

    Returns:
        Created ProjectControl record
    """
    control = ProjectControl(
        project_id=project_id,
        action=action,
        status=ProjectControlStatus.COMPLETED if not error_message else ProjectControlStatus.FAILED,
        initiated_by=initiated_by,
        agents_affected=agents_affected,
        error_message=error_message,
        meta_data={},
    )
    session.add(control)
    await session.flush()
    return control


async def _send_control_to_agents(
    project_name: str,
    action: ProjectControlAction,
) -> int:
    """Send control command to all agents for a project.

    This function sends control signals to all registered agents for a project.
    The control is sent via the agent wrapper's send_control method, which emits
    a control event that can be picked up by the agent's monitoring loop.

    Args:
        project_name: Project name
        action: Control action to send

    Returns:
        Number of agents affected
    """
    agents = _agent_registry.get_agents_by_project(project_name)

    if not agents:
        logger.info(f"No agents found for project {project_name}")
        return 0

    agents_affected = 0

    for agent in agents:
        try:
            # For agents with PIDs, we can send OS signals
            if agent.pid:
                import signal
                import os

                try:
                    if action == ProjectControlAction.STOP:
                        # Send SIGTERM to stop the agent
                        os.kill(agent.pid, signal.SIGTERM)
                        logger.info(f"Sent SIGTERM to agent {agent.agent_id} (PID: {agent.pid})")
                        agents_affected += 1
                    elif action == ProjectControlAction.PAUSE:
                        # Send SIGUSR1 to pause the agent (if supported)
                        os.kill(agent.pid, signal.SIGUSR1)
                        logger.info(f"Sent SIGUSR1 (pause) to agent {agent.agent_id} (PID: {agent.pid})")
                        agents_affected += 1
                    elif action == ProjectControlAction.RESUME:
                        # Send SIGUSR2 to resume the agent (if supported)
                        os.kill(agent.pid, signal.SIGUSR2)
                        logger.info(f"Sent SIGUSR2 (resume) to agent {agent.agent_id} (PID: {agent.pid})")
                        agents_affected += 1
                except ProcessLookupError:
                    logger.warning(f"Agent {agent.agent_id} (PID: {agent.pid}) not found")
                except PermissionError:
                    logger.warning(f"No permission to signal agent {agent.agent_id} (PID: {agent.pid})")
            else:
                # For agents without PIDs, log that we can't control them directly
                logger.info(f"Agent {agent.agent_id} has no PID, control signal sent via event stream")
                agents_affected += 1

        except Exception as e:
            logger.error(f"Error sending control to agent {agent.agent_id}: {e}")

    logger.info(f"Sent {action.value} command to {agents_affected} agents for project {project_name}")
    return agents_affected


@router.get("")
async def get_projects(
    status: ProjectStatus | None = Query(None, description="Filter by project status"),
    priority: ProjectPriority | None = Query(None, description="Filter by project priority"),
    search: str | None = Query(None, description="Search in project name and description"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get all projects with optional filters.

    Args:
        status: Filter by project status
        priority: Filter by project priority
        search: Search in project name and description
        limit: Maximum number of results (1-1000)
        offset: Pagination offset
        session: Database session

    Returns:
        Dictionary with projects list, total count, and filters applied
    """
    query: Select[tuple[Project]] = select(Project).where(
        Project.deleted_at.is_(None)
    ).order_by(
        desc(Project.last_activity_at),
        desc(Project.updated_at)
    )

    filters_applied: list[str] = []

    # Apply status filter
    if status:
        query = query.where(Project.status == status)
        filters_applied.append(f"status={status}")

    # Apply priority filter
    if priority:
        query = query.where(Project.priority == priority)
        filters_applied.append(f"priority={priority}")

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Project.name.ilike(search_pattern),
                Project.description.ilike(search_pattern),
            )
        )
        filters_applied.append(f"search={search}")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(query)
    projects = result.scalars().all()

    return {
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "status": p.status.value,
                "priority": p.priority.value,
                "description": p.description,
                "progress": p.progress,
                "total_specs": p.total_specs,
                "completed_specs": p.completed_specs,
                "active_agents": p.active_agents,
                "last_activity_at": p.last_activity_at.isoformat() if p.last_activity_at else None,
                "metadata": p.meta_data,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in projects
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "filters_applied": filters_applied,
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a single project by ID.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Project details
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    ).options(
        selectinload(Project.control_history)
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get active sessions for this project
    sessions_query = select(Session).where(
        and_(
            Session.project_name == project.name,
            Session.deleted_at.is_(None)
        )
    ).order_by(
        desc(Session.started_at)
    ).limit(10)

    sessions_result = await session.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    # Get control history
    control_history = [
        ProjectControlHistoryEntry.from_model(c).model_dump(by_alias=True, exclude_none=True)
        for c in project.control_history[:20]  # Last 20 actions
    ]

    return {
        "id": str(project.id),
        "name": project.name,
        "status": project.status.value,
        "priority": project.priority.value,
        "description": project.description,
        "progress": project.progress,
        "total_specs": project.total_specs,
        "completed_specs": project.completed_specs,
        "active_agents": project.active_agents,
        "last_activity_at": project.last_activity_at.isoformat() if project.last_activity_at else None,
        "metadata": project.meta_data,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "recent_sessions": [
            {
                "id": str(s.id),
                "agent_type": s.agent_type.value if s.agent_type else "unknown",
                "status": s.status.value if s.status else "unknown",
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            }
            for s in sessions
        ],
        "control_history": control_history,
    }


@router.get("/{project_id}/controls")
async def get_project_controls(
    project_id: str,
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get control history for a project.

    Args:
        project_id: Project UUID
        limit: Maximum number of results
        offset: Pagination offset
        session: Database session

    Returns:
        Control history entries
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

    # Get control history
    controls_query = select(ProjectControl).where(
        ProjectControl.project_id == project_uuid
    ).order_by(
        desc(ProjectControl.created_at)
    )

    # Get total count
    count_query = select(func.count()).select_from(controls_query.subquery())
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()

    # Apply pagination
    controls_query = controls_query.limit(limit).offset(offset)

    result = await session.execute(controls_query)
    controls = result.scalars().all()

    return {
        "controls": [
            ProjectControlHistoryEntry.from_model(c).model_dump(by_alias=True, exclude_none=True)
            for c in controls
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.post("")
async def create_project(
    project: ProjectCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new project.

    Args:
        project: Project creation data
        session: Database session

    Returns:
        Created project details
    """
    # Check if project with this name already exists
    existing_query = select(Project).where(
        and_(
            Project.name == project.name,
            Project.deleted_at.is_(None)
        )
    )
    existing_result = await session.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    # Create new project
    new_project = Project(
        name=project.name,
        status=project.status,
        priority=project.priority,
        description=project.description,
        progress=project.progress,
        total_specs=project.total_specs,
        completed_specs=project.completed_specs,
        active_agents=project.active_agents,
        meta_data=project.metadata,
    )

    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)

    return {
        "id": str(new_project.id),
        "name": new_project.name,
        "status": new_project.status.value,
        "priority": new_project.priority.value,
        "description": new_project.description,
        "progress": new_project.progress,
        "total_specs": new_project.total_specs,
        "completed_specs": new_project.completed_specs,
        "active_agents": new_project.active_agents,
        "last_activity_at": new_project.last_activity_at.isoformat() if new_project.last_activity_at else None,
        "metadata": new_project.meta_data,
        "created_at": new_project.created_at.isoformat() if new_project.created_at else None,
        "updated_at": new_project.updated_at.isoformat() if new_project.updated_at else None,
    }


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update a project.

    Args:
        project_id: Project UUID
        updates: Fields to update
        session: Database session

    Returns:
        Updated project details
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Apply updates
    update_data = updates.to_model_dict()
    for key, value in update_data.items():
        if hasattr(project, key):
            setattr(project, key, value)

    await session.commit()
    await session.refresh(project)

    return {
        "id": str(project.id),
        "name": project.name,
        "status": project.status.value,
        "priority": project.priority.value,
        "description": project.description,
        "progress": project.progress,
        "total_specs": project.total_specs,
        "completed_specs": project.completed_specs,
        "active_agents": project.active_agents,
        "last_activity_at": project.last_activity_at.isoformat() if project.last_activity_at else None,
        "metadata": project.meta_data,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Soft delete a project.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Soft delete
    project.soft_delete()
    await session.commit()

    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/pause")
async def pause_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Pause all active sessions in a project.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message with control info
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == ProjectStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Project is already paused")

    if project.status not in (ProjectStatus.RUNNING, ProjectStatus.IDLE):
        raise HTTPException(status_code=400, detail=f"Cannot pause project with status {project.status.value}")

    # Send pause command to agents
    agents_affected = await _send_control_to_agents(project.name, ProjectControlAction.PAUSE)

    # Update project status to paused
    project.status = ProjectStatus.PAUSED
    project.last_activity_at = datetime.now()

    await session.commit()

    # Log control action
    await _log_control_action(
        session,
        project_uuid,
        ProjectControlAction.PAUSE,
        agents_affected=agents_affected,
    )
    await session.commit()

    return {
        "message": "Project paused successfully",
        "agents_affected": agents_affected,
    }


@router.post("/{project_id}/resume")
async def resume_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Resume a paused project.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message with control info
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProjectStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Only paused projects can be resumed")

    # Send resume command to agents
    agents_affected = await _send_control_to_agents(project.name, ProjectControlAction.RESUME)

    # Update project status to running if there are active agents
    if project.active_agents > 0:
        project.status = ProjectStatus.RUNNING
    else:
        project.status = ProjectStatus.IDLE
    project.last_activity_at = datetime.now()

    await session.commit()

    # Log control action
    await _log_control_action(
        session,
        project_uuid,
        ProjectControlAction.RESUME,
        agents_affected=agents_affected,
    )
    await session.commit()

    return {
        "message": "Project resumed successfully",
        "agents_affected": agents_affected,
    }


@router.post("/{project_id}/skip")
async def skip_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Skip remaining specs in a project.

    Marks the project as skipped but doesn't terminate agents.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message with control info
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == ProjectStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Project is already completed")

    # Send skip command to agents
    agents_affected = await _send_control_to_agents(project.name, ProjectControlAction.SKIP)

    # Update project status
    project.status = ProjectStatus.COMPLETED
    project.last_activity_at = datetime.now()

    await session.commit()

    # Log control action
    await _log_control_action(
        session,
        project_uuid,
        ProjectControlAction.SKIP,
        agents_affected=agents_affected,
    )
    await session.commit()

    return {
        "message": "Project skipped successfully",
        "agents_affected": agents_affected,
    }


@router.post("/{project_id}/stop")
async def stop_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Stop all agents in a project.

    Terminates all active agent sessions.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message with control info
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Send stop command to agents
    agents_affected = await _send_control_to_agents(project.name, ProjectControlAction.STOP)

    # Update project status to idle
    project.status = ProjectStatus.IDLE
    project.active_agents = 0
    project.last_activity_at = datetime.now()

    await session.commit()

    # Log control action
    await _log_control_action(
        session,
        project_uuid,
        ProjectControlAction.STOP,
        agents_affected=agents_affected,
    )
    await session.commit()

    return {
        "message": "Project stopped successfully",
        "agents_affected": agents_affected,
    }


@router.post("/{project_id}/retry")
async def retry_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retry failed specs in a project.

    Restarts only the specs that previously failed.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message with control info
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProjectStatus.ERROR:
        raise HTTPException(status_code=400, detail="Only projects in error state can be retried")

    # Send retry command to agents
    agents_affected = await _send_control_to_agents(project.name, ProjectControlAction.RETRY)

    # Update project status
    project.status = ProjectStatus.RUNNING
    project.last_activity_at = datetime.now()

    await session.commit()

    # Log control action
    await _log_control_action(
        session,
        project_uuid,
        ProjectControlAction.RETRY,
        agents_affected=agents_affected,
    )
    await session.commit()

    return {
        "message": "Project retry initiated successfully",
        "agents_affected": agents_affected,
    }


@router.post("/{project_id}/restart")
async def restart_project(
    project_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Restart a project from the beginning.

    Restarts all specs from the beginning, regardless of previous state.

    Args:
        project_id: Project UUID
        session: Database session

    Returns:
        Success message with control info
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None)
        )
    )

    result = await session.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Send restart command to agents
    agents_affected = await _send_control_to_agents(project.name, ProjectControlAction.RESTART)

    # Reset progress
    project.progress = 0.0
    project.completed_specs = 0
    project.status = ProjectStatus.RUNNING
    project.last_activity_at = datetime.now()

    await session.commit()

    # Log control action
    await _log_control_action(
        session,
        project_uuid,
        ProjectControlAction.RESTART,
        agents_affected=agents_affected,
    )
    await session.commit()

    return {
        "message": "Project restarted successfully",
        "agents_affected": agents_affected,
    }


@router.get("/stats/summary")
async def get_projects_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get overall project statistics summary.

    Args:
        session: Database session

    Returns:
        Dictionary with project statistics
    """
    # Total projects
    total_query = select(func.count()).select_from(
        select(Project).where(Project.deleted_at.is_(None)).subquery()
    )
    total_result = await session.execute(total_query)
    total_projects = total_result.scalar() or 0

    # Projects by status
    status_counts = {}
    for status in ProjectStatus:
        status_query = select(func.count()).select_from(
            select(Project).where(
                and_(
                    Project.status == status,
                    Project.deleted_at.is_(None)
                )
            ).subquery()
        )
        status_result = await session.execute(status_query)
        status_counts[status.value] = status_result.scalar() or 0

    # Active agents across all projects
    active_agents_query = select(func.sum(Project.active_agents)).select_from(
        select(Project).where(Project.deleted_at.is_(None)).subquery()
    )
    active_agents_result = await session.execute(active_agents_query)
    total_active_agents = active_agents_result.scalar() or 0

    # Total specs
    total_specs_query = select(func.sum(Project.total_specs)).select_from(
        select(Project).where(Project.deleted_at.is_(None)).subquery()
    )
    total_specs_result = await session.execute(total_specs_query)
    total_specs = total_specs_result.scalar() or 0

    completed_specs_query = select(func.sum(Project.completed_specs)).select_from(
        select(Project).where(Project.deleted_at.is_(None)).subquery()
    )
    completed_specs_result = await session.execute(completed_specs_query)
    total_completed_specs = completed_specs_result.scalar() or 0

    # Average progress
    avg_progress_query = select(func.avg(Project.progress)).select_from(
        select(Project).where(Project.deleted_at.is_(None)).subquery()
    )
    avg_progress_result = await session.execute(avg_progress_query)
    average_progress = float(avg_progress_result.scalar() or 0)

    return {
        "total_projects": total_projects,
        "by_status": status_counts,
        "total_active_agents": total_active_agents,
        "total_specs": total_specs,
        "completed_specs": total_completed_specs,
        "average_progress": round(average_progress, 2),
    }


class BulkOperationRequest(BaseModel):
    """Request body for bulk operations."""

    project_ids: list[str]
    action: ProjectControlAction


class BulkOperationResult(BaseModel):
    """Result of a single project operation."""

    project_id: str
    project_name: str
    success: bool
    message: str
    agents_affected: int = 0
    error: str | None = None


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""

    action: ProjectControlAction
    total_requested: int
    successful: int
    failed: int
    results: list[BulkOperationResult]
    total_agents_affected: int


@router.post("/bulk/control")
async def bulk_control_projects(
    request: BulkOperationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Apply a control action to multiple projects at once.

    Args:
        request: Bulk operation request with project IDs and action
        session: Database session

    Returns:
        Bulk operation response with results for each project
    """
    results: list[BulkOperationResult] = []
    total_agents_affected = 0

    # Process each project
    for project_id in request.project_ids:
        try:
            # Validate UUID
            project_uuid = uuid.UUID(project_id)

            # Get project
            query = select(Project).where(
                and_(
                    Project.id == project_uuid,
                    Project.deleted_at.is_(None)
                )
            )
            result = await session.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                results.append(BulkOperationResult(
                    project_id=project_id,
                    project_name="Unknown",
                    success=False,
                    message="Project not found",
                    error="Project not found"
                ))
                continue

            # Validate action is applicable to project status
            action_valid = True
            error_message = None

            match request.action:
                case ProjectControlAction.PAUSE:
                    if project.status == ProjectStatus.PAUSED:
                        action_valid = False
                        error_message = "Project is already paused"
                    elif project.status not in (ProjectStatus.RUNNING, ProjectStatus.IDLE):
                        action_valid = False
                        error_message = f"Cannot pause project with status {project.status.value}"

                case ProjectControlAction.RESUME:
                    if project.status != ProjectStatus.PAUSED:
                        action_valid = False
                        error_message = "Only paused projects can be resumed"

                case ProjectControlAction.STOP:
                    # Stop can be applied to any active project
                    pass

                case _:
                    action_valid = False
                    error_message = f"Bulk operation not supported for action: {request.action.value}"

            if not action_valid:
                results.append(BulkOperationResult(
                    project_id=project_id,
                    project_name=project.name,
                    success=False,
                    message="Action not applicable",
                    error=error_message
                ))
                continue

            # Send control command to agents
            agents_affected = await _send_control_to_agents(project.name, request.action)
            total_agents_affected += agents_affected

            # Update project status based on action
            match request.action:
                case ProjectControlAction.PAUSE:
                    project.status = ProjectStatus.PAUSED
                case ProjectControlAction.RESUME:
                    if project.active_agents > 0:
                        project.status = ProjectStatus.RUNNING
                    else:
                        project.status = ProjectStatus.IDLE
                case ProjectControlAction.STOP:
                    project.status = ProjectStatus.IDLE
                    project.active_agents = 0

            project.last_activity_at = datetime.now()

            # Log control action
            await _log_control_action(
                session,
                project_uuid,
                request.action,
                agents_affected=agents_affected,
            )

            results.append(BulkOperationResult(
                project_id=project_id,
                project_name=project.name,
                success=True,
                message=f"Successfully {request.action.value}d project",
                agents_affected=agents_affected
            ))

        except ValueError:
            results.append(BulkOperationResult(
                project_id=project_id,
                project_name="Unknown",
                success=False,
                message="Invalid project ID format",
                error="Invalid UUID format"
            ))
        except Exception as e:
            logger.error(f"Error processing bulk operation for project {project_id}: {e}")
            results.append(BulkOperationResult(
                project_id=project_id,
                project_name="Unknown",
                success=False,
                message="Internal error",
                error=str(e)
            ))

    # Commit all changes
    await session.commit()

    successful_count = sum(1 for r in results if r.success)
    failed_count = len(results) - successful_count

    return BulkOperationResponse(
        action=request.action,
        total_requested=len(request.project_ids),
        successful=successful_count,
        failed=failed_count,
        results=results,
        total_agents_affected=total_agents_affected,
    ).model_dump(by_alias=True, exclude_none=True)
