import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dashboard import render
from dashboard.api import get_engagement_surface
from dashboard.graph import get_engagement_graph, get_surface_lineage_graph
from dashboard.webapp import ROUTER
from state.reporting import (
    add_threat_model_entry,
    create_engagement,
    create_finding,
    create_threat_model,
)
from state.state import create_execution
from state.surface import link_surface, upsert_surface_items


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


@pytest.fixture
def seeded():
    eid = create_engagement("ExampleCo Web Assessment")["engagement_id"]
    fn, export, search, orphan = upsert_surface_items(
        eid,
        [
            {"kind": "functionality", "name": "Account export", "attack_surface_ref": "AS-2"},
            {"url": "GET https://app.example.com/api/export", "parent": "FN-1"},
            {"url": "POST https://app.example.com/api/search", "parent": "FN-1"},
            "GET https://app.example.com/health",
        ],
    )
    create_execution(
        "recon",
        "app.example.com",
        "reconnaissance",
        {"action_type": "skill", "skill": "web.FfufFuzz"},
        engagement_id=eid,
    )
    create_execution(
        "enum",
        "app.example.com",
        "enumeration",
        {"action_type": "python"},
        engagement_id=eid,
        depends_on=["recon"],
    )
    link_surface([export["item_id"], search["item_id"]], "discovered", execution_id="recon")
    link_surface([export["item_id"]], "tested", execution_id="enum")
    finding = create_finding(
        engagement_id=eid, title="IDOR on export", severity="High", source_execution_id="enum"
    )
    link_surface([export["item_id"]], "affects", finding_id=finding["finding_id"])
    tm = create_threat_model(engagement_id=eid, title="TM")
    add_threat_model_entry(
        tm["threat_model_id"],
        "attack_path",
        ref="AP-1",
        title="Bulk export abuse",
        abused_surface="AS-2",
    )
    return {
        "eid": eid,
        "fn": fn,
        "export": export,
        "search": search,
        "orphan": orphan,
        "finding": finding,
        "tm": tm,
    }


def test_matrix_groups_rows_and_counts(seeded):
    surface = get_engagement_surface(seeded["eid"])
    assert surface["status_counts"] == {
        "vulnerable": 1,
        "tested": 0,
        "in_progress": 0,
        "discovered": 2,
    }
    fn_group, unassigned = surface["groups"]
    assert fn_group["item"]["ref"] == "FN-1"
    assert (fn_group["covered"], fn_group["total"]) == (1, 2)
    export = next(r for r in fn_group["rows"] if r["ref"] == "EP-1")
    assert export["discovered_by"] == 1
    assert export["phase_counts"] == [1, 1, 0, 0]
    assert export["findings"][0]["severity"] == "High"
    assert unassigned["item"] is None
    assert [r["ref"] for r in unassigned["rows"]] == ["EP-3"]


def test_matrix_filters(seeded):
    only_vuln = get_engagement_surface(seeded["eid"], status="vulnerable")
    assert [r["ref"] for g in only_vuln["groups"] for r in g["rows"]] == ["EP-1"]
    assert only_vuln["status_counts"]["discovered"] == 2  # summary ignores filters
    by_text = get_engagement_surface(seeded["eid"], query="health")
    assert [r["ref"] for g in by_text["groups"] for r in g["rows"]] == ["EP-3"]
    assert get_engagement_surface("eng_missing") is None


def test_lineage_graph_for_endpoint(seeded):
    graph = get_surface_lineage_graph(seeded["eid"], seeded["export"]["item_id"])
    nodes = {n["id"]: n for n in graph["nodes"]}
    rels = {(e["source"], e["target"], e["rel"]) for e in graph["edges"]}
    ep, fn = f"surface:{seeded['export']['item_id']}", f"surface:{seeded['fn']['item_id']}"
    finding = f"finding:{seeded['finding']['finding_id']}"
    assert nodes[ep]["focus"] and not nodes[fn]["focus"]
    assert {
        (fn, ep, "contains"),
        ("exec:recon", ep, "discovers"),
        (ep, "exec:enum", "tested_by"),
        ("exec:recon", "exec:enum", "depends_on"),
        (ep, finding, "affects"),
        ("exec:enum", finding, "evidences"),
        (fn, f"tm:{seeded['tm']['threat_model_id']}:AP-1", "abused_in"),
    } <= rels
    assert f"surface:{seeded['orphan']['item_id']}" not in nodes
    assert get_surface_lineage_graph(seeded["eid"], "srf_missing") is None


def test_lineage_graph_for_functionality_includes_children(seeded):
    graph = get_surface_lineage_graph(seeded["eid"], seeded["fn"]["item_id"])
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert f"surface:{seeded['search']['item_id']}" in nodes
    # EP-2 was only discovered, never tested: flagged as a gap.
    assert nodes[f"surface:{seeded['search']['item_id']}"]["flags"] == ["untested"]


def test_evidence_graph_surface_layer_is_opt_in(seeded):
    plain = get_engagement_graph(seeded["eid"])
    assert not [n for n in plain["nodes"] if n["kind"] in ("endpoint", "functionality")]
    layered = get_engagement_graph(seeded["eid"], include_surface=True)
    kinds = {n["id"]: n for n in layered["nodes"]}
    orphan = kinds[f"surface:{seeded['orphan']['item_id']}"]
    assert orphan["kind"] == "endpoint" and orphan["flags"] == ["untested"]


def test_routes_and_template_render(seeded):
    eid = seeded["eid"]
    assert (
        ROUTER.match("GET", f"/reporting/engagements/{eid}/surface")[0] == "page_engagement_surface"
    )
    assert ROUTER.match("GET", f"/reporting/engagements/{eid}")[0] == "page_engagement_workspace"
    assert (
        ROUTER.match("GET", f"/api/reporting/engagements/{eid}/surface/srf_x/graph")[0]
        == "api_surface_lineage_graph"
    )
    html = render(
        "engagement_surface.html",
        page="engagements",
        stats={},
        surface=get_engagement_surface(eid),
        filters={"status": None, "q": None},
    )
    assert "Surface Coverage" in html and "/api/x" not in html
    assert "app.example.com/api/export" in html
    assert 'data-item-id="' + seeded["export"]["item_id"] + '"' in html
