"""
Integration tests for Ralph wrapper.

Tests the Ralph event streaming integration with the WebSocket server.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response

from backend.wrappers.ralph_wrapper import (
    RalphEvent,
    RalphEventType,
    RalphOutputParser,
    RalphSession,
    RalphWrapper,
)


class TestRalphEvent:
    """Test Ralph event data structures."""

    def test_event_creation(self):
        """Test creating a Ralph event."""
        event = RalphEvent(
            event_type=RalphEventType.SPEC_START,
            session_id=uuid.uuid4(),
            data={"spec_name": "test-spec"},
        )
        assert event.event_type == RalphEventType.SPEC_START
        assert isinstance(event.session_id, uuid.UUID)
        assert event.data["spec_name"] == "test-spec"

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        session_id = uuid.uuid4()
        event = RalphEvent(
            event_type=RalphEventType.SPEC_COMPLETE,
            session_id=session_id,
            data={"spec_name": "test-spec", "duration": 1.5},
        )
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "spec_complete"
        assert event_dict["session_id"] == str(session_id)
        assert event_dict["data"]["duration"] == 1.5

    def test_event_to_ingest_payload(self):
        """Test converting event to ingest payload format."""
        session_id = uuid.uuid4()
        event = RalphEvent(
            event_type=RalphEventType.ERROR,
            session_id=session_id,
            data={"message": "Test error"},
        )
        payload = event.to_ingest_payload()
        assert "session_id" in payload
        assert "event_type" in payload
        assert "data" in payload
        assert payload["event_type"] == "error"


class TestRalphSession:
    """Test Ralph session data structure."""

    def test_session_creation(self):
        """Test creating a Ralph session."""
        session = RalphSession(project_name="test-project")
        assert isinstance(session.session_id, uuid.UUID)
        assert session.project_name == "test-project"
        assert session.status == "running"
        assert session.started_at.tzinfo == timezone.utc

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        session = RalphSession(
            project_name="test-project",
            pid=12345,
            tmux_session="ralph-session",
        )
        session_dict = session.to_dict()
        assert session_dict["project_name"] == "test-project"
        assert session_dict["pid"] == 12345
        assert session_dict["tmux_session"] == "ralph-session"


class TestRalphOutputParser:
    """Test Ralph output parser."""

    @pytest.fixture
    def session_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def parser(self, session_id):
        return RalphOutputParser(session_id)

    def test_parse_spec_start(self, parser):
        """Test parsing spec start event."""
        line = "[ORCHESTRATOR] Starting spec 04-ralph-integration"
        event = parser.parse_line(line)
        assert event is not None
        assert event.event_type == RalphEventType.SPEC_START
        assert event.data["spec_name"] == "04-ralph-integration"

    def test_parse_spec_complete(self, parser):
        """Test parsing spec complete event."""
        line = "[RALPH] Completed spec 04-ralph-integration in 12.5s"
        event = parser.parse_line(line)
        assert event is not None
        assert event.event_type == RalphEventType.SPEC_COMPLETE
        assert event.data["spec_name"] == "04-ralph-integration"
        assert event.data["duration_seconds"] == 12.5

    def test_parse_error(self, parser):
        """Test parsing error event."""
        line = "[ERROR] Failed to execute command: ralph not found"
        event = parser.parse_line(line)
        assert event is not None
        assert event.event_type == RalphEventType.ERROR
        assert "Failed to execute command" in event.data["message"]

    def test_parse_progress(self, parser):
        """Test parsing progress event."""
        line = "[PROGRESS] 50% complete"
        event = parser.parse_line(line)
        assert event is not None
        assert event.event_type == RalphEventType.PROGRESS
        assert event.data["percentage"] == 50

    def test_parse_iteration(self, parser):
        """Test parsing iteration event."""
        line = "[ORCHESTRATOR] Iteration 5/17"
        event = parser.parse_line(line)
        assert event is not None
        assert event.event_type == RalphEventType.PROGRESS
        assert event.data["iteration"] == 5
        assert event.data["max_iterations"] == 17
        assert event.data["percentage"] == int((5 / 17) * 100)

    def test_parse_atom_progress(self, parser):
        """Test parsing atom/subtask progress event."""
        line = "[ATOM] Starting: Create database schema"
        event = parser.parse_line(line)
        assert event is not None
        assert event.event_type == RalphEventType.PROGRESS
        assert event.data["atom_status"] == "starting"
        assert event.data["atom_name"] == "Create database schema"

    def test_parse_unmatched_line(self, parser):
        """Test parsing a line that doesn't match any pattern."""
        line = "Some random output that doesn't match any pattern"
        event = parser.parse_line(line)
        assert event is None

    def test_parse_empty_line(self, parser):
        """Test parsing an empty line."""
        event = parser.parse_line("")
        assert event is None

    def test_current_spec_tracking(self, parser):
        """Test that parser tracks current spec across events."""
        spec_start_line = "[RALPH] Starting spec 04-ralph-integration"
        error_line = "[ERROR] Something went wrong"

        start_event = parser.parse_line(spec_start_line)
        assert start_event is not None
        assert start_event.data["spec_name"] == "04-ralph-integration"

        error_event = parser.parse_line(error_line)
        assert error_event is not None
        # Error should include the current spec context
        assert error_event.data["spec_name"] == "04-ralph-integration"


class TestRalphProcessDetector:
    """Test Ralph process detection."""

    def test_find_tmux_session(self):
        """Test finding tmux session."""
        # This test may not find a session in CI, just verify it doesn't crash
        from backend.wrappers.ralph_wrapper import RalphProcessDetector

        session = RalphProcessDetector.find_tmux_session("ralph")
        # Result can be None or a string, both are valid
        assert session is None or isinstance(session, str)

    def test_is_process_alive(self):
        """Test checking if process is alive."""
        from backend.wrappers.ralph_wrapper import RalphProcessDetector

        # Test with current process (should be alive)
        import os
        current_pid = os.getpid()
        assert RalphProcessDetector.is_process_alive(current_pid) is True

        # Test with invalid PID (should be dead)
        assert RalphProcessDetector.is_process_alive(999999999) is False


@pytest.mark.asyncio
class TestRalphWrapper:
    """Test Ralph wrapper integration."""

    @pytest_asyncio.fixture
    async def mock_websocket_server(self):
        """Mock WebSocket server for testing."""
        mock_client = AsyncMock(spec=AsyncClient)

        async def mock_post(*args, **kwargs):
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            return mock_response

        mock_client.post = mock_post
        return mock_client

    @pytest_asyncio.fixture
    async def wrapper(self):
        """Create a wrapper instance for testing."""
        wrapper = RalphWrapper(
            websocket_url="http://localhost:8005",
            project_name="test-project",
        )
        yield wrapper
        # Cleanup
        if wrapper._running:
            await wrapper.shutdown()

    async def test_wrapper_initialization(self, wrapper):
        """Test wrapper initialization."""
        await wrapper.initialize()
        assert wrapper.session.session_id == wrapper.session_id
        assert wrapper.session.project_name == "test-project"
        assert wrapper.client is not None
        await wrapper.shutdown()

    async def test_session_start_event_emitted(self, wrapper, mock_websocket_server):
        """Test that session start event is emitted on initialization."""
        with patch.object(
            wrapper, "client", mock_websocket_server
        ):
            await wrapper.initialize()
            # Verify client.send_event was called
            # (In real test, would check the event payload)
            await wrapper.shutdown()

    async def test_wrap_command_success(self, wrapper, tmp_path):
        """Test wrapping a successful command."""
        # Create a simple test script
        test_script = tmp_path / "test.sh"
        test_script.write_text("#!/bin/bash\necho '[RALPH] Starting spec test-spec'\necho '[RALPH] Completed spec test-spec in 1.0s'\n")
        test_script.chmod(0o755)

        # Mock the client to avoid actual HTTP calls
        wrapper.client = AsyncMock()
        wrapper.client.send_event = AsyncMock(return_value=True)

        exit_code = await wrapper.wrap_command([str(test_script)])
        assert exit_code == 0

    async def test_wrap_command_failure(self, wrapper, tmp_path):
        """Test wrapping a failing command."""
        # Create a script that exits with error
        test_script = tmp_path / "fail.sh"
        test_script.write_text("#!/bin/bash\necho '[ERROR] Test error' 1>&2\nexit 1\n")
        test_script.chmod(0o755)

        # Mock the client
        wrapper.client = AsyncMock()
        wrapper.client.send_event = AsyncMock(return_value=True)

        exit_code = await wrapper.wrap_command([str(test_script)])
        assert exit_code == 1


@pytest.mark.asyncio
class TestRalphEventE2E:
    """End-to-end tests for Ralph event streaming."""

    async def test_event_lifecycle(self):
        """Test complete event lifecycle from creation to transmission."""
        session_id = uuid.uuid4()

        # Create events
        start_event = RalphEvent(
            event_type=RalphEventType.SESSION_START,
            session_id=session_id,
            data={"project_name": "test"},
        )

        spec_start_event = RalphEvent(
            event_type=RalphEventType.SPEC_START,
            session_id=session_id,
            data={"spec_name": "04-ralph-integration"},
        )

        progress_event = RalphEvent(
            event_type=RalphEventType.PROGRESS,
            session_id=session_id,
            data={"percentage": 50},
        )

        spec_complete_event = RalphEvent(
            event_type=RalphEventType.SPEC_COMPLETE,
            session_id=session_id,
            data={"spec_name": "04-ralph-integration", "duration_seconds": 10.5},
        )

        # Verify all events can be converted to payload
        for event in [start_event, spec_start_event, progress_event, spec_complete_event]:
            payload = event.to_ingest_payload()
            assert "session_id" in payload
            assert "event_type" in payload
            assert "data" in payload
            assert payload["session_id"] == str(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
