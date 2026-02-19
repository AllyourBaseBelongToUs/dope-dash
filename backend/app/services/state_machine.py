"""Project state machine service with validation, hooks, and automation."""
from datetime import datetime
from typing import Callable, Any
from enum import Enum

from sqlalchemy.orm import Session

from app.models.project import ProjectStatus
from app.models.state_transition import StateTransition, StateTransitionSource


# Valid state transitions map
# Key: current state, Value: set of valid next states
VALID_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.IDLE: {
        ProjectStatus.QUEUED,
        ProjectStatus.RUNNING,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.QUEUED: {
        ProjectStatus.RUNNING,
        ProjectStatus.IDLE,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.RUNNING: {
        ProjectStatus.PAUSED,
        ProjectStatus.ERROR,
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.PAUSED: {
        ProjectStatus.RUNNING,
        ProjectStatus.IDLE,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.ERROR: {
        ProjectStatus.IDLE,
        ProjectStatus.QUEUED,
        ProjectStatus.RUNNING,  # Retry
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.COMPLETED: {
        ProjectStatus.IDLE,  # Reset for new work
    },
    ProjectStatus.CANCELLED: {
        ProjectStatus.IDLE,
        ProjectStatus.QUEUED,
    },
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: ProjectStatus, to_state: ProjectStatus, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        message = f"Invalid transition from {from_state.value} to {to_state.value}"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class StateTransitionValidator:
    """Validates project state transitions."""

    @staticmethod
    def is_valid_transition(from_state: ProjectStatus | None, to_state: ProjectStatus) -> bool:
        """Check if a transition is valid.

        Args:
            from_state: Current state (None for initial state).
            to_state: Target state.

        Returns:
            True if transition is valid, False otherwise.
        """
        if from_state is None:
            # Initial state must be IDLE or QUEUED
            return to_state in {ProjectStatus.IDLE, ProjectStatus.QUEUED}

        return to_state in VALID_TRANSITIONS.get(from_state, set())

    @staticmethod
    def get_valid_transitions(current_state: ProjectStatus) -> list[ProjectStatus]:
        """Get all valid next states from the current state.

        Args:
            current_state: Current project state.

        Returns:
            List of valid next states.
        """
        return list(VALID_TRANSITIONS.get(current_state, set()))

    @staticmethod
    def validate_transition(from_state: ProjectStatus | None, to_state: ProjectStatus) -> None:
        """Validate a transition and raise if invalid.

        Args:
            from_state: Current state (None for initial state).
            to_state: Target state.

        Raises:
            StateTransitionError: If transition is invalid.
        """
        if not StateTransitionValidator.is_valid_transition(from_state, to_state):
            raise StateTransitionError(
                from_state or ProjectStatus.IDLE,
                to_state,
                f"Allowed from {from_state.value if from_state else 'None'}: {[s.value for s in VALID_TRANSITIONS.get(from_state, set())]}"
            )


# Type for transition hooks
TransitionHook = Callable[[ProjectStatus, ProjectStatus, dict[str, Any]], None]


class StateMachineService:
    """Service for managing project state transitions."""

    def __init__(self, db: Session):
        """Initialize the state machine service.

        Args:
            db: Database session.
        """
        self.db = db
        self._pre_hooks: list[TransitionHook] = []
        self._post_hooks: list[TransitionHook] = []

    def register_pre_hook(self, hook: TransitionHook) -> None:
        """Register a hook to run before state transitions.

        Args:
            hook: Callable that receives (from_state, to_state, metadata).
        """
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook: TransitionHook) -> None:
        """Register a hook to run after state transitions.

        Args:
            hook: Callable that receives (from_state, to_state, metadata).
        """
        self._post_hooks.append(hook)

    def transition(
        self,
        project_id: str,
        from_state: ProjectStatus | None,
        to_state: ProjectStatus,
        source: StateTransitionSource = StateTransitionSource.SYSTEM,
        initiated_by: str = "system",
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        previous_state_duration_ms: int | None = None,
    ) -> StateTransition:
        """Execute a state transition with validation and audit logging.

        Args:
            project_id: Project UUID.
            from_state: Current state (None for initial).
            to_state: Target state.
            source: Source of the transition.
            initiated_by: Who/what initiated the transition.
            reason: Optional reason for the transition.
            metadata: Additional metadata.
            previous_state_duration_ms: Duration of the previous state.

        Returns:
            Created StateTransition record.

        Raises:
            StateTransitionError: If transition is invalid.
        """
        # Validate transition
        StateTransitionValidator.validate_transition(from_state, to_state)

        # Run pre-transition hooks
        hook_metadata = metadata or {}
        for hook in self._pre_hooks:
            hook(from_state, to_state, hook_metadata)

        # Create transition record
        transition = StateTransition(
            project_id=project_id,
            from_state=from_state,
            to_state=to_state,
            source=source,
            initiated_by=initiated_by,
            transition_reason=reason,
            meta_data=hook_metadata,
            duration_ms=previous_state_duration_ms,
            created_at=datetime.utcnow(),
        )
        self.db.add(transition)
        self.db.flush()

        # Run post-transition hooks
        for hook in self._post_hooks:
            hook(from_state, to_state, hook_metadata)

        return transition

    def get_state_history(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StateTransition]:
        """Get state transition history for a project.

        Args:
            project_id: Project UUID.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            List of StateTransition records.
        """
        return (
            self.db.query(StateTransition)
            .filter(StateTransition.project_id == project_id)
            .order_by(StateTransition.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_latest_transition(self, project_id: str) -> StateTransition | None:
        """Get the most recent transition for a project.

        Args:
            project_id: Project UUID.

        Returns:
            Most recent StateTransition or None.
        """
        return (
            self.db.query(StateTransition)
            .filter(StateTransition.project_id == project_id)
            .order_by(StateTransition.created_at.desc())
            .first()
        )


def auto_retry_on_error(
    from_state: ProjectStatus | None,
    to_state: ProjectStatus,
    metadata: dict[str, Any],
) -> None:
    """Hook for automatic retry when entering ERROR state.

    This hook can be registered to automatically queue a retry
    when a project enters the ERROR state.

    Args:
        from_state: Previous state.
        to_state: New state.
        metadata: Transition metadata (can contain retry config).
    """
    if to_state == ProjectStatus.ERROR:
        # Check if auto-retry is enabled
        if metadata.get("auto_retry", False):
            max_retries = metadata.get("max_retries", 3)
            current_retry = metadata.get("retry_count", 0)

            if current_retry < max_retries:
                # Mark for auto-retry (actual transition handled by caller)
                metadata["should_auto_retry"] = True
                metadata["retry_count"] = current_retry + 1


def validate_state_permission(
    from_state: ProjectStatus | None,
    to_state: ProjectStatus,
    metadata: dict[str, Any],
) -> None:
    """Hook for validating permissions on state transitions.

    Checks if the initiator has permission to perform the transition.

    Args:
        from_state: Previous state.
        to_state: New state.
        metadata: Transition metadata.

    Raises:
        PermissionError: If transition not permitted.
    """
    # Define restricted transitions (e.g., only admins can cancel)
    restricted_transitions: dict[tuple[ProjectStatus | None, ProjectStatus], set[str]] = {
        (ProjectStatus.RUNNING, ProjectStatus.CANCELLED): {"admin", "operator"},
        (ProjectStatus.QUEUED, ProjectStatus.CANCELLED): {"admin", "operator"},
        (None, ProjectStatus.CANCELLED): {"admin"},
    }

    key = (from_state, to_state)
    if key in restricted_transitions:
        allowed_roles = restricted_transitions[key]
        initiator_role = metadata.get("initiator_role", "user")

        if initiator_role not in allowed_roles:
            raise PermissionError(
                f"Role '{initiator_role}' not permitted to transition from "
                f"{from_state.value if from_state else 'None'} to {to_state.value}"
            )
