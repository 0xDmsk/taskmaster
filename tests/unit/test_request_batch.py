"""Tests for request_batch — fan one skill out over many bounded shards."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from state.state import get_queued_executions
from state.storage import load_executions
from tools.request_batch import handle_request_batch


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))
    import audit.audit_manager as am

    monkeypatch.setattr(am, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(am, "update_report", lambda *a, **k: None)


def _base(**over):
    step = {
        "action_type": "skill",
        "phase": "reconnaissance",
        "agent_role": "recon",
        "skill": "subdomain.SubfinderEnum",
        "justification": (
            "Fan passive subdomain enumeration across the in-scope domains so each "
            "domain is a bounded execution that fits the window."
        ),
        "expected_output": "Discovered subdomains per domain.",
    }
    step.update(over)
    return step


def test_parallel_fan_out_across_targets_has_no_deps():
    result = handle_request_batch(
        _base(shards=[{"target": "a.com"}, {"target": "b.com"}, {"target": "c.com"}])
    )
    assert result["status"] == "QUEUED"
    assert result["mode"] == "parallel"
    assert result["count"] == 3

    execs = {e["execution_id"]: e for e in load_executions()}
    for eid in result["execution_ids"]:
        assert not execs[eid].get("depends_on")
    # Different targets → all three are offered to workers at once.
    ready = {e["execution_id"] for e in get_queued_executions()}
    assert ready == set(result["execution_ids"])
    assert {execs[e]["target"] for e in result["execution_ids"]} == {"a.com", "b.com", "c.com"}


def test_sequential_same_target_chains_shards():
    # A full nuclei scan split by template group, all against one target.
    result = handle_request_batch(
        _base(
            action_type="mobile_skill",
            phase="reconnaissance",
            skill="mobile.MobileNucleiScan",
            target="com.example.app",
            arguments={"source_dir": "/loot/x"},
            sequential=True,
            shards=[
                {"label": "android", "arguments": {"templates": "/t/Android"}},
                {"label": "keys", "arguments": {"templates": "/t/Keys"}},
            ],
        )
    )
    assert result["status"] == "QUEUED"
    assert result["mode"] == "sequential"
    ids = result["execution_ids"]
    assert len(ids) == 2

    execs = {e["execution_id"]: e for e in load_executions()}
    assert not execs[ids[0]].get("depends_on")
    assert execs[ids[1]]["depends_on"] == [ids[0]]
    # Only the first shard is offered; the second is gated on it.
    ready = {e["execution_id"] for e in get_queued_executions()}
    assert ready == {ids[0]}


def test_shard_arguments_merge_over_base():
    result = handle_request_batch(
        _base(
            action_type="mobile_skill",
            skill="mobile.MobileNucleiScan",
            target="com.example.app",
            arguments={"source_dir": "/loot/x", "timeout": 300},
            sequential=True,
            shards=[{"arguments": {"templates": "/t/Android", "timeout": 600}}],
        )
    )
    assert result["status"] == "QUEUED"
    eid = result["execution_ids"][0]
    execs = {e["execution_id"]: e for e in load_executions()}
    import json

    req = execs[eid]["request"]
    req = json.loads(req) if isinstance(req, str) else req
    args = req["arguments"]
    assert args["source_dir"] == "/loot/x"  # from base
    assert args["templates"] == "/t/Android"  # from shard
    assert args["timeout"] == 600  # shard overrides base


def test_empty_shards_rejected():
    assert "error" in handle_request_batch(_base(shards=[]))
    assert "error" in handle_request_batch(_base())


def test_shard_without_target_rejected():
    result = handle_request_batch(
        _base(shards=[{"arguments": {}}])
    )  # no base target, no shard target
    assert "error" in result
    assert "target" in result["error"]
