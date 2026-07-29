"""Tests for the suggest_next_action advisor."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json

import pytest

from state.state import create_execution, transition_execution
from tools.suggest_next_action import handle_suggest_next_action


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


def _categories(result):
    return {s["category"] for s in result["suggestions"]}


def _by_category(result, category):
    return next(s for s in result["suggestions"] if s["category"] == category)


def _complete(eid, executor="w1", result="{}", interpretation=None):
    transition_execution(eid, "CLAIMED", executor)
    transition_execution(eid, "RUNNING", executor)
    transition_execution(eid, "COMPLETED", executor, result=result, interpretation=interpretation)


def test_clean_scope_has_no_suggestions():
    result = handle_suggest_next_action({})
    assert result["suggestions"] == []
    assert "No outstanding actions" in result["headline"]


def test_failed_execution_is_flagged_high():
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    transition_execution("a", "CLAIMED", "w1")
    transition_execution("a", "RUNNING", "w1")
    transition_execution("a", "FAILED", "w1", result="boom")

    result = handle_suggest_next_action({})
    assert "failed_executions" in _categories(result)
    assert _by_category(result, "failed_executions")["priority"] == "high"
    assert result["summary"]["failed"] == 1


def test_completed_without_interpretation_is_flagged():
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    _complete("a")  # no interpretation

    result = handle_suggest_next_action({})
    s = _by_category(result, "missing_interpretation")
    assert s["priority"] == "high"
    assert "a" in s["execution_ids"]


def test_interpretation_present_is_not_flagged():
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    _complete("a", interpretation="Found an open admin panel at /admin.")

    result = handle_suggest_next_action({})
    assert "missing_interpretation" not in _categories(result)


def test_ready_queue_is_flagged_and_blocked_is_separate():
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    create_execution("b", "10.0.0.1", "enumeration", {"action_type": "skill"}, depends_on=["a"])

    result = handle_suggest_next_action({})
    cats = _categories(result)
    # a is ready; b is blocked behind a.
    assert "ready_queue" in cats
    assert "blocked_queue" in cats
    assert "a" in _by_category(result, "ready_queue")["execution_ids"]


def test_completed_observations_without_finding_are_unpromoted():
    envelope = json.dumps({"skill": "x", "findings": [{"host": "h", "port": 80}], "artifacts": []})
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    _complete("a", result=envelope, interpretation="Port 80 open.")

    result = handle_suggest_next_action({})
    s = _by_category(result, "unpromoted_observations")
    assert "a" in s["execution_ids"]


def test_phase_gap_recon_done_no_enumeration():
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    _complete("a", interpretation="done")

    result = handle_suggest_next_action({})
    s = _by_category(result, "phase_gap")
    targets = {g["target"]: g["next_phase"] for g in s["gaps"]}
    assert targets["10.0.0.1"] == "enumeration"


def test_no_phase_gap_when_next_phase_attempted():
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    _complete("a", interpretation="done")
    # An enumeration execution exists (even if only queued) → no gap.
    create_execution("b", "10.0.0.1", "enumeration", {"action_type": "skill"})

    result = handle_suggest_next_action({})
    assert "phase_gap" not in _categories(result)


def test_unknown_engagement_is_rejected():
    result = handle_suggest_next_action({"engagement_id": "nope"})
    assert "error" in result


def test_suggestions_are_priority_ordered():
    # One high (failed) and one lower-priority (phase gap via a second target).
    create_execution("a", "10.0.0.1", "reconnaissance", {"action_type": "skill"})
    transition_execution("a", "CLAIMED", "w1")
    transition_execution("a", "RUNNING", "w1")
    transition_execution("a", "FAILED", "w1")

    create_execution("b", "10.0.0.2", "reconnaissance", {"action_type": "skill"})
    _complete("b", interpretation="done")

    result = handle_suggest_next_action({})
    priorities = [s["priority"] for s in result["suggestions"]]
    ranks = {"high": 0, "medium": 1, "low": 2, "info": 3}
    assert priorities == sorted(priorities, key=lambda p: ranks[p])
    assert result["headline"] == result["suggestions"][0]["message"]
