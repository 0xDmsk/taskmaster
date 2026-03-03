"""
Unit tests for state management
"""
import os
import pytest

# Import state management functions
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from state.state import (
    create_execution,
    is_target_busy,
    transition_execution,
    get_execution_state,
    get_target_state,
    get_queued_executions,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Ensure every test uses an isolated SQLite database."""
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


class TestExecutionCreation:
    """Test execution creation"""

    def test_create_execution_basic(self):
        """Test basic execution creation"""
        execution = create_execution(
            execution_id="test-123",
            target="10.0.0.1",
            security_phase="reconnaissance",
            request_payload={"tool": "nmap", "command": "nmap -sV 10.0.0.1"},
        )

        assert execution["execution_id"] == "test-123"
        assert execution["target"] == "10.0.0.1"
        assert execution["status"] == "QUEUED"
        assert execution["security_phase"] == "reconnaissance"
        assert execution["result"] is None

    def test_create_execution_with_custom_creator(self):
        """Test execution creation with custom creator"""
        execution = create_execution(
            execution_id="test-456",
            target="example.com",
            security_phase="enumeration",
            request_payload={},
            created_by="agent-007",
        )

        assert execution["created_by"] == "agent-007"

    def test_create_execution_persists(self):
        """Test that created execution can be retrieved"""
        create_execution(
            execution_id="persist-1",
            target="10.0.0.1",
            security_phase="reconnaissance",
            request_payload={},
        )

        state = get_execution_state("persist-1")
        assert state is not None
        assert state["execution_id"] == "persist-1"
        assert state["status"] == "QUEUED"


class TestTargetLocking:
    """Test target locking mechanism"""

    def test_target_not_busy_when_empty(self):
        """Test that target is not busy when no executions exist"""
        assert not is_target_busy("10.0.0.1")

    def test_target_busy_when_running(self):
        """Test that target is busy when execution is RUNNING"""
        create_execution(
            execution_id="test-running",
            target="10.0.0.1",
            security_phase="reconnaissance",
            request_payload={},
        )
        transition_execution("test-running", "CLAIMED", "agent-1")
        transition_execution("test-running", "RUNNING", "agent-1")

        assert is_target_busy("10.0.0.1")

    def test_target_not_busy_when_completed(self):
        """Test that target is not busy when execution is COMPLETED"""
        create_execution(
            execution_id="test-completed",
            target="10.0.0.1",
            security_phase="reconnaissance",
            request_payload={},
        )
        transition_execution("test-completed", "CLAIMED", "agent-1")
        transition_execution("test-completed", "RUNNING", "agent-1")
        transition_execution("test-completed", "COMPLETED", "agent-1", result="done")

        assert not is_target_busy("10.0.0.1")


class TestExecutorOwnership:
    """Test executor_id verification on transitions"""

    def test_claim_binds_executor_id(self):
        """Test that claiming sets executor_id"""
        create_execution(
            execution_id="own-1",
            target="10.0.0.1",
            security_phase="reconnaissance",
            request_payload={},
        )
        transition_execution("own-1", "CLAIMED", "agent-1")

        state = get_execution_state("own-1")
        assert state["executor_id"] == "agent-1"

    def test_wrong_executor_cannot_start(self):
        """Test that a different executor cannot start another's claimed execution"""
        create_execution(
            execution_id="own-2",
            target="10.0.0.2",
            security_phase="reconnaissance",
            request_payload={},
        )
        transition_execution("own-2", "CLAIMED", "agent-1")

        with pytest.raises(ValueError, match="Executor mismatch"):
            transition_execution("own-2", "RUNNING", "agent-2")

    def test_wrong_executor_cannot_complete(self):
        """Test that a different executor cannot complete another's execution"""
        create_execution(
            execution_id="own-3",
            target="10.0.0.3",
            security_phase="reconnaissance",
            request_payload={},
        )
        transition_execution("own-3", "CLAIMED", "agent-1")
        transition_execution("own-3", "RUNNING", "agent-1")

        with pytest.raises(ValueError, match="Executor mismatch"):
            transition_execution("own-3", "COMPLETED", "agent-2", result="stolen")


class TestQuerying:
    """Test query functions"""

    def test_get_queued_executions(self):
        """Test retrieving queued executions"""
        create_execution(
            execution_id="queued-1",
            target="10.0.0.1",
            security_phase="reconnaissance",
            request_payload={},
        )

        queued = get_queued_executions()
        assert len(queued) >= 1
        assert any(e["execution_id"] == "queued-1" for e in queued)

    def test_get_target_state(self):
        """Test retrieving last phase for a target"""
        create_execution(
            execution_id="phase-1",
            target="10.0.0.5",
            security_phase="reconnaissance",
            request_payload={},
        )

        state = get_target_state("10.0.0.5")
        assert state["last_phase"] == "reconnaissance"

    def test_get_target_state_empty(self):
        """Test target state when no executions exist"""
        state = get_target_state("nonexistent.host")
        assert state["last_phase"] is None
