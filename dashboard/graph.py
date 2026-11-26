"""Engagement evidence graph — derived, read-only view over existing links.

Builds ``{nodes, edges, stats}`` for one engagement from relationships that
already exist in the schema; nothing here writes state:

- target → execution        ``executions.target`` (roots of each dependency chain)
- execution → execution     ``executions.depends_on`` (playbooks / sequential batches)
- execution → finding       ``findings.source_execution_id`` + ``finding_evidence.source_execution_id``
- execution → attack path   ``tm_attack_paths.source_execution_id``
- finding → attack path     ``tm_attack_paths.finding_id``
- attack path → asset/goal  ref strings in ``tm_attack_paths.impacted_assets`` ("CA-1, CA-4")

Gaps are flagged on the nodes (``flags``) so the UI can outline them: a report
finding with no execution behind it, a High/Critical attack path with no
evidence, an execution linked from the report but not tagged to the engagement.
"""

import re

from dashboard.api import _parse_request
from state.reporting import get_engagement, get_threat_model, list_findings, list_threat_models
from state.storage import load_executions
from state.surface import list_surface

_REF_RE = re.compile(r"\b[A-Z]{1,4}-\d+\b")
_HIGH_PRIORITIES = {"high", "critical"}
_LABEL_MAX = 60


def _short(text, limit=_LABEL_MAX):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _execution_label(execution, request):
    """Skill name when there is one; otherwise the first words of the justification."""
    skill = request.get("skill")
    if skill:
        return skill
    action_type = request.get("action_type") or "execution"
    justification = request.get("justification") or request.get("mission")
    return f"{action_type}: {_short(justification, 48)}" if justification else action_type


def _execution_node(execution):
    request = _parse_request(execution.get("request")) or {}
    return {
        "id": f"exec:{execution['execution_id']}",
        "kind": "execution",
        "label": _execution_label(execution, request),
        "execution_id": execution["execution_id"],
        "target": execution.get("target"),
        "phase": execution.get("security_phase"),
        "status": execution.get("status"),
        "created_at": execution.get("created_at"),
        "has_interpretation": bool(execution.get("interpretation")),
        "flags": [],
    }


def _finding_node(finding):
    return {
        "id": f"finding:{finding['finding_id']}",
        "kind": "finding",
        "label": _short(finding.get("title")),
        "finding_id": finding["finding_id"],
        "severity": finding.get("severity"),
        "status": finding.get("status"),
        "affected": finding.get("affected"),
        "flags": [],
    }


def _finding_sources(finding):
    """Execution ids a finding cites: its source plus each evidence item's."""
    sources = [finding.get("source_execution_id")]
    sources += [ev.get("source_execution_id") for ev in finding.get("evidence", [])]
    return [s for s in sources if s]


def _attack_path_node(path, model):
    return {
        "id": f"tm:{model['threat_model_id']}:{path['ref']}",
        "kind": "attack_path",
        "label": f"{path['ref']} {_short(path.get('title'), 50)}".strip(),
        "ref": path["ref"],
        "priority": path.get("priority"),
        "likelihood": path.get("likelihood"),
        "impact": path.get("impact"),
        "description": path.get("description"),
        "threat_model": model.get("title"),
        "flags": [],
    }


def _surface_id(item):
    return f"surface:{item['item_id']}"


def _surface_node(item):
    if item["kind"] == "functionality":
        label = f"{item['ref']} {_short(item['name'], 50)}"
    else:
        label = f"{item['ref']} {_short(item['key'], 60)}"
    return {
        "id": _surface_id(item),
        "kind": item["kind"],
        "label": label,
        "item_id": item["item_id"],
        "ref": item["ref"],
        "key": item["key"] if item["kind"] == "endpoint" else None,
        "status": item["status"],
        "attack_surface_ref": item.get("attack_surface_ref"),
        "description": item.get("description"),
        "flags": (
            ["untested"] if item["kind"] == "endpoint" and item["status"] == "discovered" else []
        ),
    }


def _surface_edges(item, add_edge, ensure_execution):
    """discovered: exec → item; tested: item → exec; affects: item → finding."""
    node_id = _surface_id(item)
    if item.get("parent_id"):
        add_edge(f"surface:{item['parent_id']}", node_id, "contains")
    for link in item["links"]:
        if link["rel"] == "affects" and link.get("finding_id"):
            add_edge(node_id, f"finding:{link['finding_id']}", "affects")
            continue
        exec_node = ensure_execution(link["execution_id"]) if link.get("execution_id") else None
        if not exec_node:
            continue
        if link["rel"] == "discovered":
            add_edge(exec_node, node_id, "discovers")
        elif link["rel"] == "tested":
            add_edge(node_id, exec_node, "tested_by")


def get_engagement_graph(engagement_id, include_surface=False):
    """Node/edge payload for the engagement workspace graph, or None if unknown.

    ``include_surface`` adds the engagement's surface items (endpoints and
    functionalities) with their discovered/tested/affects links.
    """
    if not get_engagement(engagement_id):
        return None

    nodes: dict[str, dict] = {}
    edges: dict[tuple, dict] = {}

    def add_edge(src, dst, rel):
        if src in nodes and dst in nodes and src != dst:
            edges.setdefault((src, dst, rel), {"source": src, "target": dst, "rel": rel})

    all_execs = {e["execution_id"]: e for e in load_executions()}

    def ensure_execution(execution_id):
        """Pull in an execution referenced from the report even if it isn't tagged."""
        node_id = f"exec:{execution_id}"
        if node_id in nodes:
            return node_id
        execution = all_execs.get(execution_id)
        if not execution:
            return None
        node = _execution_node(execution)
        node["flags"].append("untagged")
        nodes[node_id] = node
        _ensure_target(execution.get("target"))
        add_edge(f"target:{execution.get('target')}", node_id, "runs")
        return node_id

    def _ensure_target(target):
        node_id = f"target:{target}"
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "kind": "target", "label": target, "flags": []}
        return node_id

    # Executions tagged to the engagement (report renders are bookkeeping, not evidence).
    scoped = [
        e
        for e in all_execs.values()
        if e.get("engagement_id") == engagement_id
        and (_parse_request(e.get("request")) or {}).get("action_type") != "report_skill"
    ]
    for execution in scoped:
        nodes[f"exec:{execution['execution_id']}"] = _execution_node(execution)
        _ensure_target(execution.get("target"))
    for execution in scoped:
        node_id = f"exec:{execution['execution_id']}"
        deps = [d for d in (execution.get("depends_on") or []) if f"exec:{d}" in nodes]
        for dep in deps:
            add_edge(f"exec:{dep}", node_id, "depends_on")
        if not deps:
            add_edge(f"target:{execution.get('target')}", node_id, "runs")

    # Report findings and the executions that back them.
    for finding in list_findings(engagement_id=engagement_id, include_evidence=True):
        node_id = f"finding:{finding['finding_id']}"
        nodes[node_id] = _finding_node(finding)
        for execution_id in _finding_sources(finding):
            exec_node = ensure_execution(execution_id)
            if exec_node:
                add_edge(exec_node, node_id, "evidences")

    # Threat-model attack paths, their evidence, and the assets/goals they impact.
    for summary in list_threat_models(engagement_id=engagement_id):
        model = get_threat_model(summary["threat_model_id"])
        if not model:
            continue
        tm_id = model["threat_model_id"]
        entries = model.get("entries", {})
        by_ref = {}
        for entity_type, kind in (("asset", "asset"), ("terminal_goal", "goal")):
            for entry in entries.get(entity_type, []):
                node_id = f"tm:{tm_id}:{entry['ref']}"
                nodes[node_id] = {
                    "id": node_id,
                    "kind": kind,
                    "label": f"{entry['ref']} {_short(entry.get('name'), 40)}".strip(),
                    "ref": entry["ref"],
                    "description": entry.get("description"),
                    "threat_model": model.get("title"),
                    "flags": [],
                }
                by_ref[entry["ref"].upper()] = node_id
        for path in entries.get("attack_path", []):
            node_id = f"tm:{tm_id}:{path['ref']}"
            nodes[node_id] = _attack_path_node(path, model)
            if path.get("source_execution_id"):
                exec_node = ensure_execution(path["source_execution_id"])
                if exec_node:
                    add_edge(exec_node, node_id, "evidences")
            if path.get("finding_id"):
                add_edge(f"finding:{path['finding_id']}", node_id, "proves")
            for ref in _REF_RE.findall(path.get("impacted_assets") or ""):
                if ref.upper() in by_ref:
                    add_edge(node_id, by_ref[ref.upper()], "impacts")

    # Surface items (opt-in: they swamp a large engagement's graph).
    if include_surface:
        for item in list_surface(engagement_id):
            nodes[_surface_id(item)] = _surface_node(item)
        for item in list_surface(engagement_id):
            _surface_edges(item, add_edge, ensure_execution)

    # Gap flags: anything the report or threat model claims without a linked source.
    # An engagement with no executions at all (e.g. a code review done outside
    # Taskmaster) has nothing to link to, so unbacked findings aren't a gap there.
    incoming = {}
    for edge in edges.values():
        incoming.setdefault(edge["target"], set()).add(edge["rel"])
    has_executions = any(n["kind"] == "execution" for n in nodes.values())
    for node in nodes.values():
        rels = incoming.get(node["id"], set())
        if node["kind"] == "finding" and has_executions and "evidences" not in rels:
            node["flags"].append("no_execution")
        elif node["kind"] == "attack_path" and not rels & {"evidences", "proves"}:
            if str(node.get("priority") or "").lower() in _HIGH_PRIORITIES:
                node["flags"].append("unevidenced")
        elif (
            node["kind"] == "execution"
            and node["status"] == "COMPLETED"
            and not node["has_interpretation"]
        ):
            node["flags"].append("no_interpretation")

    node_list = list(nodes.values())
    return {
        "engagement_id": engagement_id,
        "nodes": node_list,
        "edges": list(edges.values()),
        "stats": {
            "nodes": len(node_list),
            "edges": len(edges),
            "flagged": sum(1 for n in node_list if n["flags"]),
        },
    }


def get_surface_lineage_graph(engagement_id, item_id):
    """Lineage for one surface item, or None if unknown.

    The item (plus its functionality parent, or its endpoints if it is a
    functionality) → the executions that discovered and tested it (with
    ``depends_on`` between them) → the findings it affects and the executions
    backing those → attack paths proven by those findings or abusing the item's
    ``attack_surface_ref``.
    """
    items = {i["item_id"]: i for i in list_surface(engagement_id)}
    focus = items.get(item_id)
    if not focus:
        return None

    scope = [focus]
    if focus["kind"] == "functionality":
        scope += [i for i in items.values() if i.get("parent_id") == item_id]
    elif focus.get("parent_id") in items:
        scope.append(items[focus["parent_id"]])

    nodes: dict[str, dict] = {}
    edges: dict[tuple, dict] = {}

    def add_edge(src, dst, rel):
        if src in nodes and dst in nodes and src != dst:
            edges.setdefault((src, dst, rel), {"source": src, "target": dst, "rel": rel})

    all_execs = {e["execution_id"]: e for e in load_executions()}

    def ensure_execution(execution_id):
        node_id = f"exec:{execution_id}"
        if node_id not in nodes and execution_id in all_execs:
            nodes[node_id] = _execution_node(all_execs[execution_id])
        return node_id if node_id in nodes else None

    for item in scope:
        node = _surface_node(item)
        node["focus"] = item["item_id"] == item_id
        nodes[node["id"]] = node

    findings = {f["finding_id"]: f for f in list_findings(engagement_id=engagement_id)}
    for item in scope:
        for link in item["links"]:
            finding = findings.get(link.get("finding_id"))
            if link["rel"] == "affects" and finding:
                nodes[f"finding:{finding['finding_id']}"] = _finding_node(finding)
                for execution_id in _finding_sources(finding):
                    exec_node = ensure_execution(execution_id)
                    if exec_node:
                        add_edge(exec_node, f"finding:{finding['finding_id']}", "evidences")
        _surface_edges(item, add_edge, ensure_execution)

    for node in list(nodes.values()):
        if node["kind"] != "execution":
            continue
        for dep in all_execs[node["execution_id"]].get("depends_on") or []:
            add_edge(f"exec:{dep}", node["id"], "depends_on")

    surface_refs = {i["attack_surface_ref"].upper() for i in scope if i.get("attack_surface_ref")}
    for summary in list_threat_models(engagement_id=engagement_id):
        model = get_threat_model(summary["threat_model_id"])
        for path in (model or {}).get("entries", {}).get("attack_path", []):
            abused = {r.upper() for r in _REF_RE.findall(path.get("abused_surface") or "")}
            proven_by = f"finding:{path.get('finding_id')}"
            if proven_by not in nodes and not abused & surface_refs:
                continue
            ap = _attack_path_node(path, model)
            nodes[ap["id"]] = ap
            add_edge(proven_by, ap["id"], "proves")
            for item in scope:
                if (item.get("attack_surface_ref") or "").upper() in abused:
                    add_edge(_surface_id(item), ap["id"], "abused_in")

    node_list = list(nodes.values())
    return {
        "engagement_id": engagement_id,
        "item_id": item_id,
        "nodes": node_list,
        "edges": list(edges.values()),
        "stats": {
            "nodes": len(node_list),
            "edges": len(edges),
            "flagged": sum(1 for n in node_list if n["flags"]),
        },
    }
