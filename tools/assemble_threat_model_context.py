"""Assemble the engagement-scoped inputs an LLM needs to build a threat model.

Gathers the DB-side evidence (scoped assets, recon/enumeration observations,
curated findings, existing model + unresolved questions) into one bundle. The
orchestrating LLM combines this with the engagement's Findings.md / recon-data.md
(which live in its working directory, not the server's) and writes the model
back with create_threat_model + add_threat_model_entry.
"""

import json

from state.storage import load_executions
from state.reporting import (
    get_engagement,
    list_assets,
    list_findings,
    list_threat_models,
    get_threat_model,
)

RECON_PHASES = {"reconnaissance", "enumeration"}


def _parse(raw):
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def handle_assemble_threat_model_context(args):
    engagement_id = args.get("engagement_id")
    if not engagement_id:
        return {"error": "engagement_id is required"}
    engagement = get_engagement(engagement_id)
    if not engagement:
        return {"error": f"Unknown engagement_id: {engagement_id}"}

    observations = []
    for e in load_executions():
        if e.get("engagement_id") != engagement_id:
            continue
        if e.get("security_phase") not in RECON_PHASES:
            continue
        if e.get("status") != "COMPLETED":
            continue
        result = _parse(e.get("result")) or {}
        observations.append(
            {
                "execution_id": e.get("execution_id"),
                "target": e.get("target"),
                "phase": e.get("security_phase"),
                "skill": result.get("skill"),
                "tool": result.get("tool"),
                "observations": result.get("findings"),
                "interpretation": e.get("interpretation"),
            }
        )

    findings = list_findings(engagement_id=engagement_id, include_evidence=False)
    findings_slim = [
        {
            "finding_id": f["finding_id"],
            "title": f["title"],
            "severity": f["severity"],
            "status": f["status"],
            "category": f.get("category"),
            "affected": f.get("affected"),
        }
        for f in findings
    ]

    # Existing models, and any unresolved assumptions/open questions to drive the
    # validation interview on a refinement pass.
    models = list_threat_models(engagement_id=engagement_id)
    unresolved = []
    for m in models:
        full = get_threat_model(m["threat_model_id"]) or {}
        entries = full.get("entries", {})
        for q in entries.get("open_question", []):
            if "REMAINING OPEN QUESTION" in (q.get("status") or "").upper():
                unresolved.append(
                    {
                        "threat_model_id": m["threat_model_id"],
                        "ref": q["ref"],
                        "question": q["question"],
                    }
                )
        for a in entries.get("assumption", []):
            if (a.get("status") or "").upper().startswith("ASSUMED"):
                unresolved.append(
                    {
                        "threat_model_id": m["threat_model_id"],
                        "ref": a["ref"],
                        "assumption": a["context"],
                    }
                )

    return {
        "engagement": engagement,
        "assets": list_assets(engagement_id),
        "recon_observations": observations,
        "observation_count": len(observations),
        "findings": findings_slim,
        "existing_threat_models": models,
        "unresolved_for_validation": unresolved,
        "methodology": "STRIDE",
        "entity_types": [
            "assumption (A-#)",
            "role (UR-#)",
            "asset (CA-#)",
            "terminal_goal (ATG-#)",
            "attack_surface (AS-#)",
            "trust_boundary (TB-#)",
            "attack_path (AP-#)",
            "test_objective (TO-#)",
            "existing_mitigation (EM-#)",
            "recommended_mitigation (RM-#)",
            "open_question (OQ-#)",
            "evidence_note (EV-#)",
        ],
        "guidance": (
            "Build an evidence-grounded threat model in two passes. FIRST PASS: from the "
            "assets, recon/enumeration observations, findings above, and the engagement's "
            "Findings.md / recon-data.md in your working directory, create the model with "
            "create_threat_model, then add entities with add_threat_model_entry. Enumerate "
            "roles, critical assets, attacker terminal goals, attack surface, trust "
            "boundaries, and a small set of high-quality attack paths (STRIDE threat "
            "category, impacted assets, abused surface/boundary, preconditions, existing "
            "controls, gaps, likelihood, impact, priority). Link a confirmed attack path to "
            "its finding (finding_id) and evidence (source_execution_id). For every High or "
            "Critical attack path add at least one test_objective mapped to it. "
            "EVIDENCE RULE: tag every element EVIDENCED (grounded in a Taskmaster execution/"
            "finding or an artifact), USER-CONFIRMED, ASSUMED, or OUT-OF-SCOPE; never present "
            "an assumption as fact. Record assumptions (A-#) and open questions (OQ-#). "
            "VALIDATION PASS: ask the material open questions one at a time (see "
            "unresolved_for_validation), then propagate each answer into the affected attack "
            "paths' likelihood/impact/priority, controls, and mitigations — not just the "
            "summary. Export the deliverable with export_threat_model_markdown."
        ),
    }
