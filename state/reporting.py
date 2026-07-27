"""Canonical reporting data access for Taskmaster.

Executions are an event log. This module stores the reporting state that
survives after a run: engagements, assets, findings, evidence, references,
templates, and report artifacts.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from state.storage import _connect

SEVERITIES = {"Critical", "High", "Medium", "Low", "Info"}
FINDING_STATUSES = {
    "draft",
    "needs_review",
    "confirmed",
    "reported",
    "accepted_risk",
    "false_positive",
}
ENGAGEMENT_STATUSES = {"active", "archived", "complete"}

# Finding categories are a fixed set mirrored from the pwndoc-ng
# `vulnerabilitycategories` collection so Taskmaster findings line up with the
# internal tracking apps. Two Taskmaster-side buckets are appended: "TBD" (the
# default when a category is omitted) and "Other" (the catch-all a non-matching
# value coerces to — the LLM never invents a free-form category). Keep this list
# in sync with pwndoc when categories are added there.
FINDING_CATEGORY_ORDER = [
    "Web",
    "OS-Windows",
    "Multi",
    "Cloud-AWS",
    "API",
    "Containers",
    "Infrastructure",
    "OS-Multi",
    "Cloud-GCP",
    "Software",
    "Thick-Client",
    "ActiveDirectory",
    "OS-Linux",
    "Mobile-Android",
    "CI-CD",
    "Cloud-Azure",
    "Okta",
    "AI-LLM",
    "Other",
    "TBD",
]
FINDING_CATEGORIES = set(FINDING_CATEGORY_ORDER)
DEFAULT_FINDING_CATEGORY = "TBD"
FALLBACK_FINDING_CATEGORY = "Other"


def normalize_category(value: Any) -> str:
    """Coerce a finding category to the fixed set.

    Omitted/empty -> DEFAULT_FINDING_CATEGORY ("TBD"); an unrecognized value ->
    FALLBACK_FINDING_CATEGORY ("Other"); a recognized value passes through. This
    coerces rather than rejects, so a write never fails on category alone — but
    the stored (possibly coerced) value is returned so the caller sees it.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_FINDING_CATEGORY
    return value if value in FINDING_CATEGORIES else FALLBACK_FINDING_CATEGORY


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "engagement"


def _unique_slug(conn, base: str) -> str:
    slug = _slugify(base)
    candidate = slug
    suffix = 2
    while conn.execute("SELECT 1 FROM engagements WHERE slug = ?", (candidate,)).fetchone():
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def _validate_choice(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field} must be one of: {allowed_values}")
    return value


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _normalize_affected(payload: dict) -> str:
    affected = payload.get("affected")
    if affected is None:
        affected = payload.get("affected_assets")
    if isinstance(affected, (list, tuple)):
        return "\n".join(str(item) for item in affected)
    return _clean_text(affected)


def _normalize_cvss(payload: dict) -> tuple[str | None, str | None]:
    cvss = payload.get("cvss") or {}
    if not isinstance(cvss, dict):
        cvss = {}
    score = cvss.get("score") or payload.get("cvss_score")
    vector = cvss.get("vector") or payload.get("cvss_vector")
    return (
        str(score) if score not in (None, "") else None,
        str(vector) if vector not in (None, "") else None,
    )


def create_engagement(
    name: str,
    *,
    engagement_id: str | None = None,
    slug: str | None = None,
    client_name: str | None = None,
    status: str = "active",
    summary: str | None = None,
) -> dict:
    """Create an engagement and return the stored row."""
    if not name:
        raise ValueError("name is required")
    _validate_choice(status, ENGAGEMENT_STATUSES, "status")

    now = _now()
    engagement_id = engagement_id or _new_id("eng")
    with _connect() as conn:
        slug = slug or _unique_slug(conn, name)
        conn.execute(
            """INSERT INTO engagements
               (engagement_id, name, slug, client_name, status, summary,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                engagement_id,
                name,
                slug,
                client_name,
                status,
                summary,
                now,
                now,
            ),
        )
    return get_engagement(engagement_id)


def get_engagement(engagement_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM engagements WHERE engagement_id = ?", (engagement_id,)
        ).fetchone()
        return dict(row) if row else None


def list_engagements(status: str | None = None) -> list[dict]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM engagements WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM engagements ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def create_asset(
    value: str,
    *,
    engagement_id: str | None = None,
    asset_id: str | None = None,
    kind: str = "host",
    description: str | None = None,
) -> dict:
    if not value:
        raise ValueError("value is required")
    now = _now()
    asset_id = asset_id or _new_id("asset")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO report_assets
               (asset_id, engagement_id, kind, value, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (asset_id, engagement_id, kind, value, description, now, now),
        )
    return get_asset(asset_id)


def get_asset(asset_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM report_assets WHERE asset_id = ?", (asset_id,)).fetchone()
        return dict(row) if row else None


def delete_asset(asset_id: str) -> bool:
    """Remove a scope asset. Returns True if a row was deleted."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM report_assets WHERE asset_id = ?", (asset_id,))
        return cur.rowcount > 0


def list_assets(engagement_id: str | None = None) -> list[dict]:
    with _connect() as conn:
        if engagement_id:
            rows = conn.execute(
                """SELECT * FROM report_assets
                   WHERE engagement_id = ?
                   ORDER BY kind, value""",
                (engagement_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM report_assets ORDER BY kind, value").fetchall()
        return [dict(row) for row in rows]


def create_finding(
    *,
    title: str,
    engagement_id: str | None = None,
    finding_id: str | None = None,
    severity: str = "Info",
    category: str | None = None,
    status: str = "draft",
    affected: str | list[str] | None = None,
    affected_assets: list[str] | None = None,
    description: str = "",
    impact: str = "",
    proof_of_concept: str = "",
    remediation: str = "",
    cvss: dict | None = None,
    cvss_score: str | None = None,
    cvss_vector: str | None = None,
    references: list[str | dict] | None = None,
    evidence: list[dict] | None = None,
    source_execution_id: str | None = None,
    created_by: str = "system",
) -> dict:
    """Create a first-class finding with optional evidence and references."""
    if not title:
        raise ValueError("title is required")
    _validate_choice(severity, SEVERITIES, "severity")
    _validate_choice(status, FINDING_STATUSES, "status")
    category = normalize_category(category)

    payload = {
        "affected": affected,
        "affected_assets": affected_assets,
        "cvss": cvss,
        "cvss_score": cvss_score,
        "cvss_vector": cvss_vector,
    }
    affected_text = _normalize_affected(payload)
    score, vector = _normalize_cvss(payload)

    now = _now()
    finding_id = finding_id or _new_id("fnd")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO findings
               (finding_id, engagement_id, title, severity, category, status,
                affected, description, impact, proof_of_concept, remediation,
                cvss_score, cvss_vector, source_execution_id, created_at,
                created_by, updated_at, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                finding_id,
                engagement_id,
                title,
                severity,
                category,
                status,
                affected_text,
                _clean_text(description),
                _clean_text(impact),
                _clean_text(proof_of_concept),
                _clean_text(remediation),
                score,
                vector,
                source_execution_id,
                now,
                created_by,
                now,
                created_by,
            ),
        )

        for idx, ref in enumerate(references or []):
            _insert_reference(conn, finding_id, ref, idx)
        for idx, item in enumerate(evidence or []):
            _insert_evidence(conn, finding_id, item, idx, created_by)

    return get_finding(finding_id)


def get_finding(finding_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM findings WHERE finding_id = ?", (finding_id,)).fetchone()
        if not row:
            return None
        finding = dict(row)
        finding["references"] = _list_references(conn, finding_id)
        finding["evidence"] = _list_evidence(conn, finding_id)
        return finding


def list_findings(
    *,
    engagement_id: str | None = None,
    status: str | None = None,
    include_evidence: bool = True,
) -> list[dict]:
    query = "SELECT * FROM findings"
    clauses = []
    values = []
    if engagement_id:
        clauses.append("engagement_id = ?")
        values.append(engagement_id)
    if status:
        clauses.append("status = ?")
        values.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"

    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
        findings = []
        for row in rows:
            finding = dict(row)
            finding["references"] = _list_references(conn, finding["finding_id"])
            finding["evidence"] = (
                _list_evidence(conn, finding["finding_id"]) if include_evidence else []
            )
            findings.append(finding)
        return findings


def update_finding(finding_id: str, *, updated_by: str = "system", **updates) -> dict | None:
    """Update scalar finding fields.

    References and evidence are intentionally managed by their own helpers so
    an edit cannot silently replace the proof trail.
    """
    allowed = {
        "engagement_id",
        "title",
        "severity",
        "category",
        "status",
        "affected",
        "description",
        "impact",
        "proof_of_concept",
        "remediation",
        "cvss_score",
        "cvss_vector",
        "source_execution_id",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Unsupported finding fields: {', '.join(sorted(unknown))}")

    if "severity" in updates:
        _validate_choice(updates["severity"], SEVERITIES, "severity")
    if "status" in updates:
        _validate_choice(updates["status"], FINDING_STATUSES, "status")
    if "category" in updates:
        updates["category"] = normalize_category(updates["category"])

    if not updates:
        return get_finding(finding_id)

    updates = dict(updates)
    updates["updated_at"] = _now()
    updates["updated_by"] = updated_by

    set_clauses = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [finding_id]
    with _connect() as conn:
        conn.execute(
            f"UPDATE findings SET {set_clauses} WHERE finding_id = ?",
            values,
        )
    return get_finding(finding_id)


def add_finding_reference(
    finding_id: str,
    url: str,
    *,
    label: str | None = None,
    sort_order: int | None = None,
) -> dict:
    with _connect() as conn:
        if sort_order is None:
            sort_order = _next_sort_order(conn, "finding_references", finding_id)
        ref = _insert_reference(
            conn,
            finding_id,
            {"url": url, "label": label},
            sort_order,
        )
        return ref


def add_finding_evidence(
    finding_id: str,
    *,
    kind: str = "note",
    title: str | None = None,
    body: str | None = None,
    artifact_path: str | None = None,
    url: str | None = None,
    source_execution_id: str | None = None,
    created_by: str = "system",
    sort_order: int | None = None,
) -> dict:
    if not any([title, body, artifact_path, url]):
        raise ValueError("evidence requires title, body, artifact_path, or url")
    with _connect() as conn:
        if sort_order is None:
            sort_order = _next_sort_order(conn, "finding_evidence", finding_id)
        return _insert_evidence(
            conn,
            finding_id,
            {
                "kind": kind,
                "title": title,
                "body": body,
                "artifact_path": artifact_path,
                "url": url,
                "source_execution_id": source_execution_id,
            },
            sort_order,
            created_by,
        )


def finding_to_report_dict(finding: dict) -> dict:
    """Return the normalized shape expected by FindingDocxReport."""
    refs = []
    for ref in finding.get("references", []):
        label = ref.get("label")
        url = ref.get("url")
        refs.append(f"{label} - {url}" if label else url)

    return {
        "id": finding["finding_id"],
        "title": finding["title"],
        "severity": finding["severity"],
        "category": finding["category"],
        "cvss": {
            "score": finding.get("cvss_score") or "",
            "vector": finding.get("cvss_vector") or "",
        },
        "affected": finding.get("affected") or "",
        "description": finding.get("description") or "",
        "impact": finding.get("impact") or "",
        "proof_of_concept": finding.get("proof_of_concept") or "",
        "remediation": finding.get("remediation") or "",
        "references": refs,
    }


def _insert_reference(conn, finding_id: str, ref: str | dict, sort_order: int) -> dict:
    if isinstance(ref, str):
        label = None
        url = ref
    elif isinstance(ref, dict):
        label = ref.get("label")
        url = ref.get("url") or ref.get("href")
    else:
        raise ValueError("reference must be a URL string or dict")
    if not url:
        raise ValueError("reference url is required")

    reference_id = _new_id("ref")
    conn.execute(
        """INSERT INTO finding_references
           (reference_id, finding_id, label, url, sort_order, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (reference_id, finding_id, label, url, sort_order, _now()),
    )
    return {
        "reference_id": reference_id,
        "finding_id": finding_id,
        "label": label,
        "url": url,
        "sort_order": sort_order,
    }


def _insert_evidence(
    conn,
    finding_id: str,
    item: dict,
    sort_order: int,
    created_by: str,
) -> dict:
    if not isinstance(item, dict):
        raise ValueError("evidence must be a dict")
    if not any(
        [
            item.get("title"),
            item.get("body"),
            item.get("artifact_path"),
            item.get("url"),
        ]
    ):
        raise ValueError("evidence requires title, body, artifact_path, or url")

    evidence_id = _new_id("evd")
    now = _now()
    conn.execute(
        """INSERT INTO finding_evidence
           (evidence_id, finding_id, source_execution_id, kind, title, body,
            artifact_path, url, sort_order, created_at, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            evidence_id,
            finding_id,
            item.get("source_execution_id"),
            item.get("kind") or "note",
            item.get("title"),
            item.get("body"),
            item.get("artifact_path"),
            item.get("url"),
            sort_order,
            now,
            created_by,
        ),
    )
    return {
        "evidence_id": evidence_id,
        "finding_id": finding_id,
        "source_execution_id": item.get("source_execution_id"),
        "kind": item.get("kind") or "note",
        "title": item.get("title"),
        "body": item.get("body"),
        "artifact_path": item.get("artifact_path"),
        "url": item.get("url"),
        "sort_order": sort_order,
        "created_at": now,
        "created_by": created_by,
    }


def _list_references(conn, finding_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM finding_references
           WHERE finding_id = ?
           ORDER BY sort_order, created_at""",
        (finding_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _list_evidence(conn, finding_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM finding_evidence
           WHERE finding_id = ?
           ORDER BY sort_order, created_at""",
        (finding_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _next_sort_order(conn, table: str, finding_id: str) -> int:
    if table not in {"finding_references", "finding_evidence"}:
        raise ValueError("unsupported table")
    row = conn.execute(
        f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order "
        f"FROM {table} WHERE finding_id = ?",
        (finding_id,),
    ).fetchone()
    return int(row["next_order"])


# --------------------------------------------------------------------------- #
# Threat models (evidence-grounded, multi-entity)                             #
# --------------------------------------------------------------------------- #

THREAT_MODEL_STATUSES = {"draft", "in_review", "final"}

# Entity registry. Each entity type maps to its table, the columns it owns
# (besides the universal ``ref``), which of those are required, the human-facing
# ref prefix (A-#, CA-#, AP-#, ...), and the section title used in exports.
# Cross-references between entities are plain ref strings the caller authors
# (e.g. an attack path's ``impacted_assets`` = "CA-1, CA-4").
TM_ENTITIES = {
    "assumption": {
        "table": "tm_assumptions",
        "prefix": "A",
        "title": "Validated Context and Assumptions",
        "cols": ["status", "context", "impact"],
        "required": ["context"],
    },
    "role": {
        "table": "tm_roles",
        "prefix": "UR",
        "title": "User Roles",
        "cols": ["name", "description"],
        "required": ["name"],
    },
    "asset": {
        "table": "tm_assets",
        "prefix": "CA",
        "title": "Critical Assets",
        "cols": ["name", "description"],
        "required": ["name"],
    },
    "terminal_goal": {
        "table": "tm_terminal_goals",
        "prefix": "ATG",
        "title": "Attacker Terminal Goals",
        "cols": ["name", "description"],
        "required": ["name"],
    },
    "attack_surface": {
        "table": "tm_attack_surface",
        "prefix": "AS",
        "title": "Attack Surface",
        "cols": ["name", "description"],
        "required": ["name"],
    },
    "trust_boundary": {
        "table": "tm_trust_boundaries",
        "prefix": "TB",
        "title": "Trust Boundaries",
        "cols": ["boundary", "protocol", "authn", "authz", "encryption", "validation", "evidence"],
        "required": ["boundary"],
    },
    "attack_path": {
        "table": "tm_attack_paths",
        "prefix": "AP",
        "title": "Attack Paths",
        "cols": [
            "title",
            "description",
            "threat_category",
            "impacted_assets",
            "abused_surface",
            "preconditions",
            "existing_controls",
            "gaps",
            "likelihood",
            "impact",
            "priority",
            "evidence",
            "source_execution_id",
            "finding_id",
        ],
        "required": ["title"],
    },
    "test_objective": {
        "table": "tm_test_objectives",
        "prefix": "TO",
        "title": "Test Objectives",
        "cols": ["attack_path_ref", "status", "objective", "priority", "environment", "notes"],
        "required": ["objective"],
    },
    "existing_mitigation": {
        "table": "tm_existing_mitigations",
        "prefix": "EM",
        "title": "Existing Mitigations",
        "cols": ["mitigation", "control_type", "evidence", "related_paths"],
        "required": ["mitigation"],
    },
    "recommended_mitigation": {
        "table": "tm_recommended_mitigations",
        "prefix": "RM",
        "title": "Recommended Mitigation Focus",
        "cols": ["recommendation", "control_type", "location", "related_paths"],
        "required": ["recommendation"],
    },
    "open_question": {
        "table": "tm_open_questions",
        "prefix": "OQ",
        "title": "Resolved Questions and Remaining Open Questions",
        "cols": ["status", "question", "resolution"],
        "required": ["question"],
    },
    "evidence_note": {
        "table": "tm_evidence_notes",
        "prefix": "EV",
        "title": "Evidence and Out-of-Scope Notes",
        "cols": ["note", "status"],
        "required": ["note"],
    },
}
TM_ENTITY_ORDER = [
    "assumption",
    "role",
    "asset",
    "terminal_goal",
    "attack_surface",
    "trust_boundary",
    "attack_path",
    "test_objective",
    "existing_mitigation",
    "recommended_mitigation",
    "open_question",
    "evidence_note",
]
# Columns that are nullable foreign keys — an empty value must be stored as NULL,
# not "" (which would violate the FK to executions/findings).
TM_NULLABLE_COLS = {"source_execution_id", "finding_id"}


def _tm_col_value(col: str, fields: dict):
    if col in TM_NULLABLE_COLS:
        return fields.get(col) or None
    return _clean_text(fields.get(col, ""))


def _tm_entity(entity_type: str) -> dict:
    spec = TM_ENTITIES.get(entity_type)
    if spec is None:
        allowed = ", ".join(TM_ENTITY_ORDER)
        raise ValueError(f"Unknown entity_type '{entity_type}'. Allowed: {allowed}")
    return spec


def _threat_model_exists(conn, threat_model_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM threat_models WHERE threat_model_id = ?", (threat_model_id,)
        ).fetchone()
        is not None
    )


def create_threat_model(
    *,
    engagement_id: str | None = None,
    title: str,
    threat_model_id: str | None = None,
    methodology: str = "STRIDE",
    status: str = "draft",
    review_date: str | None = None,
    scope: str = "",
    out_of_scope: str = "",
    summary: str = "",
    created_by: str = "system",
) -> dict:
    """Create a threat model shell. Add entries with add_threat_model_entry."""
    if not title:
        raise ValueError("title is required")
    _validate_choice(status, THREAT_MODEL_STATUSES, "status")
    now = _now()
    threat_model_id = threat_model_id or _new_id("tm")
    with _connect() as conn:
        conn.execute(
            """INSERT INTO threat_models
               (threat_model_id, engagement_id, title, methodology, status, review_date,
                scope, out_of_scope, summary, created_at, created_by, updated_at, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                threat_model_id,
                engagement_id,
                title,
                methodology,
                status,
                review_date,
                _clean_text(scope),
                _clean_text(out_of_scope),
                _clean_text(summary),
                now,
                created_by,
                now,
                created_by,
            ),
        )
    return get_threat_model(threat_model_id)


def update_threat_model(
    threat_model_id: str, *, updated_by: str = "system", **updates
) -> dict | None:
    allowed = {
        "engagement_id",
        "title",
        "methodology",
        "status",
        "review_date",
        "scope",
        "out_of_scope",
        "summary",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Unsupported threat model fields: {', '.join(sorted(unknown))}")
    if "status" in updates:
        _validate_choice(updates["status"], THREAT_MODEL_STATUSES, "status")
    if not updates:
        return get_threat_model(threat_model_id)
    updates = dict(updates)
    updates["updated_at"] = _now()
    updates["updated_by"] = updated_by
    set_clauses = ", ".join(f"{f} = ?" for f in updates)
    with _connect() as conn:
        conn.execute(
            f"UPDATE threat_models SET {set_clauses} WHERE threat_model_id = ?",
            list(updates.values()) + [threat_model_id],
        )
    return get_threat_model(threat_model_id)


def get_threat_model(threat_model_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM threat_models WHERE threat_model_id = ?", (threat_model_id,)
        ).fetchone()
        if not row:
            return None
        model = dict(row)
        entries: dict = {}
        counts: dict = {}
        for entity_type in TM_ENTITY_ORDER:
            rows = _list_tm_entries(conn, threat_model_id, entity_type)
            entries[entity_type] = rows
            counts[entity_type] = len(rows)
        model["entries"] = entries
        model["counts"] = counts
        return model


def list_threat_models(engagement_id: str | None = None, status: str | None = None) -> list[dict]:
    query = "SELECT * FROM threat_models"
    clauses, values = [], []
    if engagement_id:
        clauses.append("engagement_id = ?")
        values.append(engagement_id)
    if status:
        clauses.append("status = ?")
        values.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"
    with _connect() as conn:
        rows = conn.execute(query, values).fetchall()
        out = []
        for row in rows:
            model = dict(row)
            model["counts"] = {
                et: _count_tm_entries(conn, model["threat_model_id"], et) for et in TM_ENTITY_ORDER
            }
            out.append(model)
        return out


def add_threat_model_entry(
    threat_model_id: str,
    entity_type: str,
    *,
    ref: str | None = None,
    created_by: str = "system",
    **fields,
) -> dict:
    """Add one entity (assumption, asset, attack path, ...) to a threat model."""
    spec = _tm_entity(entity_type)
    unknown = set(fields) - set(spec["cols"])
    if unknown:
        raise ValueError(
            f"Unsupported {entity_type} fields: {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(spec['cols'])}"
        )
    missing = [f for f in spec["required"] if not (fields.get(f) or "").strip()]
    if missing:
        raise ValueError(f"{entity_type} requires: {', '.join(missing)}")

    now = _now()
    entry_id = _new_id("tme")
    with _connect() as conn:
        if not _threat_model_exists(conn, threat_model_id):
            raise ValueError(f"Unknown threat_model_id: {threat_model_id}")
        sort_order = _next_entry_sort(conn, spec["table"], threat_model_id)
        ref = ref or f"{spec['prefix']}-{sort_order + 1}"
        cols = (
            ["entry_id", "threat_model_id", "ref"]
            + spec["cols"]
            + [
                "sort_order",
                "created_at",
                "created_by",
                "updated_at",
                "updated_by",
            ]
        )
        values = (
            [entry_id, threat_model_id, ref]
            + [_tm_col_value(c, fields) for c in spec["cols"]]
            + [sort_order, now, created_by, now, created_by]
        )
        placeholders = ", ".join("?" for _ in cols)
        conn.execute(
            f"INSERT INTO {spec['table']} ({', '.join(cols)}) VALUES ({placeholders})", values
        )
        return _get_tm_entry(conn, entity_type, entry_id)


def update_threat_model_entry(
    threat_model_id: str,
    entity_type: str,
    ref: str,
    *,
    updated_by: str = "system",
    **fields,
) -> dict | None:
    spec = _tm_entity(entity_type)
    unknown = set(fields) - set(spec["cols"])
    if unknown:
        raise ValueError(
            f"Unsupported {entity_type} fields: {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(spec['cols'])}"
        )
    if not fields:
        with _connect() as conn:
            return _find_tm_entry(conn, entity_type, threat_model_id, ref)
    updates = {c: _tm_col_value(c, fields) for c in fields}
    updates["updated_at"] = _now()
    updates["updated_by"] = updated_by
    set_clauses = ", ".join(f"{c} = ?" for c in updates)
    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {spec['table']} SET {set_clauses} " "WHERE threat_model_id = ? AND ref = ?",
            list(updates.values()) + [threat_model_id, ref],
        )
        if cur.rowcount == 0:
            return None
        return _find_tm_entry(conn, entity_type, threat_model_id, ref)


def delete_threat_model_entry(threat_model_id: str, entity_type: str, ref: str) -> bool:
    spec = _tm_entity(entity_type)
    with _connect() as conn:
        cur = conn.execute(
            f"DELETE FROM {spec['table']} WHERE threat_model_id = ? AND ref = ?",
            (threat_model_id, ref),
        )
        return cur.rowcount > 0


def _list_tm_entries(conn, threat_model_id: str, entity_type: str) -> list[dict]:
    spec = _tm_entity(entity_type)
    rows = conn.execute(
        f"SELECT * FROM {spec['table']} WHERE threat_model_id = ? "
        "ORDER BY sort_order, created_at",
        (threat_model_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _count_tm_entries(conn, threat_model_id: str, entity_type: str) -> int:
    spec = _tm_entity(entity_type)
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM {spec['table']} WHERE threat_model_id = ?",
        (threat_model_id,),
    ).fetchone()
    return int(row["n"])


def _get_tm_entry(conn, entity_type: str, entry_id: str) -> dict | None:
    spec = _tm_entity(entity_type)
    row = conn.execute(f"SELECT * FROM {spec['table']} WHERE entry_id = ?", (entry_id,)).fetchone()
    return dict(row) if row else None


def _find_tm_entry(conn, entity_type: str, threat_model_id: str, ref: str) -> dict | None:
    spec = _tm_entity(entity_type)
    row = conn.execute(
        f"SELECT * FROM {spec['table']} WHERE threat_model_id = ? AND ref = ?",
        (threat_model_id, ref),
    ).fetchone()
    return dict(row) if row else None


def _next_entry_sort(conn, table: str, threat_model_id: str) -> int:
    row = conn.execute(
        f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order "
        f"FROM {table} WHERE threat_model_id = ?",
        (threat_model_id,),
    ).fetchone()
    return int(row["next_order"])


# --------------------------------------------------------------------------- #
# Threat model markdown export (reference deliverable format)                  #
# --------------------------------------------------------------------------- #


def _md_cell(value: Any) -> str:
    """Escape a value for a markdown table cell."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", "<br>").strip()


def _md_table(headers: list[str], rows: list[list]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows)
    return "\n".join([head, sep, body]) if rows else "\n".join([head, sep])


def threat_model_sections(model: dict) -> list[dict]:
    """Shared tabular sections for a get_threat_model() dict.

    Returns a list of {title, headers, rows} used by both the markdown export
    and the dashboard (rendered as auto-escaped HTML tables). Cross-references
    stay as the ref strings the caller authored.
    """
    e = model["entries"]
    return [
        {
            "title": "Validated Context and Assumptions",
            "headers": ["ID", "Status", "Context / Assumption", "Threat Model Impact"],
            "rows": [[a["ref"], a["status"], a["context"], a["impact"]] for a in e["assumption"]],
        },
        {
            "title": "User Roles",
            "headers": ["ID", "User Role", "Description"],
            "rows": [[r["ref"], r["name"], r["description"]] for r in e["role"]],
        },
        {
            "title": "Critical Assets",
            "headers": ["ID", "Critical Asset", "Description"],
            "rows": [[a["ref"], a["name"], a["description"]] for a in e["asset"]],
        },
        {
            "title": "Attacker Terminal Goals",
            "headers": ["ID", "Attacker End Goal", "Description"],
            "rows": [[g["ref"], g["name"], g["description"]] for g in e["terminal_goal"]],
        },
        {
            "title": "Attack Surface",
            "headers": ["ID", "Attack Surface", "Description"],
            "rows": [[s["ref"], s["name"], s["description"]] for s in e["attack_surface"]],
        },
        {
            "title": "Trust Boundaries",
            "headers": [
                "ID",
                "Boundary",
                "Protocol / Mechanism",
                "Authn / Authz",
                "Encryption",
                "Validation / Rate Limiting",
                "Evidence / Assumptions",
            ],
            "rows": [
                [
                    b["ref"],
                    b["boundary"],
                    b["protocol"],
                    " / ".join(x for x in (b["authn"], b["authz"]) if x),
                    b["encryption"],
                    b["validation"],
                    b["evidence"],
                ]
                for b in e["trust_boundary"]
            ],
        },
        {
            "title": "Attack Paths Summary",
            "headers": ["ID", "Attack Path", "Threat Category", "Priority"],
            "rows": [
                [p["ref"], p["title"], p["threat_category"], p["priority"]]
                for p in e["attack_path"]
            ],
        },
        {
            "title": "Test Objectives",
            "headers": [
                "AP-ID",
                "Attack Path / Test Objective Status",
                "Test Objective ID",
                "Test Objective",
                "Test Priority",
                "Environment",
                "Notes",
            ],
            "rows": [
                [
                    t["attack_path_ref"],
                    t["status"],
                    t["ref"],
                    t["objective"],
                    t["priority"],
                    t["environment"],
                    t["notes"],
                ]
                for t in e["test_objective"]
            ],
        },
        {
            "title": "Existing Mitigations",
            "headers": [
                "ID",
                "Mitigation",
                "Control Type",
                "Evidence / Status",
                "Related Attack Paths",
            ],
            "rows": [
                [m["ref"], m["mitigation"], m["control_type"], m["evidence"], m["related_paths"]]
                for m in e["existing_mitigation"]
            ],
        },
        {
            "title": "Recommended Mitigation Focus",
            "headers": [
                "ID",
                "Recommendation",
                "Control Type",
                "Location / Boundary",
                "Related Attack Paths",
            ],
            "rows": [
                [
                    m["ref"],
                    m["recommendation"],
                    m["control_type"],
                    m["location"],
                    m["related_paths"],
                ]
                for m in e["recommended_mitigation"]
            ],
        },
        {
            "title": "Resolved Questions and Remaining Open Questions",
            "headers": ["ID", "Status", "Question / Topic", "Resolution or Remaining Risk"],
            "rows": [
                [q["ref"], q["status"], q["question"], q["resolution"]] for q in e["open_question"]
            ],
        },
        {
            "title": "Evidence and Out-of-Scope Notes",
            "headers": ["ID", "Note", "Status"],
            "rows": [[n["ref"], n["note"], n["status"]] for n in e["evidence_note"]],
        },
    ]


def threat_model_detail_paths(model: dict) -> list[dict]:
    """Detailed attack paths for a get_threat_model() dict: {ref, title, fields}."""
    out = []
    for p in model["entries"]["attack_path"]:
        out.append(
            {
                "ref": p["ref"],
                "title": p["title"],
                "fields": [
                    ("ID", p["ref"]),
                    ("Attack Path", p["title"]),
                    ("Description", p["description"]),
                    ("Threat Category", p["threat_category"]),
                    ("Impacted Assets", p["impacted_assets"]),
                    ("Abused Entry Point or Trust Boundary", p["abused_surface"]),
                    ("Preconditions", p["preconditions"]),
                    ("Existing Controls", p["existing_controls"]),
                    ("Gaps / Open Questions", p["gaps"]),
                    ("Likelihood", p["likelihood"]),
                    ("Impact", p["impact"]),
                    ("Priority", p["priority"]),
                    ("Evidence / Assumptions", p["evidence"]),
                ],
            }
        )
    return out


def render_threat_model_markdown(threat_model_id: str) -> str | None:
    """Render a threat model as the reference-format markdown deliverable."""
    model = get_threat_model(threat_model_id)
    if not model:
        return None
    parts: list[str] = [f"# {model['title']}", ""]
    if model.get("review_date"):
        parts += [f"Review date: {model['review_date']}", ""]
    if model.get("scope"):
        parts += [f"Scope: {model['scope']}", ""]
    if model.get("out_of_scope"):
        parts += [f"Out of scope: {model['out_of_scope']}", ""]
    if model.get("summary"):
        parts += [model["summary"], ""]

    for sec in threat_model_sections(model):
        parts.append(f"## {sec['title']}")
        parts.append("")
        parts.append(_md_table(sec["headers"], sec["rows"]) if sec["rows"] else "_None recorded._")
        parts.append("")

    detail_paths = threat_model_detail_paths(model)
    if detail_paths:
        parts.append("## Detailed Attack Paths")
        parts.append("")
        for path in detail_paths:
            parts.append(f"### {path['ref']}: {path['title']}")
            parts.append("")
            parts.append(_md_table(["Field", "Detail"], [[k, v] for k, v in path["fields"]]))
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"
