"""Tests for execution dependencies: gating, readiness, and cancel propagation."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from state.state import (
    cancel_blocked_dependents,
    create_execution,
    dependencies_satisfied,
    get_execution_state,
    get_queued_executions,
    transition_execution,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


def _queue(eid, target="10.0.0.1", phase="reconnaissance", depends_on=None):
    return create_execution(
        execution_id=eid,
        target=target,
        security_phase=phase,
        request_payload={"action_type": "skill", "skill": "x"},
        depends_on=depends_on,
    )


def _complete(eid, executor="w1"):
    transition_execution(eid, "CLAIMED", executor)
    transition_execution(eid, "RUNNING", executor)
    transition_execution(eid, "COMPLETED", executor, result="{}")


def _queued_ids():
    return {e["execution_id"] for e in get_queued_executions()}


def test_no_dependencies_is_ready():
    _queue("a")
    assert dependencies_satisfied(get_execution_state("a")) is True
    assert "a" in _queued_ids()


def test_dependent_is_hidden_until_prerequisite_completes():
    _queue("a")
    _queue("b", depends_on=["a"])

    # b is withheld while a is still QUEUED.
    assert _queued_ids() == {"a"}
    assert dependencies_satisfied(get_execution_state("b")) is False

    _complete("a")

    # Now b is ready and offered to workers.
    assert _queued_ids() == {"b"}
    assert dependencies_satisfied(get_execution_state("b")) is True


def test_claiming_a_blocked_execution_is_rejected():
    _queue("a")
    _queue("b", depends_on=["a"])

    with pytest.raises(ValueError, match="unmet dependencies"):
        transition_execution("b", "CLAIMED", "w1")


def test_failed_prerequisite_cancels_dependent():
    _queue("a")
    _queue("b", depends_on=["a"])

    transition_execution("a", "CLAIMED", "w1")
    transition_execution("a", "RUNNING", "w1")
    transition_execution("a", "FAILED", "w1", result="boom")

    assert get_execution_state("b")["status"] == "CANCELLED"
    assert _queued_ids() == set()


def test_cancelled_prerequisite_cancels_dependent():
    _queue("a")
    _queue("b", depends_on=["a"])

    transition_execution("a", "CANCELLED", "w1")

    assert get_execution_state("b")["status"] == "CANCELLED"


def test_cancellation_propagates_through_a_chain():
    _queue("a")
    _queue("b", depends_on=["a"])
    _queue("c", depends_on=["b"])

    # a fails → b cancelled → c cancelled (recursively).
    transition_execution("a", "CLAIMED", "w1")
    transition_execution("a", "RUNNING", "w1")
    transition_execution("a", "FAILED", "w1")

    assert get_execution_state("b")["status"] == "CANCELLED"
    assert get_execution_state("c")["status"] == "CANCELLED"


def test_cancel_blocked_dependents_returns_ids_and_is_idempotent():
    _queue("a")
    _queue("b", depends_on=["a"])

    cancelled = cancel_blocked_dependents("a", "manual")
    assert cancelled == ["b"]
    # Running it again cancels nothing new (b is already terminal).
    assert cancel_blocked_dependents("a", "manual") == []


def test_multiple_prerequisites_all_must_complete():
    _queue("a")
    _queue("b")
    _queue("c", depends_on=["a", "b"])

    _complete("a")
    assert "c" not in _queued_ids()  # b still pending

    _complete("b")
    assert "c" in _queued_ids()
