import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from state.state import create_execution, transition_execution
from state.storage import get_execution_by_id
from tools.mark_execution_complete import handle_mark_execution_complete


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


def _drive_to_completed(eid, executor="w1"):
    create_execution(eid, "com.example.app", "reconnaissance", {"action_type": "mobile_skill"})
    transition_execution(eid, "CLAIMED", executor)
    transition_execution(eid, "RUNNING", executor)
    transition_execution(eid, "COMPLETED", executor, result='{"raw": "worker output"}')


def test_interpretation_attaches_to_already_completed_execution():
    # Regression: the worker completes the execution, then the orchestrator adds
    # its interpretation. COMPLETED has no self-transition, so this must be a
    # metadata attach, not an illegal COMPLETED -> COMPLETED transition.
    eid = "exec-interp-1"
    _drive_to_completed(eid)

    res = handle_mark_execution_complete(
        {
            "execution_id": eid,
            "executor_id": "orchestrator",
            "interpretation": "Manifest exposes 3 unguarded components; follow up on the provider.",
        }
    )

    assert "error" not in res, res
    assert res["status"] == "COMPLETED"
    assert res["interpretation_attached"] is True

    stored = get_execution_by_id(eid)
    assert stored["interpretation"].startswith("Manifest exposes")
    # The worker's raw result must be preserved, not clobbered.
    assert "worker output" in stored["result"]


def test_illegal_transition_still_rejected():
    # A genuinely illegal transition (e.g. COMPLETED -> FAILED) must still fail.
    eid = "exec-interp-2"
    _drive_to_completed(eid)

    res = handle_mark_execution_complete(
        {"execution_id": eid, "executor_id": "w1", "status": "FAILED"}
    )
    assert "error" in res
    assert "Illegal transition" in res["error"]
