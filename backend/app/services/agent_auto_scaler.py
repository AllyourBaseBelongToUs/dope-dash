"""Agent auto-scaler service for dynamic pool management.

This service provides:
- Scaling recommendation based on pool metrics
- Scaling event tracking and history
- Auto-scaling monitoring loop
- Configurable scaling policies
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_pool import (
    AgentPool,
    PoolAgentStatus,
    ScalingAction,
    ScalingPolicy,
    ScalingRecommendation,
    PoolMetrics,
)
from app.services.agent_pool import get_agent_pool_service


logger = logging.getLogger(__name__)


@dataclass
class ScalingEvent:
    """Record of a scaling action that was taken.

    Attributes:
        id: Unique event identifier
        action: Type of scaling action
        previous_count: Number of agents before scaling
        new_count: Number of agents after scaling
        reason: Human-readable reason for scaling
        metadata: Additional event metadata
        created_at: When the event occurred
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    action: ScalingAction = ScalingAction.NO_OP
    previous_count: int = 0
    new_count: int = 0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentAutoScaler:
    """Auto-scaler service for agent pool management.

    This service monitors pool metrics and makes scaling recommendations
    based on configurable policies. It can run in monitoring mode to
    automatically execute scaling actions.
    """

    def __init__(self, policy: ScalingPolicy | None = None) -> None:
        """Initialize the auto-scaler.

        Args:
            policy: Scaling policy configuration (uses default if not provided)
        """
        self._policy = policy or ScalingPolicy()
        self._pool_service = get_agent_pool_service()
        self._monitoring = False
        self._monitor_task: asyncio.Task[None] | None = None
        self._scaling_history: list[ScalingEvent] = []
        self._last_scale_up: datetime | None = None
        self._last_scale_down: datetime | None = None

    def set_policy(self, policy: ScalingPolicy) -> None:
        """Update the scaling policy.

        Args:
            policy: New scaling policy
        """
        self._policy = policy
        logger.info(f"Updated scaling policy: {policy}")

    def get_policy(self) -> ScalingPolicy:
        """Get the current scaling policy.

        Returns:
            Current scaling policy
        """
        return self._policy

    async def get_scaling_recommendation(
        self,
        session: AsyncSession,
    ) -> ScalingRecommendation:
        """Get a scaling recommendation based on current pool metrics.

        Args:
            session: Database session

        Returns:
            Scaling recommendation with action and reason
        """
        metrics = await self._pool_service.get_pool_metrics(session)

        action = ScalingAction.NO_OP
        reason = "Pool is healthy"
        recommended_count = metrics.total_agents
        delta = 0

        # Check if we need to scale up
        if (
            metrics.utilization_percent >= self._policy.scale_up_threshold
            and metrics.total_agents < self._policy.max_agents
        ):
            action = ScalingAction.SCALE_UP
            # Calculate how many agents to add (aim for 60% utilization)
            target_capacity = int(metrics.used_capacity / 0.6)
            target_agents = max(self._policy.min_agents, target_capacity)
            recommended_count = min(self._policy.max_agents, target_agents)
            delta = recommended_count - metrics.total_agents
            reason = f"High utilization ({metrics.utilization_percent:.1f}%), recommend adding {delta} agent(s)"

        # Check if we need to scale down
        elif (
            metrics.utilization_percent <= self._policy.scale_down_threshold
            and metrics.total_agents > self._policy.min_agents
        ):
            action = ScalingAction.SCALE_DOWN
            # Calculate how many agents to remove (aim for 60% utilization)
            target_capacity = int(metrics.used_capacity / 0.6)
            target_agents = max(self._policy.min_agents, target_capacity)
            recommended_count = max(self._policy.min_agents, target_agents)
            delta = metrics.total_agents - recommended_count
            reason = f"Low utilization ({metrics.utilization_percent:.1f}%), recommend removing {delta} agent(s)"

        # Check for offline agents that need replacement
        elif metrics.offline_agents > 0:
            action = ScalingAction.SCALE_UP
            recommended_count = metrics.total_agents + metrics.offline_agents
            delta = metrics.offline_agents
            reason = f"Replace {metrics.offline_agents} offline agent(s)"

        return ScalingRecommendation(
            action=action,
            current_count=metrics.total_agents,
            recommended_count=recommended_count,
            delta=delta,
            reason=reason,
            metrics=metrics,
        )

    async def execute_scaling(
        self,
        session: AsyncSession,
        recommendation: ScalingRecommendation,
    ) -> ScalingEvent:
        """Execute a scaling action based on recommendation.

        Note: This method records the scaling event but does not actually
        spawn or terminate agents. The actual agent lifecycle management
        is handled by the agent factory/registry.

        Args:
            session: Database session
            recommendation: Scaling recommendation to execute

        Returns:
            Scaling event record
        """
        now = datetime.now(timezone.utc)
        event = ScalingEvent(
            action=recommendation.action,
            previous_count=recommendation.current_count,
            new_count=recommendation.recommended_count,
            reason=recommendation.reason,
            metadata={
                "metrics": recommendation.metrics.model_dump(),
                "policy": self._policy.model_dump(),
            },
        )

        # Check cooldowns
        if recommendation.action == ScalingAction.SCALE_UP:
            if self._last_scale_up:
                elapsed = now - self._last_scale_up
                if elapsed < timedelta(minutes=self._policy.scale_up_cooldown_minutes):
                    logger.info(f"Scale up skipped due to cooldown ({elapsed.total_seconds():.0f}s < {self._policy.scale_up_cooldown_minutes * 60}s)")
                    event.action = ScalingAction.NO_OP
                    event.reason += " [Skipped: cooldown period]"
            else:
                self._last_scale_up = now

        elif recommendation.action == ScalingAction.SCALE_DOWN:
            if self._last_scale_down:
                elapsed = now - self._last_scale_down
                if elapsed < timedelta(minutes=self._policy.scale_down_cooldown_minutes):
                    logger.info(f"Scale down skipped due to cooldown ({elapsed.total_seconds():.0f}s < {self._policy.scale_down_cooldown_minutes * 60}s)")
                    event.action = ScalingAction.NO_OP
                    event.reason += " [Skipped: cooldown period]"
            else:
                self._last_scale_down = now

        # Record event
        self._scaling_history.append(event)
        logger.info(f"Scaling event: {event.action.value} ({event.previous_count} -> {event.new_count}): {event.reason}")

        # Note: Actual agent spawning/termination would be handled by
        # the agent factory or external orchestrator. This service
        # only makes recommendations and tracks events.

        return event

    async def get_scaling_history(
        self,
        limit: int = 50,
    ) -> list[ScalingEvent]:
        """Get history of scaling events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of scaling events, most recent first
        """
        return list(reversed(self._scaling_history[-limit:]))

    async def start_monitoring(
        self,
        interval_seconds: int = 60,
    ) -> None:
        """Start the auto-scaling monitoring loop.

        Args:
            interval_seconds: How often to check for scaling needs
        """
        if self._monitoring:
            logger.warning("Auto-scaling monitoring already running")
            return

        if not self._policy.enable_auto_scaling:
            logger.info("Auto-scaling is disabled in policy")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info(f"Started auto-scaling monitoring (interval: {interval_seconds}s)")

    async def stop_monitoring(self) -> None:
        """Stop the auto-scaling monitoring loop."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("Stopped auto-scaling monitoring")

    async def _monitor_loop(self, interval_seconds: int) -> None:
        """Monitoring loop that periodically checks for scaling needs.

        Args:
            interval_seconds: How often to check
        """
        while self._monitoring:
            try:
                async for session in self._get_db_session():
                    recommendation = await self.get_scaling_recommendation(session)

                    if recommendation.action != ScalingAction.NO_OP:
                        await self.execute_scaling(session, recommendation)

                    break  # Exit the session context manager

            except Exception as e:
                logger.error(f"Error in auto-scaler monitor loop: {e}", exc_info=True)

            await asyncio.sleep(interval_seconds)

    async def _get_db_session(self):
        """Get database session for monitoring.

        Yields:
            Database session
        """
        from db.connection import get_db_session
        async for session in get_db_session():
            yield session

    async def mark_stale_agents(
        self,
        session: AsyncSession,
    ) -> int:
        """Mark agents with stale heartbeats as offline.

        Args:
            session: Database session

        Returns:
            Number of agents marked as offline
        """
        timeout = timedelta(minutes=self._policy.stale_agent_timeout_minutes)
        cutoff = datetime.now(timezone.utc) - timeout

        result = await session.execute(
            select(AgentPool).where(
                and_(
                    AgentPool.deleted_at.is_(None),
                    AgentPool.status != PoolAgentStatus.OFFLINE,
                    AgentPool.last_heartbeat.isnot(None),
                    AgentPool.last_heartbeat < cutoff,
                )
            )
        )
        agents = result.scalars().all()

        count = 0
        for agent in agents:
            agent.status = PoolAgentStatus.OFFLINE
            count += 1
            logger.warning(f"Marked stale agent as offline: {agent.agent_id}")

        if count > 0:
            await session.flush()

        return count


# Singleton instance
_agent_auto_scaler: AgentAutoScaler | None = None


def get_agent_auto_scaler() -> AgentAutoScaler:
    """Get the singleton auto-scaler instance.

    Returns:
        AgentAutoScaler instance
    """
    global _agent_auto_scaler
    if _agent_auto_scaler is None:
        _agent_auto_scaler = AgentAutoScaler()
    return _agent_auto_scaler
