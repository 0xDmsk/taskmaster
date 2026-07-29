"""Tests for the playbook registry and request_playbook expansion."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from policies.playbooks import get_playbook, list_playbooks
from state.state import get_queued_executions
from state.storage import load_executions
from tools.request_playbook import handle_request_playbook


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))
    # Keep audit side effects out of the test run.
    import audit.audit_manager as am

    monkeypatch.setattr(am, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(am, "update_report", lambda *a, **k: None)


def test_registry_lists_builtins():
    names = {p["name"] for p in list_playbooks()}
    assert {"web-recon", "subdomain-recon"} <= names
    assert get_playbook("web-recon")["steps"]
    assert get_playbook("does-not-exist") is None


def test_no_args_lists_available_playbooks():
    result = handle_request_playbook({})
    assert "available_playbooks" in result
    assert any(p["name"] == "web-recon" for p in result["available_playbooks"])


def test_unknown_playbook_reports_available():
    result = handle_request_playbook({"target": "http://example.com", "playbook": "nope"})
    assert "error" in result
    assert "web-recon" in result["available_playbooks"]


def test_missing_target_is_rejected():
    result = handle_request_playbook({"playbook": "web-recon"})
    assert "error" in result and "target" in result["error"]


def test_web_recon_expands_into_a_dependency_chain():
    result = handle_request_playbook(
        {"target": "http://example.com", "playbook": "web-recon"}
    )
    assert result["status"] == "QUEUED"
    ids = result["execution_ids"]
    assert len(ids) == 2

    execs = {e["execution_id"]: e for e in load_executions()}
    step1, step2 = ids
    # Step 2 depends on step 1; step 1 has no deps.
    assert not execs[step1].get("depends_on")
    assert execs[step2]["depends_on"] == [step1]
    # Phases follow the playbook order.
    assert execs[step1]["security_phase"] == "reconnaissance"
    assert execs[step2]["security_phase"] == "enumeration"

    # Only the first step is offered to workers; the second is gated.
    queued_ids = {e["execution_id"] for e in get_queued_executions()}
    assert queued_ids == {step1}


def test_inline_steps_are_chained():
    steps = [
        {
            "phase": "reconnaissance",
            "agent_role": "recon",
            "action_type": "skill",
            "skill": "network.NmapScan",
            "arguments": {},
            "justification": (
                "Initial service and version scan of the target host to enumerate open "
                "ports before deeper enumeration."
            ),
            "expected_output": "Open ports with detected services and versions.",
        },
        {
            "phase": "enumeration",
            "agent_role": "enumeration",
            "action_type": "skill",
            "skill": "web.FfufFuzz",
            "arguments": {},
            "justification": (
                "Content discovery against any web service found by the prior scan to "
                "surface hidden endpoints for review."
            ),
            "expected_output": "Discovered paths with status codes.",
        },
    ]
    result = handle_request_playbook({"target": "10.0.0.5", "steps": steps})
    assert result["status"] == "QUEUED"
    ids = result["execution_ids"]
    assert len(ids) == 2

    execs = {e["execution_id"]: e for e in load_executions()}
    assert execs[ids[1]]["depends_on"] == [ids[0]]


def test_phase_out_of_order_step_aborts_chain():
    # Second step jumps straight to exploitation from reconnaissance — the phase
    # policy rejects it, and the tool reports which step failed.
    steps = [
        {
            "phase": "reconnaissance",
            "agent_role": "recon",
            "action_type": "skill",
            "skill": "network.NmapScan",
            "arguments": {},
            "justification": (
                "Baseline service scan of the host to enumerate exposed ports and "
                "versions before anything else."
            ),
            "expected_output": "Open ports and services.",
        },
        {
            "phase": "exploitation",
            "agent_role": "exploitation",
            "action_type": "skill",
            "skill": "web.FfufFuzz",
            "arguments": {},
            "justification": (
                "This step deliberately skips the enumeration phase to exercise the "
                "phase-ordering guard in the playbook expander."
            ),
            "expected_output": "n/a",
        },
    ]
    result = handle_request_playbook({"target": "10.0.0.9", "steps": steps})
    assert result["failed_step"] == 2
    # The first step was already queued before the invalid one was rejected.
    assert len(result["created_executions"]) == 1
