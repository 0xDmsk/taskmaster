"""suggest_next_action — the copilot's planning brain as a tool.

Given the current state (optionally scoped to an engagement), inspect executions,
report findings, and threat models and return a prioritized list of concrete,
actionable gaps: work that failed, executions that need an interpretation,
observations not yet triaged into findings, findings that aren't report-ready,
phase-coverage gaps, and threat-model status. This saves the orchestrating LLM
from reconstructing engagement state by hand every session.

Read-only: it never mutates state — it only recommends the next move.
"""

import json

from state.storage import load_executions
from state.reporting import (
    finding_to_report_dict,
    get_engagement,
    list_assets,
    list_findings,
    list_threat_models,
)
from tools.request_reporting_docx import _REQUIRED_REPORT_FIELDS

PHASES = ["reconnaissance", "enumeration", "exploitation", "post_exploitation", "reporting"]
# Non-scan phases we don't auto-suggest as "the next scan"; reporting is driven
# by the findings workflow, not by queuing more recon-style executions.
_SCAN_PHASES = ["reconnaissance", "enumeration", "exploitation", "post_exploitation"]
CLOSED_STATUSES = {"reported", "accepted_risk", "false_positive"}
TRIAGE_STATUSES = {"draft", "needs_review"}

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}


def _parse_result(raw):
    """Parse an execution result envelope that may be a JSON string or dict."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _has_observations(result):
    """True when a completed envelope carries observations or artifacts worth triaging."""
    findings = result.get("findings")
    artifacts = result.get("artifacts")
    has_findings = bool(findings) and not (isinstance(findings, dict) and not findings)
    return has_findings or bool(artifacts)


def _suggest(suggestions, priority, category, message, **extra):
    entry = {"priority": priority, "category": category, "message": message}
    entry.update(extra)
    suggestions.append(entry)


def handle_suggest_next_action(args):
    engagement_id = args.get("engagement_id")
    if engagement_id and not get_engagement(engagement_id):
        return {
            "error": "Unknown engagement_id",
            "details": f"No engagement '{engagement_id}' exists.",
        }

    execs = load_executions()
    if engagement_id:
        execs = [e for e in execs if e.get("engagement_id") == engagement_id]

    findings = list_findings(engagement_id=engagement_id or None, include_evidence=False)

    counts = {
        "executions": len(execs),
        "queued": sum(1 for e in execs if e.get("status") == "QUEUED"),
        "running": sum(1 for e in execs if e.get("status") == "RUNNING"),
        "completed": sum(1 for e in execs if e.get("status") == "COMPLETED"),
        "failed": sum(1 for e in execs if e.get("status") == "FAILED"),
        "cancelled": sum(1 for e in execs if e.get("status") == "CANCELLED"),
        "findings": len(findings),
        "open_findings": sum(1 for f in findings if f.get("status") not in CLOSED_STATUSES),
    }

    suggestions = []

    # --- Failed work ------------------------------------------------------
    failed = [e for e in execs if e.get("status") == "FAILED"]
    if failed:
        _suggest(
            suggestions,
            "high",
            "failed_executions",
            f"{len(failed)} execution(s) FAILED — review the errors and decide whether to "
            "retry (re-queue) or accept and move on.",
            execution_ids=[e["execution_id"] for e in failed[:20]],
        )

    # --- Completed but not finalized with an interpretation ---------------
    missing_interp = [
        e
        for e in execs
        if e.get("status") == "COMPLETED" and not (e.get("interpretation") or "").strip()
    ]
    if missing_interp:
        _suggest(
            suggestions,
            "high",
            "missing_interpretation",
            f"{len(missing_interp)} completed execution(s) have no interpretation — call "
            "mark_execution_complete with an 'interpretation' so the analysis (not just raw "
            "stdout) is captured.",
            execution_ids=[e["execution_id"] for e in missing_interp[:20]],
        )

    # --- Ready work waiting for a worker ---------------------------------
    by_id = {e["execution_id"]: e for e in execs}

    def _deps_done(e):
        return all(
            by_id.get(dep, {}).get("status") == "COMPLETED" for dep in (e.get("depends_on") or [])
        )

    ready = [e for e in execs if e.get("status") == "QUEUED" and _deps_done(e)]
    blocked = [e for e in execs if e.get("status") == "QUEUED" and not _deps_done(e)]
    if ready:
        _suggest(
            suggestions,
            "high" if counts["running"] == 0 else "medium",
            "ready_queue",
            f"{len(ready)} queued execution(s) are ready to run — spawn a compatible agent "
            "(or verify a live worker), then monitor with wait_for_completion.",
            execution_ids=[e["execution_id"] for e in ready[:20]],
        )
    if blocked:
        _suggest(
            suggestions,
            "info",
            "blocked_queue",
            f"{len(blocked)} queued execution(s) are waiting on unfinished prerequisites; "
            "they'll unblock automatically as their dependencies complete.",
        )

    cancelled = [e for e in execs if e.get("status") == "CANCELLED"]
    if cancelled:
        _suggest(
            suggestions,
            "info",
            "cancelled_chain",
            f"{len(cancelled)} execution(s) were cancelled because a prerequisite failed — "
            "re-queue the chain if that work is still needed.",
        )

    # --- Observations not yet promoted to report findings -----------------
    linked_execution_ids = {
        f.get("source_execution_id") for f in findings if f.get("source_execution_id")
    }
    unpromoted = [
        e
        for e in execs
        if e.get("status") == "COMPLETED"
        and e["execution_id"] not in linked_execution_ids
        and _has_observations(_parse_result(e.get("result")))
    ]
    if unpromoted:
        _suggest(
            suggestions,
            "medium",
            "unpromoted_observations",
            f"{len(unpromoted)} completed execution(s) produced observations that aren't linked "
            "to any report finding — triage the notable ones into findings with "
            "create_reporting_finding (set source_execution_id).",
            execution_ids=[e["execution_id"] for e in unpromoted[:20]],
        )

    # --- Report findings not yet report-ready -----------------------------
    not_ready = []
    for finding in findings:
        report = finding_to_report_dict(finding)
        missing = [field for field in _REQUIRED_REPORT_FIELDS if not report.get(field)]
        if missing:
            not_ready.append({"finding_id": finding.get("finding_id"), "missing": missing})
    if not_ready:
        _suggest(
            suggestions,
            "medium",
            "findings_not_report_ready",
            f"{len(not_ready)} finding(s) are missing required fields and would return "
            "not_ready from request_reporting_docx — fill them via update_reporting_finding.",
            findings=not_ready[:20],
        )

    # --- Findings still in triage ----------------------------------------
    in_triage = [f for f in findings if f.get("status") in TRIAGE_STATUSES]
    if in_triage:
        _suggest(
            suggestions,
            "low",
            "findings_in_triage",
            f"{len(in_triage)} finding(s) are still in draft/needs_review — progress their "
            "status once validated.",
            finding_ids=[f.get("finding_id") for f in in_triage[:20]],
        )

    # --- Observations captured but no findings at all ---------------------
    completed_with_obs = any(
        e.get("status") == "COMPLETED" and _has_observations(_parse_result(e.get("result")))
        for e in execs
    )
    if completed_with_obs and not findings:
        _suggest(
            suggestions,
            "medium",
            "no_findings_yet",
            "Completed executions have captured observations, but no report findings exist yet — "
            "start curating findings for the deliverable.",
        )

    # --- Phase-coverage gaps ---------------------------------------------
    completed_phases_by_target = {}
    attempted_phases_by_target = {}
    for e in execs:
        target = e.get("target")
        phase = e.get("security_phase")
        if not target or phase not in PHASES:
            continue
        attempted_phases_by_target.setdefault(target, set()).add(phase)
        if e.get("status") == "COMPLETED":
            completed_phases_by_target.setdefault(target, set()).add(phase)

    phase_gaps = []
    for target, done in completed_phases_by_target.items():
        attempted = attempted_phases_by_target.get(target, set())
        # Highest scan phase completed for this target.
        highest = max((i for i, p in enumerate(_SCAN_PHASES) if p in done), default=-1)
        if highest < 0:
            continue
        next_index = highest + 1
        if next_index < len(_SCAN_PHASES):
            next_phase = _SCAN_PHASES[next_index]
            if next_phase not in attempted:
                phase_gaps.append({"target": target, "next_phase": next_phase})
    if phase_gaps:
        preview = ", ".join(f"{g['target']} → {g['next_phase']}" for g in phase_gaps[:6])
        _suggest(
            suggestions,
            "medium",
            "phase_gap",
            f"{len(phase_gaps)} target(s) completed a phase with no work queued in the next "
            f"phase: {preview}.",
            gaps=phase_gaps[:20],
        )

    # --- Threat model status (engagement-scoped only) ---------------------
    if engagement_id:
        models = list_threat_models(engagement_id=engagement_id)
        assets = list_assets(engagement_id)
        if not models and (findings or assets):
            _suggest(
                suggestions,
                "low",
                "no_threat_model",
                "No threat model exists for this engagement yet — assemble_threat_model_context "
                "then create_threat_model to synthesize one from the evidence.",
            )
        for model in models:
            if model.get("status") != "final":
                open_qs = (model.get("counts") or {}).get("open_question", 0)
                tail = f" ({open_qs} open question(s) to resolve)" if open_qs else ""
                _suggest(
                    suggestions,
                    "low",
                    "threat_model_unfinished",
                    f"Threat model '{model.get('title', model.get('threat_model_id'))}' is "
                    f"'{model.get('status')}'{tail} — run the validation pass and promote it to "
                    "final.",
                    threat_model_id=model.get("threat_model_id"),
                )

    suggestions.sort(key=lambda s: _PRIORITY_RANK.get(s["priority"], 9))

    headline = suggestions[0]["message"] if suggestions else (
        "No outstanding actions detected for this scope — the queue is clear, completed work is "
        "interpreted, and findings look report-ready."
    )

    return {
        "engagement_id": engagement_id,
        "headline": headline,
        "summary": counts,
        "suggestions": suggestions,
    }
