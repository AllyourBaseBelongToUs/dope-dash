"""Agent pool synchronization service.

This service bridges the in-memory AgentRegistry with the database-backed
AgentPoolService, ensuring detected agents are persisted and synchronized.

Features:
- Syncs detected agents from AgentRegistry to database
- Updates heartbeats and status periodically
- Handles registration of new detected agents
- Removes stale agents from the pool
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_

from app.models.agent_pool import AgentPool, PoolAgentStatus
from app.models.session import AgentType
from app.services.agent_registry import get_agent_registry, AgentStatus, RegisteredAgent
from app.services.agent_pool import get_agent_pool_service
from db.connection import get_db_session


logger = logging.getLogger(__name__)


class AgentPoolSyncService:
    """Service for synchronizing AgentRegistry to AgentPoolService.

    This service periodically syncs detected agents from the in-memory
    registry to the database-backed pool service.
    """

    def __init__(self, sync_interval_seconds: int = 60) -> None:
        """Initialize the sync service.

        Args:
            sync_interval_seconds: Interval between sync operations
        """
        self._sync_interval = sync_interval_seconds
        self._sync_task: asyncio.Task[None] | None = None

    async def start_sync(self) -> None:
        """Start the background synchronization loop."""
        if self._sync_task is not None:
            logger.warning("Agent pool sync already running")
            return

        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"Started agent pool sync service (interval: {self._sync_interval}s)")

    async def stop_sync(self) -> None:
        """Stop the background synchronization loop."""
        if self._sync_task is None:
            return

        self._sync_task.cancel()
        try:
            await self._sync_task
        except asyncio.CancelledError:
            pass
        self._sync_task = None
        logger.info("Stopped agent pool sync service")

    async def sync_once(self) -> dict[str, Any]:
        """Perform a single synchronization.

        Returns:
            Summary of sync operation
        """
        registry = get_agent_registry()
        detected_agents = registry.get_all_agents()

        added = 0
        updated = 0
        removed = 0

        async for session in get_db_session():
            try:
                # Get all existing agents from database
                result = await session.execute(
                    select(AgentPool).where(AgentPool.deleted_at.is_(None))
                )
                db_agents = {a.agent_id: a for a in result.scalars().all()}

                # Track which agent_ids we've seen
                seen_agent_ids: set[str] = set()

                # Sync detected agents to database
                for detected in detected_agents:
                    seen_agent_ids.add(detected.agent_id)

                    if detected.agent_id in db_agents:
                        # Update existing agent
                        db_agent = db_agents[detected.agent_id]

                        # Update status based on registry status
                        status_map = {
                            AgentStatus.REGISTERED: PoolAgentStatus.AVAILABLE,
                            AgentStatus.ACTIVE: PoolAgentStatus.AVAILABLE,
                            AgentStatus.IDLE: PoolAgentStatus.AVAILABLE,
                            AgentStatus.DISCONNECTED: PoolAgentStatus.OFFLINE,
                            AgentStatus.TERMINATED: PoolAgentStatus.OFFLINE,
                        }
                        db_agent.status = status_map.get(
                            detected.status, PoolAgentStatus.AVAILABLE
                        )

                        # Update heartbeat
                        if detected.last_heartbeat:
                            db_agent.last_heartbeat = detected.last_heartbeat.timestamp
                        else:
                            db_agent.last_heartbeat = datetime.now(timezone.utc)

                        # Update other fields
                        db_agent.pid = detected.pid
                        db_agent.working_dir = detected.working_dir
                        db_agent.command = detected.command
                        db_agent.tmux_session = detected.tmux_session

                        updated += 1
                    else:
                        # Register new agent
                        new_agent = AgentPool(
                            agent_id=detected.agent_id,
                            agent_type=detected.agent_type,
                            status=PoolAgentStatus.AVAILABLE,
                            pid=detected.pid,
                            working_dir=detected.working_dir,
                            command=detected.command,
                            tmux_session=detected.tmux_session,
                            last_heartbeat=datetime.now(timezone.utc),
                            current_load=0,
                            max_capacity=5,
                            capabilities=[c.name for c in detected.capabilities],
                            metadata=detected.metadata,
                        )
                        session.add(new_agent)
                        added += 1

                # Mark agents not in registry as offline (but don't delete)
                for agent_id, db_agent in db_agents.items():
                    if agent_id not in seen_agent_ids:
                        if db_agent.status != PoolAgentStatus.OFFLINE:
                            db_agent.status = PoolAgentStatus.OFFLINE
                            removed += 1

                await session.commit()

            except Exception as e:
                logger.error(f"Error during agent pool sync: {e}", exc_info=True)
                await session.rollback()
            break  # Only run once per call

        return {
            "added": added,
            "updated": updated,
            "removed": removed,
            "total_detected": len(detected_agents),
        }

    async def _sync_loop(self) -> None:
        """Background synchronization loop."""
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                result = await self.sync_once()
                logger.debug(
                    f"Agent pool sync completed: "
                    f"{result['added']} added, {result['updated']} updated, "
                    f"{result['removed']} marked offline"
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in agent pool sync loop: {e}", exc_info=True)


# Singleton instance
_agent_pool_sync_service: AgentPoolSyncService | None = None


def get_agent_pool_sync_service() -> AgentPoolSyncService:
    """Get the singleton agent pool sync service instance.

    Returns:
        AgentPoolSyncService instance
    """
    global _agent_pool_sync_service
    if _agent_pool_sync_service is None:
        _agent_pool_sync_service = AgentPoolSyncService()
    return _agent_pool_sync_service
