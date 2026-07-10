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
    category: str = "General",
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
