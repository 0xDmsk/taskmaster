"""REST API handlers — pure functions returning dicts for JSON or template rendering."""

import json
import logging

from state.storage import load_executions, get_execution_by_id
from state.reporting import (
    FINDING_STATUSES,
    SEVERITIES,
    get_finding,
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


def get_stats():
    """Summary counters across all executions."""
    execs = load_executions()
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
    return counts


def get_executions(status=None, target=None, phase=None):
    """Filtered execution list."""
    execs = load_executions()
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


def get_observations():
    """Extract execution observations from completed execution envelopes.

    Worker envelopes still use the historical ``findings`` key. The dashboard
    calls those values observations so "finding" can mean a curated report
    finding everywhere user-facing.
    """
    execs = load_executions()
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
    if severity:
        findings = [finding for finding in findings if finding.get("severity") == severity]
    if query:
        needle = query.lower()
        findings = [
            finding
            for finding in findings
            if needle in (finding.get("title") or "").lower()
            or needle in (finding.get("affected") or "").lower()
            or needle in (finding.get("description") or "").lower()
        ]

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
