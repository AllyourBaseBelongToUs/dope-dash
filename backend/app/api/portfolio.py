"""Portfolio API endpoints for project management.

Provides endpoints for managing projects in the portfolio view,
including CRUD operations, filtering, and search functionality.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db_session

from app.models.project import Project, ProjectStatus, ProjectPriority
from app.models.session import Session, SessionStatus


router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/projects")
async def get_projects(
    status: ProjectStatus | None = Query(None, description="Filter by project status"),
    priority: ProjectPriority | None = Query(None, description="Filter by project priority"),
    search: str | None = Query(None, description="Search in project name and description"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of projects to return"),
    offset: int = Query(0, ge=0, description="Number of projects to skip"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get all projects with optional filtering and search.

    Args:
        status: Optional filter by project status
        priority: Optional filter by project priority
        search: Optional search term for name/description
        limit: Maximum number of results
        offset: Number of results to skip
        session: Database session

    Returns:
        Dictionary with projects list and metadata
    """
    # Build base query - exclude soft-deleted projects
    conditions = [Project.deleted_at.is_(None)]

    if status:
        conditions.append(Project.status == status)

    if priority:
        conditions.append(Project.priority == priority)

    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Project.name.ilike(search_pattern),
                Project.description.ilike(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).where(and_(*conditions))
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get projects with pagination
    projects_query = select(Project).where(
        and_(*conditions)
    ).order_by(
        desc(Project.last_activity_at),
        desc(Project.updated_at),
    ).limit(limit).offset(offset)

    projects_result = await session.execute(projects_query)
    projects = projects_result.scalars().all()

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
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "metadata": p.meta_data,
            }
            for p in projects
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get detailed information about a single project.

    Args:
        project_id: Project UUID
        db_session: Database session

    Returns:
        Dictionary with project details and related sessions
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Get project
    project_query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None),
        )
    )
    project_result = await db_session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get related sessions
    sessions_query = select(Session).where(
        Session.project_name == project.name
    ).order_by(
        desc(Session.started_at)
    ).limit(10)

    sessions_result = await db_session.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    # Get session stats
    total_sessions_query = select(func.count()).where(
        Session.project_name == project.name
    )
    total_sessions_result = await db_session.execute(total_sessions_query)
    total_sessions = total_sessions_result.scalar() or 0

    # Get active sessions count
    active_sessions_query = select(func.count()).where(
        and_(
            Session.project_name == project.name,
            Session.status == SessionStatus.RUNNING,
        )
    )
    active_sessions_result = await db_session.execute(active_sessions_query)
    active_sessions = active_sessions_result.scalar() or 0

    # Get recent sessions with basic info
    recent_sessions = []
    for s in sessions:
        recent_sessions.append({
            "id": str(s.id),
            "agent_type": s.agent_type.value,
            "status": s.status.value,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

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
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "metadata": project.meta_data,
        "stats": {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
        },
        "recent_sessions": recent_sessions,
    }


@router.post("/projects")
async def create_project(
    project_data: dict[str, Any],
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new project.

    Args:
        project_data: Project creation data
        db_session: Database session

    Returns:
        Created project data
    """
    name = project_data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    # Check if project with this name already exists
    existing_query = select(Project).where(
        and_(
            Project.name == name,
            Project.deleted_at.is_(None),
        )
    )
    existing_result = await db_session.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    # Create project
    project = Project(
        name=name,
        status=ProjectStatus(project_data.get("status", "idle")),
        priority=ProjectPriority(project_data.get("priority", "medium")),
        description=project_data.get("description"),
        progress=project_data.get("progress", 0.0),
        total_specs=project_data.get("total_specs", 0),
        completed_specs=project_data.get("completed_specs", 0),
        active_agents=project_data.get("active_agents", 0),
        meta_data=project_data.get("metadata", {}),
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

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
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "metadata": project.meta_data,
    }


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    project_data: dict[str, Any],
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update an existing project.

    Args:
        project_id: Project UUID
        project_data: Project update data
        db_session: Database session

    Returns:
        Updated project data
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Get project
    project_query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None),
        )
    )
    project_result = await db_session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields
    if "status" in project_data:
        project.status = ProjectStatus(project_data["status"])

    if "priority" in project_data:
        project.priority = ProjectPriority(project_data["priority"])

    if "description" in project_data:
        project.description = project_data["description"]

    if "progress" in project_data:
        project.progress = project_data["progress"]

    if "total_specs" in project_data:
        project.total_specs = project_data["total_specs"]

    if "completed_specs" in project_data:
        project.completed_specs = project_data["completed_specs"]

    if "active_agents" in project_data:
        project.active_agents = project_data["active_agents"]

    if "last_activity_at" in project_data:
        if project_data["last_activity_at"]:
            project.last_activity_at = datetime.fromisoformat(project_data["last_activity_at"])
        else:
            project.last_activity_at = None

    if "metadata" in project_data:
        project.meta_data = project_data["metadata"]

    await db_session.commit()
    await db_session.refresh(project)

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
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "metadata": project.meta_data,
    }


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Soft delete a project.

    Args:
        project_id: Project UUID
        db_session: Database session

    Returns:
        Confirmation message
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Get project
    project_query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None),
        )
    )
    project_result = await db_session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Soft delete
    project.soft_delete()
    await db_session.commit()

    return {"message": "Project deleted successfully", "id": str(project.id)}


@router.get("/summary")
async def get_portfolio_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get overall portfolio summary statistics.

    Args:
        session: Database session

    Returns:
        Dictionary with portfolio statistics
    """
    # Get total projects (excluding soft-deleted)
    total_projects_query = select(func.count()).where(Project.deleted_at.is_(None))
    total_projects_result = await session.execute(total_projects_query)
    total_projects = total_projects_result.scalar() or 0

    # Get projects by status
    projects_by_status_query = select(
        Project.status,
        func.count().label("count")
    ).where(
        Project.deleted_at.is_(None)
    ).group_by(Project.status)

    projects_by_status_result = await session.execute(projects_by_status_query)
    projects_by_status = {row.status.value: row.count for row in projects_by_status_result.all()}

    # Get projects by priority
    projects_by_priority_query = select(
        Project.priority,
        func.count().label("count")
    ).where(
        Project.deleted_at.is_(None)
    ).group_by(Project.priority)

    projects_by_priority_result = await session.execute(projects_by_priority_query)
    projects_by_priority = {row.priority.value: row.count for row in projects_by_priority_result.all()}

    # Get total active agents across all projects
    total_active_agents_query = select(func.sum(Project.active_agents)).where(
        Project.deleted_at.is_(None)
    )
    total_active_agents_result = await session.execute(total_active_agents_query)
    total_active_agents = total_active_agents_result.scalar() or 0

    # Get average progress across all projects
    avg_progress_query = select(func.avg(Project.progress)).where(
        Project.deleted_at.is_(None)
    )
    avg_progress_result = await session.execute(avg_progress_query)
    avg_progress = avg_progress_result.scalar() or 0

    # Get total specs across all projects
    total_specs_query = select(func.sum(Project.total_specs)).where(
        Project.deleted_at.is_(None)
    )
    total_specs_result = await session.execute(total_specs_query)
    total_specs = total_specs_result.scalar() or 0

    # Get completed specs across all projects
    completed_specs_query = select(func.sum(Project.completed_specs)).where(
        Project.deleted_at.is_(None)
    )
    completed_specs_result = await session.execute(completed_specs_query)
    completed_specs = completed_specs_result.scalar() or 0

    # Get recently active projects (last activity in last 24 hours)
    recent_activity_threshold = datetime.now() - timedelta(hours=24)
    recent_projects_query = select(func.count()).where(
        and_(
            Project.deleted_at.is_(None),
            Project.last_activity_at >= recent_activity_threshold,
        )
    )
    recent_projects_result = await session.execute(recent_projects_query)
    recent_active_projects = recent_projects_result.scalar() or 0

    return {
        "total_projects": total_projects,
        "projects_by_status": projects_by_status,
        "projects_by_priority": projects_by_priority,
        "total_active_agents": total_active_agents,
        "avg_progress": round(avg_progress, 2),
        "total_specs": total_specs,
        "completed_specs": completed_specs,
        "overall_completion_rate": round(completed_specs / total_specs, 2) if total_specs > 0 else 0,
        "recent_active_projects": recent_active_projects,
    }


@router.post("/projects/{project_id}/sync")
async def sync_project_from_sessions(
    project_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Sync project data from related sessions.

    This endpoint updates project stats based on actual session data.
    Useful for keeping the portfolio view in sync with real activity.

    Args:
        project_id: Project UUID
        db_session: Database session

    Returns:
        Updated project data
    """
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    # Get project
    project_query = select(Project).where(
        and_(
            Project.id == project_uuid,
            Project.deleted_at.is_(None),
        )
    )
    project_result = await db_session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get session stats for this project
    sessions_query = select(Session).where(Session.project_name == project.name)
    sessions_result = await db_session.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    # Calculate stats
    active_agents = sum(1 for s in sessions if s.status == SessionStatus.RUNNING)
    total_specs = sum(s.meta_data.get("specs", {}).get("total", 0) for s in sessions)
    completed_specs = sum(s.meta_data.get("specs", {}).get("completed", 0) for s in sessions)

    # Get last activity
    last_activity = None
    if sessions:
        last_activity = max(
            (s.last_heartbeat or s.updated_at or s.created_at for s in sessions),
            default=None,
        )

    # Determine project status
    if active_agents > 0:
        new_status = ProjectStatus.RUNNING
    elif any(s.status == SessionStatus.FAILED for s in sessions):
        new_status = ProjectStatus.ERROR
    elif completed_specs >= total_specs and total_specs > 0:
        new_status = ProjectStatus.COMPLETED
    else:
        new_status = ProjectStatus.IDLE

    # Update project
    project.active_agents = active_agents
    project.total_specs = total_specs
    project.completed_specs = completed_specs
    project.last_activity_at = last_activity
    project.progress = completed_specs / total_specs if total_specs > 0 else 0
    project.status = new_status

    await db_session.commit()
    await db_session.refresh(project)

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
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "metadata": project.meta_data,
    }
