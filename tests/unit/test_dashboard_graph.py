import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dashboard.graph import get_engagement_graph
from state.reporting import (
    add_threat_model_entry,
    create_engagement,
    create_finding,
    create_threat_model,
)
from state.state import create_execution


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


def _seed():
    eng = create_engagement("ExampleCo Web Assessment")
    eid = eng["engagement_id"]
    recon = create_execution(
        "exec-recon",
        "app.example.com",
        "reconnaissance",
        {"action_type": "skill", "skill": "network.NmapScan"},
        engagement_id=eid,
    )
    enum = create_execution(
        "exec-enum",
        "app.example.com",
        "enumeration",
        {"action_type": "python", "justification": "Enumerate the export API"},
        engagement_id=eid,
        depends_on=[recon["execution_id"]],
    )
    create_execution(
        "exec-render",
        "ExampleCo Web Assessment",
        "reporting",
        {"action_type": "report_skill", "skill": "reporting.FindingDocxReport"},
        engagement_id=eid,
    )
    create_execution(
        "exec-untagged", "other.example.com", "reconnaissance", {"action_type": "python"}
    )
    backed = create_finding(
        engagement_id=eid,
        title="Missing authorization on export endpoint",
        severity="High",
        source_execution_id=enum["execution_id"],
    )
    via_evidence = create_finding(
        engagement_id=eid,
        title="Verbose error messages",
        severity="Low",
        evidence=[{"title": "Trace", "source_execution_id": "exec-untagged"}],
    )
    orphan = create_finding(engagement_id=eid, title="Weak TLS configuration", severity="Medium")
    tm = create_threat_model(engagement_id=eid, title="ExampleCo TM")
    tm_id = tm["threat_model_id"]
    add_threat_model_entry(tm_id, "asset", ref="CA-1", name="Customer records")
    add_threat_model_entry(tm_id, "terminal_goal", ref="TG-1", name="Bulk data exfiltration")
    add_threat_model_entry(
        tm_id,
        "attack_path",
        ref="AP-1",
        title="IDOR on export",
        priority="High",
        impacted_assets="CA-1, TG-1, CA-9",
        finding_id=backed["finding_id"],
    )
    add_threat_model_entry(
        tm_id, "attack_path", ref="AP-2", title="Session fixation", priority="Critical"
    )
    add_threat_model_entry(tm_id, "attack_path", ref="AP-3", title="Clickjacking", priority="Low")
    return eid, tm_id, backed, via_evidence, orphan


def _by_id(graph):
    return {n["id"]: n for n in graph["nodes"]}


def _rels(graph):
    return {(e["source"], e["target"], e["rel"]) for e in graph["edges"]}


def test_unknown_engagement_returns_none():
    assert get_engagement_graph("does-not-exist") is None


def test_graph_links_targets_executions_findings_and_threat_model():
    eid, tm_id, backed, via_evidence, _ = _seed()
    graph = get_engagement_graph(eid)
    nodes, rels = _by_id(graph), _rels(graph)

    assert "exec:exec-render" not in nodes  # report renders are bookkeeping
    assert nodes["exec:exec-recon"]["label"] == "network.NmapScan"
    assert nodes["exec:exec-enum"]["label"] == "python: Enumerate the export API"

    assert ("target:app.example.com", "exec:exec-recon", "runs") in rels
    assert ("exec:exec-recon", "exec:exec-enum", "depends_on") in rels
    # A dependent hangs off its prerequisite, not the target as well.
    assert ("target:app.example.com", "exec:exec-enum", "runs") not in rels

    assert ("exec:exec-enum", f"finding:{backed['finding_id']}", "evidences") in rels
    assert ("exec:exec-untagged", f"finding:{via_evidence['finding_id']}", "evidences") in rels
    assert ("target:other.example.com", "exec:exec-untagged", "runs") in rels

    ap1 = f"tm:{tm_id}:AP-1"
    assert (f"finding:{backed['finding_id']}", ap1, "proves") in rels
    assert (ap1, f"tm:{tm_id}:CA-1", "impacts") in rels
    assert (ap1, f"tm:{tm_id}:TG-1", "impacts") in rels
    assert not any(e["target"].endswith("CA-9") for e in graph["edges"])  # dangling ref


def test_gap_flags():
    eid, tm_id, backed, via_evidence, orphan = _seed()
    nodes = _by_id(get_engagement_graph(eid))

    assert nodes[f"finding:{orphan['finding_id']}"]["flags"] == ["no_execution"]
    assert nodes[f"finding:{backed['finding_id']}"]["flags"] == []
    assert nodes[f"finding:{via_evidence['finding_id']}"]["flags"] == []
    assert nodes["exec:exec-untagged"]["flags"] == ["untagged"]

    assert nodes[f"tm:{tm_id}:AP-1"]["flags"] == []
    assert nodes[f"tm:{tm_id}:AP-2"]["flags"] == ["unevidenced"]
    assert nodes[f"tm:{tm_id}:AP-3"]["flags"] == []  # low priority: not a gap


def test_findings_not_flagged_when_engagement_has_no_executions():
    eng = create_engagement("Source Code Review")
    finding = create_finding(
        engagement_id=eng["engagement_id"], title="Hardcoded key", severity="High"
    )
    nodes = _by_id(get_engagement_graph(eng["engagement_id"]))
    assert nodes[f"finding:{finding['finding_id']}"]["flags"] == []
