"""MCP-level surface inventory: surface_refs on queue/findings, ingestion on completion."""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from server import TOOLS
from state.reporting import create_engagement
from state.state import transition_execution
from state.surface import list_surface
from tools.complete_execution import handle_complete_execution
from tools.create_reporting_finding import handle_create_reporting_finding
from tools.list_surface_items import handle_list_surface_items
from tools.mark_execution_complete import handle_mark_execution_complete
from tools.request_security_action import REQUEST_SECURITY_ACTION_SCHEMA, handle_request
from tools.update_reporting_finding import handle_update_reporting_finding
from tools.upsert_surface_items import handle_upsert_surface_items


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))
    import audit.audit_manager as am

    monkeypatch.setattr(am, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(am, "update_report", lambda *a, **k: None)


@pytest.fixture
def eid():
    return create_engagement("ExampleCo Web Assessment")["engagement_id"]


def _queue(eid, **over):
    payload = {
        "agent_role": "recon",
        "phase": "reconnaissance",
        "target": "https://app.example.com",
        "action_type": "python",
        "command": "print('hi')",
        "engagement_id": eid,
        "justification": "Map the application's API surface from the public JS bundle before testing.",
        "expected_output": "Endpoint list.",
    }
    payload.update(over)
    return handle_request(payload)


def _run(execution_id, envelope):
    transition_execution(execution_id, "CLAIMED", executor_id="w")
    transition_execution(execution_id, "RUNNING", executor_id="w")
    return handle_complete_execution(
        {"execution_id": execution_id, "executor_id": "w", "result": json.dumps(envelope)}
    )


def _status(eid):
    return {i["key"]: i["status"] for i in list_surface(eid)}


def test_published_schema_declares_surface_refs():
    path = os.path.join(os.path.dirname(__file__), "../../tools/request_security_action.json")
    with open(path, encoding="utf-8") as f:
        published = json.load(f)["inputSchema"]["properties"]
    assert published["surface_refs"]["type"] == "array"
    assert REQUEST_SECURITY_ACTION_SCHEMA["properties"]["surface_refs"]["type"] == "array"
    for tool in ("request_batch", "create_reporting_finding", "update_reporting_finding"):
        assert "surface_refs" in TOOLS[tool]["inputSchema"]["properties"]
    assert {"upsert_surface_items", "list_surface_items"} <= set(TOOLS)


def test_end_to_end_coverage_progression(eid):
    recon = _queue(eid)
    done = _run(
        recon["execution_id"],
        {"skill": "python_sandbox", "findings": {"stdout": "", "endpoints": ["GET /api/users/7"]}},
    )
    assert done["surface_endpoints_ingested"] == 1
    assert _status(eid) == {"GET app.example.com/api/users/{id}": "discovered"}

    enum = _queue(
        eid,
        agent_role="enumeration",
        phase="enumeration",
        surface_refs=["EP-1", "POST /api/users"],
        depends_on=[recon["execution_id"]],
    )
    assert enum["surface_refs"] == ["EP-1", "EP-2"]
    assert set(_status(eid).values()) == {"in_progress"}

    _run(enum["execution_id"], {"skill": "python_sandbox", "findings": {"stdout": ""}})
    assert set(_status(eid).values()) == {"tested"}

    created = handle_create_reporting_finding(
        {"title": "IDOR on user read", "engagement_id": eid, "surface_refs": ["EP-1"]}
    )
    assert created["surface_refs"] == ["EP-1"]
    assert _status(eid)["GET app.example.com/api/users/{id}"] == "vulnerable"

    updated = handle_update_reporting_finding(
        {"finding_id": created["finding"]["finding_id"], "surface_refs": ["EP-2"]}
    )
    assert updated["surface_refs"] == ["EP-2"]
    assert set(_status(eid).values()) == {"vulnerable"}

    listed = handle_list_surface_items({"engagement_id": eid})
    assert listed["endpoint_status_counts"] == {"vulnerable": 2}
    ep1 = next(i for i in listed["items"] if i["ref"] == "EP-1")
    assert ep1["discovered_by"] == [recon["execution_id"]]
    assert ep1["tested_by"] == [enum["execution_id"]]
    assert ep1["phase_counts"] == {"reconnaissance": 1, "enumeration": 1}


def test_unknown_ref_rejects_queue_without_creating_execution(eid):
    from state.storage import load_executions

    result = _queue(eid, surface_refs=["EP-42"])
    assert result["error"] == "Invalid surface_refs"
    assert load_executions() == []


def test_surface_refs_require_engagement():
    result = handle_request(
        {
            "agent_role": "recon",
            "phase": "reconnaissance",
            "target": "app.example.com",
            "action_type": "python",
            "command": "print(1)",
            "justification": "Map the application's API surface from the public JS bundle before testing.",
            "expected_output": "x",
            "surface_refs": ["GET /x"],
        }
    )
    assert result["error"] == "surface_refs requires engagement_id"


def test_finding_with_bad_ref_is_not_created(eid):
    from state.reporting import list_findings

    result = handle_create_reporting_finding(
        {"title": "X", "engagement_id": eid, "surface_refs": ["FN-3"]}
    )
    assert "Unknown surface ref" in result["error"]
    assert list_findings(engagement_id=eid) == []


def test_malformed_envelope_never_fails_completion(eid):
    recon = _queue(eid)
    transition_execution(recon["execution_id"], "CLAIMED", executor_id="w")
    transition_execution(recon["execution_id"], "RUNNING", executor_id="w")
    done = handle_complete_execution(
        {"execution_id": recon["execution_id"], "executor_id": "w", "result": "not json {"}
    )
    assert done["status"] == "COMPLETED"
    assert "surface_endpoints_ingested" not in done


def test_mark_complete_result_override_is_ingested(eid):
    recon = _queue(eid)
    _run(recon["execution_id"], {"skill": "python_sandbox", "findings": {"stdout": ""}})
    out = handle_mark_execution_complete(
        {
            "execution_id": recon["execution_id"],
            "executor_id": "orchestrator",
            "interpretation": "Found the admin API.",
            "result": json.dumps({"findings": {"endpoints": ["GET /admin/users"]}}),
        }
    )
    assert out["surface_endpoints_ingested"] == 1


def test_upsert_tool(eid):
    out = handle_upsert_surface_items(
        {
            "engagement_id": eid,
            "default_host": "app.example.com",
            "items": [
                {"kind": "functionality", "name": "Billing", "attack_surface_ref": "AS-3"},
                {"method": "GET", "url": "/api/invoices/export", "parent": "FN-1"},
            ],
        }
    )
    assert [i["ref"] for i in out["items"]] == ["FN-1", "EP-1"]
    assert handle_upsert_surface_items({"engagement_id": eid, "items": []})["error"]
    listed = handle_list_surface_items({"engagement_id": eid, "kind": "endpoint"})
    assert listed["items"][0]["parent"] == "FN-1"
