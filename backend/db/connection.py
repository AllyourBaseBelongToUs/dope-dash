"""Database connection pool and session management.

This module provides a centralized database connection pool that handles
20+ concurrent connections with proper async support.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings


class DatabaseConnectionManager:
    """Manages database connection pool and sessions.

    Features:
    - Connection pooling with configurable size
    - Support for 20+ concurrent connections
    - Automatic connection recycling
    - Graceful shutdown handling
    """

    def __init__(self) -> None:
        """Initialize the database connection manager."""
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine.

        Raises:
            RuntimeError: If engine has not been initialized.
        """
        if self._engine is None:
            raise RuntimeError(
                "Database engine not initialized. Call init_db() first."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory.

        Raises:
            RuntimeError: If session factory has not been initialized.
        """
        if self._session_factory is None:
            raise RuntimeError(
                "Session factory not initialized. Call init_db() first."
            )
        return self._session_factory

    def init_db(self, *, pool_pre_ping: bool = True, testing: bool = False) -> None:
        """Initialize the database connection pool.

        Args:
            pool_pre_ping: Enable connection health checks before use.
            testing: If True, use NullPool for testing (no connection pooling).

        Raises:
            RuntimeError: If database is already initialized.
        """
        if self._engine is not None:
            raise RuntimeError("Database already initialized.")

        # Configure engine based on environment
        engine_params: dict[str, Any] = {
            "echo": settings.database_echo,
            "future": True,
        }

        if testing:
            # Use NullPool for tests - connections are closed after each use
            engine_params["poolclass"] = NullPool
        else:
            # Use default async pool for production (AsyncAdaptedQueuePool is automatic)
            engine_params.update(
                {
                    "pool_size": settings.db_pool_size,  # Default: 20
                    "max_overflow": settings.db_max_overflow,  # Default: 10
                    "pool_timeout": settings.db_pool_timeout,  # Default: 30s
                    "pool_recycle": settings.db_pool_recycle,  # Default: 1 hour
                    "pool_pre_ping": pool_pre_ping,
                }
            )

        self._engine = create_async_engine(
            settings.database_url,
            **engine_params,
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def close_db(self) -> None:
        """Close the database connection pool.

        This should be called during application shutdown to properly
        close all connections.
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session from the pool.

        Yields:
            AsyncSession: A database session.

        Example:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
        """
        if self._session_factory is None:
            raise RuntimeError(
                "Session factory not initialized. Call init_db() first."
            )

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """Get a raw database connection from the pool.

        This is useful for operations that don't require a full session,
        such as bulk inserts or DDL operations.

        Yields:
            AsyncConnection: A raw database connection.
        """
        if self._engine is None:
            raise RuntimeError("Database engine not initialized. Call init_db() first.")

        async with self._engine.connect() as conn:
            yield conn

    async def health_check(self) -> bool:
        """Check if database connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise.
        """
        try:
            async with self.get_connection() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False


# Global database manager instance
db_manager = DatabaseConnectionManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for FastAPI endpoints.

    Yields:
        AsyncSession: A database session.

    Example:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(User))
    """
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """Initialize the database connection pool.

    This should be called during application startup.
    """
    db_manager.init_db()


async def close_database() -> None:
    """Close the database connection pool.

    This should be called during application shutdown.
    """
    await db_manager.close_db()
