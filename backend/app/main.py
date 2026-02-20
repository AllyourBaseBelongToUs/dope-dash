"""FastAPI application for Dope Dash API.

This application provides the REST API for the Dope Dash dashboard,
including endpoints for managing agent sessions, events, and metrics.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiohttp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from db.connection import db_manager, get_db_session


# Global references for background tasks
_queue_processor_task = None
_http_session = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events for the application,
    including database connection management, scheduled reports,
    and request queue processing.
    """
    global _queue_processor_task, _http_session

    # Startup: Initialize database connection pool
    try:
        db_manager.init_db()
        print(f"✓ Database connection pool initialized (pool_size={settings.db_pool_size})")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        raise

    # Start the background scheduler for scheduled reports
    try:
        from app.lib.scheduler import start_scheduler
        start_scheduler()
        print("✓ Background scheduler started for scheduled reports")
    except Exception as e:
        print(f"⚠ Failed to start scheduler: {e}")

    # Start the request queue processor
    try:
        from app.services.request_queue import RequestQueueService

        # Create HTTP session for queue processor
        _http_session = aiohttp.ClientSession()

        async def start_queue_processor():
            """Start the queue processor with a database session."""
            async for session in get_db_session():
                service = RequestQueueService(session)
                global _queue_processor_task
                _queue_processor_task = await service.start_queue_processor(
                    http_session_factory=lambda: _http_session
                )
                break  # Only start once

        await start_queue_processor()
        print("✓ Request queue processor started")
    except Exception as e:
        print(f"⚠ Failed to start queue processor: {e}")

    yield

    # Shutdown: Close database connection pool, stop scheduler, and stop queue processor
    try:
        if _queue_processor_task:
            _queue_processor_task.cancel()
            try:
                await _queue_processor_task
            except Exception:
                pass  # Task was cancelled
            print("✓ Request queue processor stopped")
    except Exception as e:
        print(f"⚠ Error stopping queue processor: {e}")

    try:
        from app.lib.scheduler import stop_scheduler
        stop_scheduler()
        print("✓ Background scheduler stopped")
    except Exception as e:
        print(f"⚠ Error stopping scheduler: {e}")

    try:
        if _http_session:
            await _http_session.close()
            print("✓ HTTP session closed")
    except Exception as e:
        print(f"⚠ Error closing HTTP session: {e}")

    try:
        await db_manager.close_db()
        print("✓ Database connection pool closed")
    except Exception as e:
        print(f"✗ Error closing database: {e}")


# Create FastAPI application with lifespan handler
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns the health status of the application and its dependencies.
    """
    # Check database connection
    db_healthy = await db_manager.health_check()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "connected" if db_healthy else "disconnected",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Dope Dash API",
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_url": "/health",
    }


# Include API routers (Core API only - Port 8000)
# Note: analytics router handled by analytics service (port 8004)
# Note: commands router handled by control service (port 8002)
from app.api.query import router as query_router
from app.api.reports import router as reports_router
from app.api.retention import router as retention_router
from app.api.portfolio import router as portfolio_router
from app.api.projects import router as projects_router
from app.api.request_queue import router as request_queue_router
from app.api.agent_pool import router as agent_pool_router
from app.api.quota import router as quota_router

app.include_router(query_router)
app.include_router(reports_router)
app.include_router(retention_router)
app.include_router(portfolio_router)
app.include_router(projects_router)
app.include_router(request_queue_router)
app.include_router(agent_pool_router)
app.include_router(quota_router)
