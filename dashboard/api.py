"""REST API handlers — pure functions returning dicts for JSON or template rendering."""

import json
import logging
import os

import config
from state.storage import load_executions, get_execution_by_id
from state.reporting import (
    FINDING_STATUSES,
    SEVERITIES,
    get_engagement,
    get_finding,
    list_assets,
    list_engagements,
    list_findings,
)

logger = logging.getLogger(__name__)

PHASES = ["reconnaissance", "enumeration", "exploitation", "post_exploitation", "reporting"]
SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Info"]
STATUS_ORDER = [
    "draft",
    "needs_review",
    "confirmed",
    "reported",
    "accepted_risk",
    "false_positive",
]
# Statuses that mean the finding is no longer actively worked on.
CLOSED_STATUSES = {"reported", "accepted_risk", "false_positive"}


def _scope_executions(execs, engagement_id):
    """Filter executions to those tagged with the engagement (no-op if None).

    Executions are bound to an engagement explicitly via their ``engagement_id``
    (set at queue time through ``request_security_action`` / ``request_reporting_docx``,
    or reassigned from the dashboard). Untagged executions never appear under an
    engagement scope; they show only under "All engagements".
    """
    if not engagement_id:
        return execs
    return [e for e in execs if e.get("engagement_id") == engagement_id]


def get_stats(engagement_id=None):
    """Summary counters across executions plus report-finding rollups.

    When ``engagement_id`` is set, both the execution counters and the finding
    rollup are scoped to that engagement.
    """
    execs = _scope_executions(load_executions(), engagement_id)
    counts = {
        "total": len(execs),
        "QUEUED": 0,
        "CLAIMED": 0,
        "RUNNING": 0,
        "COMPLETED": 0,
        "FAILED": 0,
    }
    for e in execs:
        s = e.get("status", "QUEUED")
        if s in counts:
            counts[s] += 1

    findings = list_findings(engagement_id=engagement_id or None, include_evidence=False)
    counts["findings"] = {
        "total": len(findings),
        "open": sum(1 for f in findings if f.get("status") not in CLOSED_STATUSES),
        "reported": sum(1 for f in findings if f.get("status") == "reported"),
        "severity": _severity_counts(findings),
    }
    return counts


def _severity_counts(findings):
    """Count findings per severity, in Critical→Info order."""
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for f in findings:
        sev = f.get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts


def _status_counts(findings):
    """Count findings per workflow status, in pipeline order."""
    counts = {status: 0 for status in STATUS_ORDER}
    for f in findings:
        status = f.get("status")
        if status in counts:
            counts[status] += 1
    return counts


def _filter_findings(findings, status=None, severity=None, query=None):
    """Apply the shared status/severity/text filters to a finding list."""
    if status:
        findings = [f for f in findings if f.get("status") == status]
    if severity:
        findings = [f for f in findings if f.get("severity") == severity]
    if query:
        needle = query.lower()
        findings = [
            f
            for f in findings
            if needle in (f.get("title") or "").lower()
            or needle in (f.get("affected") or "").lower()
            or needle in (f.get("description") or "").lower()
        ]
    return findings


def get_executions(status=None, target=None, phase=None, engagement_id=None):
    """Filtered execution list, optionally scoped to an engagement."""
    execs = _scope_executions(load_executions(), engagement_id)
    if status:
        execs = [e for e in execs if e.get("status") == status]
    if target:
        execs = [e for e in execs if e.get("target") == target]
    if phase:
        execs = [e for e in execs if e.get("security_phase") == phase]
    # Most recent first
    execs.reverse()
    return execs


def get_execution(execution_id):
    """Single execution detail."""
    return get_execution_by_id(execution_id)


def get_targets():
    """Per-target aggregated stats with phase progress."""
    execs = load_executions()
    targets = {}
    for e in execs:
        t = e.get("target", "unknown")
        if t not in targets:
            targets[t] = {
                "target": t,
                "total": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "queued": 0,
                "phases": {p: {"total": 0, "completed": 0} for p in PHASES},
            }
        info = targets[t]
        info["total"] += 1
        s = e.get("status", "QUEUED")
        if s == "COMPLETED":
            info["completed"] += 1
        elif s == "FAILED":
            info["failed"] += 1
        elif s == "RUNNING":
            info["running"] += 1
        elif s in ("QUEUED", "CLAIMED"):
            info["queued"] += 1
        phase = e.get("security_phase", "")
        if phase in info["phases"]:
            info["phases"][phase]["total"] += 1
            if s == "COMPLETED":
                info["phases"][phase]["completed"] += 1
    return list(targets.values())


def _parse_result(raw):
    """Parse a result field that may be a JSON string or dict."""
    if not raw:
        return None
    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None
    return result if isinstance(result, dict) else None


def _parse_request(raw):
    """Parse a request field that may be a JSON string or dict."""
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def get_execution_detail(execution_id):
    """Full execution with parsed request + result."""
    e = get_execution_by_id(execution_id)
    if not e:
        return None
    detail = dict(e)
    detail["parsed_request"] = _parse_request(e.get("request")) or {}
    detail["parsed_result"] = _parse_result(e.get("result")) or {}
    detail["interpretation"] = e.get("interpretation")
    return detail


def get_target_detail(target):
    """All executions for a target grouped by phase, with stats."""
    execs = load_executions()
    target_execs = [e for e in execs if e.get("target") == target]
    if not target_execs:
        return None

    by_phase = {p: [] for p in PHASES}
    stats = {"total": 0, "completed": 0, "failed": 0, "running": 0, "queued": 0}
    for e in target_execs:
        stats["total"] += 1
        s = e.get("status", "QUEUED")
        if s == "COMPLETED":
            stats["completed"] += 1
        elif s == "FAILED":
            stats["failed"] += 1
        elif s == "RUNNING":
            stats["running"] += 1
        elif s in ("QUEUED", "CLAIMED"):
            stats["queued"] += 1
        phase = e.get("security_phase", "")
        if phase in by_phase:
            by_phase[phase].append(e)

    return {"target": target, "stats": stats, "by_phase": by_phase, "phases": PHASES}


def get_observations(engagement_id=None):
    """Extract execution observations from completed execution envelopes.

    Worker envelopes still use the historical ``findings`` key. The dashboard
    calls those values observations so "finding" can mean a curated report
    finding everywhere user-facing. Optionally scoped to an engagement.
    """
    execs = _scope_executions(load_executions(), engagement_id)
    observations = []
    for e in execs:
        if e.get("status") != "COMPLETED":
            continue
        result = _parse_result(e.get("result"))
        if not result:
            continue
        entry_observations = result.get("findings", [])
        artifacts = result.get("artifacts", [])
        interpretation = e.get("interpretation")
        if not entry_observations and not artifacts and not interpretation:
            continue

        request = _parse_request(e.get("request")) or {}

        # Extract report-like fields from legacy execution output if present.
        severity = None
        cvss = None
        risk = None
        remediation = None
        references = None
        description = None
        if isinstance(entry_observations, dict):
            severity = entry_observations.get("severity")
            cvss = entry_observations.get("cvss")
            risk = entry_observations.get("risk")
            remediation = entry_observations.get("remediation")
            references = entry_observations.get("references")
            description = entry_observations.get("description")

        observations.append(
            {
                "execution_id": e.get("execution_id"),
                "target": e.get("target"),
                "phase": e.get("security_phase"),
                "skill": result.get("skill", "unknown"),
                "observations": entry_observations,
                "findings": entry_observations,  # legacy API compatibility
                "artifacts": artifacts,
                "errors": result.get("errors", []),
                "executor_id": e.get("executor_id"),
                "justification": request.get("justification"),
                "tool": result.get("tool"),
                "severity": severity,
                "cvss": cvss,
                "risk": risk,
                "remediation": remediation,
                "references": references,
                "description": description,
                "interpretation": e.get("interpretation"),
            }
        )
    return observations


def get_findings():
    """Compatibility alias for legacy dashboard/API callers."""
    return get_observations()


def get_report_finding_options():
    """Dropdown values for the report finding UI."""
    return {
        "engagements": list_engagements(),
        "severities": [severity for severity in SEVERITY_ORDER if severity in SEVERITIES],
        "statuses": [status for status in STATUS_ORDER if status in FINDING_STATUSES],
        "categories": ["Web", "API", "Cloud", "Infra", "Mobile", "General"],
    }


def get_report_findings(engagement_id=None, status=None, severity=None, query=None):
    """List canonical report findings for the dashboard."""
    findings = list_findings(
        engagement_id=engagement_id or None,
        status=status or None,
        include_evidence=True,
    )
    findings = _filter_findings(findings, severity=severity or None, query=query or None)

    engagements = {item["engagement_id"]: item for item in list_engagements()}
    for finding in findings:
        finding["engagement"] = engagements.get(finding.get("engagement_id"))
        finding["evidence_count"] = len(finding.get("evidence", []))
        finding["reference_count"] = len(finding.get("references", []))
    return findings


def get_report_finding_detail(finding_id):
    """Return one canonical report finding with engagement metadata."""
    finding = get_finding(finding_id)
    if not finding:
        return None
    engagement_id = finding.get("engagement_id")
    finding["engagement"] = None
    if engagement_id:
        finding["engagement"] = next(
            (
                engagement
                for engagement in list_engagements()
                if engagement["engagement_id"] == engagement_id
            ),
            None,
        )
    return finding


# --------------------------------------------------------------------------- #
# Engagement workspace                                                         #
# --------------------------------------------------------------------------- #


def get_engagements_overview():
    """List engagements annotated with finding/severity/asset rollups."""
    engagements = list_engagements()
    findings = list_findings(include_evidence=False)
    assets = list_assets()

    findings_by_eng = {}
    for f in findings:
        findings_by_eng.setdefault(f.get("engagement_id"), []).append(f)
    assets_by_eng = {}
    for a in assets:
        assets_by_eng.setdefault(a.get("engagement_id"), []).append(a)

    overview = []
    for engagement in engagements:
        eid = engagement["engagement_id"]
        eng_findings = findings_by_eng.get(eid, [])
        overview.append(
            {
                **engagement,
                "finding_total": len(eng_findings),
                "open_count": sum(
                    1 for f in eng_findings if f.get("status") not in CLOSED_STATUSES
                ),
                "severity_counts": _severity_counts(eng_findings),
                "status_counts": _status_counts(eng_findings),
                "asset_count": len(assets_by_eng.get(eid, [])),
            }
        )
    return overview


def get_engagement_workspace(engagement_id, status=None, severity=None, query=None):
    """Full workspace payload for a single engagement.

    Severity/status rollups are computed across *all* the engagement's findings;
    the ``findings`` list reflects the active status/severity/text filters so the
    summary bar stays stable while the list narrows.
    """
    engagement = get_engagement(engagement_id)
    if not engagement:
        return None

    all_findings = list_findings(engagement_id=engagement_id, include_evidence=True)
    findings = _filter_findings(all_findings, status=status, severity=severity, query=query)
    for finding in findings:
        finding["evidence_count"] = len(finding.get("evidence", []))
        finding["reference_count"] = len(finding.get("references", []))

    return {
        "engagement": engagement,
        "assets": list_assets(engagement_id),
        "findings": findings,
        "finding_total": len(all_findings),
        "open_count": sum(1 for f in all_findings if f.get("status") not in CLOSED_STATUSES),
        "severity_counts": _severity_counts(all_findings),
        "status_counts": _status_counts(all_findings),
        "renders": get_engagement_renders(engagement),
    }


def get_engagement_findings(engagement_id, status=None, severity=None, query=None):
    """Filtered finding list for an engagement (htmx partial swaps)."""
    findings = list_findings(engagement_id=engagement_id, include_evidence=True)
    findings = _filter_findings(findings, status=status, severity=severity, query=query)
    for finding in findings:
        finding["evidence_count"] = len(finding.get("evidence", []))
        finding["reference_count"] = len(finding.get("references", []))
    return findings


def get_engagement_renders(engagement):
    """Rendered-DOCX history for an engagement, from reporting executions.

    Render requests are queued as normal executions with ``action_type``
    ``report_skill`` (see tools/request_reporting_docx.py); the DOCX path lands
    in the execution result envelope, not in a dedicated table. New renders are
    tagged with the engagement_id; legacy renders are matched on the execution
    target (set to the engagement slug or name).
    """
    engagement_id = engagement.get("engagement_id")
    targets = {t for t in (engagement.get("slug"), engagement.get("name")) if t}

    renders = []
    for e in load_executions():
        request = _parse_request(e.get("request")) or {}
        if request.get("action_type") != "report_skill":
            continue
        if e.get("engagement_id") != engagement_id and e.get("target") not in targets:
            continue
        result = _parse_result(e.get("result")) or {}
        renders.append(
            {
                "execution_id": e.get("execution_id"),
                "status": e.get("status", "QUEUED"),
                "created_at": e.get("created_at"),
                "updated_at": e.get("updated_at"),
                "artifacts": _render_artifacts(result),
            }
        )
    renders.reverse()  # newest first
    return renders


def _render_artifacts(result):
    """Ordered artifact paths for a report execution result envelope.

    The DOCX ``output_path`` (emitted inside the ``findings`` dict) is surfaced
    first when it is not already listed under ``artifacts``.
    """
    artifacts = list(result.get("artifacts", []))
    envelope_findings = result.get("findings")
    if isinstance(envelope_findings, dict):
        output_path = envelope_findings.get("output_path")
        if output_path and output_path not in artifacts:
            artifacts.insert(0, output_path)
    return artifacts


def resolve_artifact_host_path(artifact):
    """Map a container/host artifact path to a real host file under runtime dirs.

    Rendered deliverables live under ``runtime/reports`` (container ``/reports``)
    and tool loot under ``runtime/loot`` (container ``/loot``). Any path that
    resolves outside those roots, or does not point at an existing file, returns
    None so the caller can 404 instead of leaking arbitrary files.
    """
    if not artifact:
        return None

    candidates = []
    if artifact.startswith("/reports/"):
        candidates.append(os.path.join(config.REPORTS_DIR, artifact[len("/reports/") :]))
    elif artifact.startswith("/loot/"):
        candidates.append(os.path.join(config.LOOT_DIR, artifact[len("/loot/") :]))
    elif os.path.isabs(artifact):
        candidates.append(artifact)
    else:
        candidates.append(os.path.join(config.WORK_DIR, artifact))
    # Fallback: match by basename inside the reports dir (host-side renders).
    candidates.append(os.path.join(config.REPORTS_DIR, os.path.basename(artifact)))

    roots = [os.path.realpath(config.REPORTS_DIR), os.path.realpath(config.LOOT_DIR)]
    for candidate in candidates:
        real = os.path.realpath(candidate)
        within = any(real == root or real.startswith(root + os.sep) for root in roots)
        if within and os.path.isfile(real):
            return real
    return None


def get_render_artifact(execution_id, index):
    """Resolve the host path for a single artifact of a reporting execution."""
    if not execution_id:
        return None
    execution = get_execution_by_id(execution_id)
    if not execution:
        return None
    result = _parse_result(execution.get("result")) or {}
    artifacts = _render_artifacts(result)
    if index < 0 or index >= len(artifacts):
        return None
    return resolve_artifact_host_path(artifacts[index])
