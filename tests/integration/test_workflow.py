"""
Integration tests for complete workflows
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from tools.request_security_action import handle_request
from tools.claim_execution import handle_claim_execution
from tools.start_execution import handle_start_execution
from tools.complete_execution import handle_complete_execution
from tools.fail_execution import handle_fail_execution
from tools.query_execution_status import handle_query_execution_status
from tools.recover_execution import handle_recover_execution


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Ensure every test uses an isolated SQLite database."""
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


class TestFullLifecycle:
    """Test complete execution lifecycle"""

    def test_successful_execution_lifecycle(self):
        """Test a complete successful execution from QUEUED to COMPLETED"""
        # 1. Request action
        payload = {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "10.0.0.1",
            "action_type": "network_scan",
            "tool": "nmap",
            "command": "nmap -sV 10.0.0.1",
            "justification": "Initial reconnaissance to identify open ports and services on target system",
            "expected_output": "XML scan results",
        }
        result = handle_request(payload)
        execution_id = result["execution_id"]

        # Verify QUEUED state
        status = handle_query_execution_status({"execution_id": execution_id})
        assert status["status"] == "QUEUED"

        # 2. Claim execution
        claim_result = handle_claim_execution(
            {"execution_id": execution_id, "executor_id": "test-agent-1"}
        )
        assert claim_result["status"] == "CLAIMED"

        # 3. Start execution
        start_result = handle_start_execution(
            {"execution_id": execution_id, "executor_id": "test-agent-1"}
        )
        assert start_result["status"] == "RUNNING"

        # 4. Complete execution
        complete_result = handle_complete_execution(
            {
                "execution_id": execution_id,
                "executor_id": "test-agent-1",
                "result": "Scan completed successfully",
            }
        )
        assert complete_result["status"] == "COMPLETED"

    def test_failed_execution_lifecycle(self):
        """Test execution lifecycle ending in FAILED state"""
        # Request action
        payload = {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "10.0.0.2",
            "action_type": "network_scan",
            "tool": "nmap",
            "command": "nmap -sV 10.0.0.2",
            "justification": "Test failed execution path for unreachable target system",
            "expected_output": "Error or timeout",
        }
        result = handle_request(payload)
        execution_id = result["execution_id"]

        # Claim and start
        handle_claim_execution(
            {"execution_id": execution_id, "executor_id": "test-agent-2"}
        )
        handle_start_execution(
            {"execution_id": execution_id, "executor_id": "test-agent-2"}
        )

        # Fail execution
        fail_result = handle_fail_execution(
            {
                "execution_id": execution_id,
                "executor_id": "test-agent-2",
                "error_info": "Network timeout - host unreachable",
            }
        )
        assert fail_result["status"] == "FAILED"


class TestTargetConcurrency:
    """Test target locking and concurrent execution prevention"""

    def test_cannot_run_concurrent_executions_on_same_target(self):
        """Test that target locking prevents concurrent executions"""
        # Start first execution
        payload = {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "10.0.0.1",
            "action_type": "network_scan",
            "tool": "nmap",
            "command": "nmap -sV 10.0.0.1",
            "justification": "First execution to test concurrent target locking mechanism",
            "expected_output": "Scan results",
        }
        result1 = handle_request(payload)
        exec_id_1 = result1["execution_id"]

        # Move to RUNNING
        handle_claim_execution({"execution_id": exec_id_1, "executor_id": "agent-1"})
        handle_start_execution({"execution_id": exec_id_1, "executor_id": "agent-1"})

        # Try to start second execution on same target
        result2 = handle_request(payload)
        exec_id_2 = result2["execution_id"]
        handle_claim_execution({"execution_id": exec_id_2, "executor_id": "agent-2"})

        # start_execution catches ValueError internally and returns an error dict
        start_result = handle_start_execution(
            {"execution_id": exec_id_2, "executor_id": "agent-2"}
        )
        assert "error" in start_result
        assert "busy" in start_result["error"].lower()


class TestExecutorOwnership:
    """Test that agents cannot interfere with each other's executions"""

    def test_agent2_cannot_complete_agent1_task(self):
        """Test that a different executor cannot complete another's running execution"""
        payload = {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "10.0.0.3",
            "action_type": "network_scan",
            "tool": "nmap",
            "command": "nmap -sV 10.0.0.3",
            "justification": "Test executor ownership enforcement across different agents",
            "expected_output": "Scan results",
        }
        result = handle_request(payload)
        execution_id = result["execution_id"]

        # agent-1 claims and starts
        handle_claim_execution(
            {"execution_id": execution_id, "executor_id": "agent-1"}
        )
        handle_start_execution(
            {"execution_id": execution_id, "executor_id": "agent-1"}
        )

        # agent-2 tries to complete — should get an error
        complete_result = handle_complete_execution(
            {
                "execution_id": execution_id,
                "executor_id": "agent-2",
                "result": "Hijacked!",
            }
        )
        assert "error" in complete_result
        assert "mismatch" in complete_result["error"].lower()


class TestRecovery:
    """Test the recovery tool"""

    def test_recover_single_running_execution(self):
        """Test recovering a single stuck RUNNING execution"""
        payload = {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "10.0.0.4",
            "action_type": "network_scan",
            "tool": "nmap",
            "command": "nmap -sV 10.0.0.4",
            "justification": "Test recovery of stuck running execution after agent crash",
            "expected_output": "Scan results",
        }
        result = handle_request(payload)
        execution_id = result["execution_id"]

        # Move to RUNNING
        handle_claim_execution(
            {"execution_id": execution_id, "executor_id": "agent-1"}
        )
        handle_start_execution(
            {"execution_id": execution_id, "executor_id": "agent-1"}
        )

        # Recover it
        recover_result = handle_recover_execution({"execution_id": execution_id})
        assert recover_result["status"] == "success"
        assert recover_result["recovered_count"] == 1
        assert recover_result["recovered"][0]["previous_status"] == "RUNNING"
        assert recover_result["recovered"][0]["new_status"] == "FAILED"

        # Verify it's now FAILED
        status = handle_query_execution_status({"execution_id": execution_id})
        assert status["status"] == "FAILED"

    def test_recover_non_stuck_execution_fails(self):
        """Test that recovering a QUEUED execution fails gracefully"""
        payload = {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "10.0.0.5",
            "action_type": "network_scan",
            "tool": "nmap",
            "command": "nmap -sV 10.0.0.5",
            "justification": "Test that recovery rejects non-stuck queued execution state",
            "expected_output": "Scan results",
        }
        result = handle_request(payload)
        execution_id = result["execution_id"]

        # Try to recover a QUEUED execution — should fail
        recover_result = handle_recover_execution({"execution_id": execution_id})
        assert "error" in recover_result
