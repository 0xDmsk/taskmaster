import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from state.state import create_execution, transition_execution
from tools.aggregate_executions import handle_aggregate_executions


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


def _completed_shard(eid, findings, status="COMPLETED", executor="w1"):
    create_execution(eid, "com.example.app", "enumeration", {"action_type": "mobile_skill"})
    transition_execution(eid, "CLAIMED", executor)
    transition_execution(eid, "RUNNING", executor)
    envelope = {
        "skill": "mobile.MobileNucleiScan",
        "findings": findings,
        "artifacts": [],
        "errors": [],
    }
    final = "COMPLETED" if status == "COMPLETED" else "FAILED"
    transition_execution(eid, final, executor, result=json.dumps(envelope))


def test_merges_lists_and_counts_and_or_bools():
    _completed_shard(
        "s1",
        {
            "results": [{"template_id": "a"}, {"template_id": "b"}],
            "result_count": 2,
            "timed_out": False,
        },
    )
    _completed_shard(
        "s2",
        {
            "results": [{"template_id": "b"}, {"template_id": "c"}],
            "result_count": 2,
            "timed_out": True,
        },
    )

    agg = handle_aggregate_executions({"execution_ids": ["s1", "s2"]})
    # b appears in both shards -> deduped to one.
    tids = {r["template_id"] for r in agg["findings"]["results"]}
    assert tids == {"a", "b", "c"}
    # Canonical recomputed count from the deduped list; the skill's own
    # 'result_count' (which would double-count b) is dropped, not surfaced.
    assert agg["findings"]["results_count"] == 3
    assert "result_count" not in agg["findings"]  # count-ish numbers are not summed
    assert agg["findings"]["timed_out"] is True  # OR across shards
    assert agg["any_timed_out"] is True
    assert agg["overall_status"] == "partial"  # a shard timed out
    assert agg["shard_count"] == 2


def test_overall_complete_when_all_clean():
    _completed_shard("c1", {"results": [{"template_id": "x"}], "timed_out": False})
    _completed_shard("c2", {"results": [{"template_id": "y"}], "timed_out": False})
    agg = handle_aggregate_executions({"execution_ids": ["c1", "c2"]})
    assert agg["overall_status"] == "complete"
    assert agg["findings"]["results_count"] == 2


def test_overall_incomplete_on_failure_or_missing():
    _completed_shard("f1", {"results": []}, status="FAILED")
    agg = handle_aggregate_executions({"execution_ids": ["f1", "does-not-exist"]})
    assert agg["overall_status"] == "incomplete"
    assert "does-not-exist" in agg["missing_execution_ids"]


def test_empty_ids_rejected():
    assert "error" in handle_aggregate_executions({"execution_ids": []})
    assert "error" in handle_aggregate_executions({})
