"""Surface inventory: the functionalities and endpoints mapped for an engagement.

Items are functionalities (``FN-n``) and endpoints (``EP-n``, optionally under a
functionality). Links tie an item to the executions that ``discovered`` or
``tested`` it and to the report findings that it ``affects``. Coverage status
is derived from the links on read, never stored, so it can't drift.

Population rides on calls the orchestrator already makes:
- result envelopes carrying ``findings.endpoints`` are ingested on completion
  (``ingest_execution_endpoints``) as ``discovered`` links;
- ``surface_refs`` on ``request_security_action`` creates ``tested`` links;
- ``surface_refs`` on report findings creates ``affects`` links;
- ``upsert_surface_items`` covers knowledge that isn't an execution (scoping
  docs, OpenAPI specs).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlsplit

from state.reporting import _clean_text, _new_id, _now
from state.storage import _connect, get_execution_by_id

logger = logging.getLogger(__name__)

KINDS = {"functionality", "endpoint"}
RELS = {"discovered", "tested", "affects"}
SOURCES = {"skill", "sandbox", "llm", "import"}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}
STATUS_ORDER = ["vulnerable", "tested", "in_progress", "discovered"]

_REF_PREFIX = {"functionality": "FN", "endpoint": "EP"}
_REF_RE = re.compile(r"^(FN|EP)-\d+$", re.IGNORECASE)
_DEFAULT_PORTS = {"http": 80, "https": 443}
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
_HEX_RE = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
# Cap on endpoints ingested from one envelope: a runaway crawler shouldn't be
# able to flood the inventory.
MAX_INGEST = 2000


def _template_segment(segment: str) -> str:
    if segment.isdigit() or _UUID_RE.match(segment) or _HEX_RE.match(segment):
        return "{id}"
    return segment


def _host_from_target(target: str | None) -> str:
    """A usable default host from an execution target, or "" if it isn't one."""
    target = (target or "").strip()
    if not target or " " in target:
        return ""
    if "://" in target:
        return _split_host(urlsplit(target))
    if "." in target or ":" in target:
        return _split_host(urlsplit("//" + target))
    return ""


def _split_host(parts) -> str:
    host = (parts.hostname or "").lower()
    if not host:
        return ""
    scheme = (parts.scheme or "").lower()
    try:
        port = parts.port
    except ValueError:
        port = None
    # Keep the port unless it's the scheme's default (80/443 for a bare host).
    defaults = {_DEFAULT_PORTS[scheme]} if scheme in _DEFAULT_PORTS else {80, 443}
    if port and port not in defaults:
        host = f"{host}:{port}"
    # Web schemes collapse together; app schemes (deeplinks) stay distinct.
    if scheme and scheme not in _DEFAULT_PORTS:
        host = f"{scheme}://{host}"
    return host


def normalize_endpoint(
    method: str | None, url_or_path: str, default_host: str = ""
) -> dict[str, str]:
    """Normalize an endpoint into ``{method, host, path, key, sample_url}``.

    ``url_or_path`` may be a full URL, a bare ``host/path`` or a path. A leading
    HTTP method in the string (``"POST /api/x"``) wins over ``method``. Query
    strings and fragments are dropped and id-like path segments become ``{id}``,
    so ``/users/42`` and ``/users/97`` are the same endpoint.
    """
    raw = (url_or_path or "").strip()
    head, _, rest = raw.partition(" ")
    if head.upper() in HTTP_METHODS | {"ANY"} and rest.strip():
        method, raw = head, rest.strip()
    method = (method or "ANY").strip().upper() or "ANY"
    if not raw:
        raise ValueError("endpoint requires a url or path")

    if "://" in raw:
        parts = urlsplit(raw)
        host = _split_host(parts)
    elif raw.startswith("/"):
        parts = urlsplit(raw)
        host = (default_host or "").lower()
    else:
        parts = urlsplit("//" + raw)
        host = _split_host(parts)

    segments = [_template_segment(s) for s in parts.path.split("/") if s]
    path = "/" + "/".join(segments)
    return {
        "method": method,
        "host": host,
        "path": path,
        "key": f"{method} {host}{path}",
        "sample_url": raw,
    }


def _functionality_key(name: str) -> str:
    return "FN " + " ".join(name.lower().split())


def _next_ref(conn, engagement_id: str, kind: str) -> str:
    prefix = _REF_PREFIX[kind]
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(ref, 4) AS INTEGER)) FROM surface_items "
        "WHERE engagement_id = ? AND kind = ?",
        (engagement_id, kind),
    ).fetchone()
    return f"{prefix}-{(row[0] or 0) + 1}"


def _engagement_exists(conn, engagement_id: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM engagements WHERE engagement_id = ?", (engagement_id,)
        ).fetchone()
    )


def _item_by_ref(conn, engagement_id: str, ref: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM surface_items WHERE engagement_id = ? AND UPPER(ref) = UPPER(?)",
        (engagement_id, ref),
    ).fetchone()
    return dict(row) if row else None


def _upsert(conn, engagement_id: str, fields: dict, source: str, created_by: str) -> dict:
    """Insert an item, or fill blanks on the existing one with the same key."""
    row = conn.execute(
        "SELECT * FROM surface_items WHERE engagement_id = ? AND key = ?",
        (engagement_id, fields["key"]),
    ).fetchone()
    now = _now()
    if row:
        existing = dict(row)
        # Never overwrite curated data with later discovery: only fill empties.
        fill = {
            k: v
            for k, v in fields.items()
            if k in ("name", "description", "attack_surface_ref", "parent_id", "sample_url")
            and v
            and not existing.get(k)
        }
        if fill:
            sets = ", ".join(f"{k} = ?" for k in fill)
            conn.execute(
                f"UPDATE surface_items SET {sets}, updated_at = ? WHERE item_id = ?",
                [*fill.values(), now, existing["item_id"]],
            )
            existing.update(fill)
        return existing

    item = {
        "item_id": _new_id("srf"),
        "engagement_id": engagement_id,
        "ref": _next_ref(conn, engagement_id, fields["kind"]),
        "kind": fields["kind"],
        "name": fields.get("name") or "",
        "method": fields.get("method") or "ANY",
        "host": fields.get("host") or "",
        "path": fields.get("path") or "",
        "key": fields["key"],
        "sample_url": fields.get("sample_url"),
        "parent_id": fields.get("parent_id"),
        "attack_surface_ref": fields.get("attack_surface_ref") or "",
        "description": fields.get("description") or "",
        "source": source,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
    }
    cols = ", ".join(item)
    conn.execute(
        f"INSERT INTO surface_items ({cols}) VALUES ({', '.join('?' for _ in item)})",
        list(item.values()),
    )
    return item


def _resolve_parent(conn, engagement_id: str, parent: Any, source: str, created_by: str):
    """A parent given as ``FN-n`` must exist; a name creates the functionality."""
    if not parent:
        return None
    parent = str(parent).strip()
    if _REF_RE.match(parent):
        item = _item_by_ref(conn, engagement_id, parent)
        if not item or item["kind"] != "functionality":
            raise ValueError(f"Unknown functionality ref: {parent}")
        return item["item_id"]
    fields = {"kind": "functionality", "name": parent, "key": _functionality_key(parent)}
    return _upsert(conn, engagement_id, fields, source, created_by)["item_id"]


def _item_fields(conn, engagement_id, item, default_host, source, created_by) -> dict:
    """Turn one input (a string or dict) into normalized column values."""
    if isinstance(item, str):
        item = {"url": item}
    if not isinstance(item, dict):
        raise ValueError("surface item must be a string or an object")
    kind = item.get("kind") or "endpoint"
    if kind not in KINDS:
        raise ValueError(f"kind must be one of: {', '.join(sorted(KINDS))}")

    fields: dict[str, Any] = {
        "kind": kind,
        "name": _clean_text(item.get("name")).strip(),
        "description": _clean_text(item.get("description")).strip(),
        "attack_surface_ref": _clean_text(item.get("attack_surface_ref")).strip(),
    }
    if kind == "functionality":
        if not fields["name"]:
            raise ValueError("functionality requires a name")
        fields["key"] = _functionality_key(fields["name"])
        return fields

    location = item.get("url") or item.get("path")
    if not location and item.get("host"):
        location = item["host"]
    fields.update(
        normalize_endpoint(
            item.get("method"), _clean_text(location), item.get("host") or default_host
        )
    )
    fields["parent_id"] = _resolve_parent(
        conn, engagement_id, item.get("parent"), source, created_by
    )
    return fields


def _link(conn, item_id, rel, execution_id=None, finding_id=None):
    if rel not in RELS:
        raise ValueError(f"rel must be one of: {', '.join(sorted(RELS))}")
    conn.execute(
        "INSERT OR IGNORE INTO surface_links "
        "(link_id, item_id, rel, execution_id, finding_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (_new_id("srl"), item_id, rel, execution_id, finding_id, _now()),
    )


def upsert_surface_items(
    engagement_id: str,
    items: list,
    *,
    source: str = "llm",
    execution_id: str | None = None,
    rel: str | None = None,
    default_host: str = "",
    created_by: str = "system",
) -> list[dict]:
    """Add (or merge) items; optionally link each one to ``execution_id`` as ``rel``."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of: {', '.join(sorted(SOURCES))}")
    out = []
    with _connect() as conn:
        if not _engagement_exists(conn, engagement_id):
            raise ValueError(f"Unknown engagement_id: {engagement_id}")
        for item in items:
            fields = _item_fields(conn, engagement_id, item, default_host, source, created_by)
            stored = _upsert(conn, engagement_id, fields, source, created_by)
            if rel and execution_id:
                _link(conn, stored["item_id"], rel, execution_id=execution_id)
            out.append(stored)
    return out


def resolve_surface_refs(
    engagement_id: str,
    refs: list[str],
    *,
    default_host: str = "",
    created_by: str = "system",
) -> list[dict]:
    """Resolve ``surface_refs`` to items.

    ``EP-n`` / ``FN-n`` must already exist (a typo is an error, not a new item).
    Anything else is read as an endpoint (``"GET /api/x"``) and created if new.
    """
    out = []
    with _connect() as conn:
        if not _engagement_exists(conn, engagement_id):
            raise ValueError(f"Unknown engagement_id: {engagement_id}")
        for ref in refs:
            ref = str(ref).strip()
            if _REF_RE.match(ref):
                item = _item_by_ref(conn, engagement_id, ref)
                if not item:
                    raise ValueError(f"Unknown surface ref: {ref}")
            else:
                fields = _item_fields(conn, engagement_id, ref, default_host, "llm", created_by)
                item = _upsert(conn, engagement_id, fields, "llm", created_by)
            out.append(item)
    return out


def link_surface(item_ids: list[str], rel: str, *, execution_id=None, finding_id=None) -> None:
    with _connect() as conn:
        for item_id in item_ids:
            _link(conn, item_id, rel, execution_id=execution_id, finding_id=finding_id)


def link_finding_surface(finding_id: str, engagement_id: str, refs: list[str]) -> list[str]:
    """Resolve ``refs`` and link them to a report finding as ``affects``; returns refs."""
    items = resolve_surface_refs(engagement_id, refs)
    link_surface([i["item_id"] for i in items], "affects", finding_id=finding_id)
    return [i["ref"] for i in items]


def _parse_envelope(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw) if raw else None
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def envelope_endpoints(envelope) -> list:
    """``findings.endpoints`` from an envelope (top-level ``endpoints`` also accepted)."""
    envelope = _parse_envelope(envelope)
    findings = envelope.get("findings")
    endpoints = findings.get("endpoints") if isinstance(findings, dict) else None
    if endpoints is None:
        endpoints = envelope.get("endpoints")
    return endpoints if isinstance(endpoints, list) else []


def ingest_execution_endpoints(execution_id: str) -> int:
    """Record the endpoints an execution's envelope reports as ``discovered``.

    A no-op for executions not tagged to an engagement. Malformed entries are
    skipped rather than failing the whole batch. Returns the number ingested.
    """
    execution = get_execution_by_id(execution_id)
    if not execution or not execution.get("engagement_id"):
        return 0
    endpoints = envelope_endpoints(execution.get("result"))[:MAX_INGEST]
    if not endpoints:
        return 0
    envelope = _parse_envelope(execution.get("result"))
    source = "sandbox" if envelope.get("skill") in ("python_sandbox", None) else "skill"
    default_host = _host_from_target(execution.get("target"))
    count = 0
    with _connect() as conn:
        for entry in endpoints:
            try:
                fields = _item_fields(
                    conn, execution["engagement_id"], entry, default_host, source, "ingest"
                )
            except ValueError:
                continue
            stored = _upsert(conn, execution["engagement_id"], fields, source, "ingest")
            _link(conn, stored["item_id"], "discovered", execution_id=execution_id)
            count += 1
    return count


def ingest_after_completion(execution_id: str) -> int:
    """Completion-hook wrapper: ingestion problems are logged, never raised.

    A malformed envelope must not turn a successful execution into a failed
    completion call, so this is what the completion tools call.
    """
    try:
        return ingest_execution_endpoints(execution_id)
    except Exception:
        logger.exception("surface ingestion failed for execution %s", execution_id)
        return 0


def _derive_status(links: list[dict]) -> str:
    if any(l["rel"] == "affects" and l.get("finding_status") != "false_positive" for l in links):
        return "vulnerable"
    tested = [l for l in links if l["rel"] == "tested"]
    if any(l.get("execution_status") == "COMPLETED" for l in tested):
        return "tested"
    if any(l.get("execution_status") in ("QUEUED", "CLAIMED", "RUNNING") for l in tested):
        return "in_progress"
    return "discovered"


def list_surface(engagement_id: str) -> list[dict]:
    """Every item for an engagement with its links and derived coverage status.

    Each item gains ``links`` (with execution phase/status and finding
    severity/status joined in), ``status``, ``phase_counts`` (distinct linked
    executions per phase) and, for functionalities, ``endpoint_count``.
    """
    with _connect() as conn:
        items = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM surface_items WHERE engagement_id = ? "
                "ORDER BY kind DESC, CAST(SUBSTR(ref, 4) AS INTEGER)",
                (engagement_id,),
            ).fetchall()
        ]
        rows = conn.execute(
            "SELECT l.*, e.security_phase AS phase, e.status AS execution_status, "
            "f.title AS finding_title, f.severity AS finding_severity, "
            "f.status AS finding_status "
            "FROM surface_links l "
            "JOIN surface_items i ON i.item_id = l.item_id "
            "LEFT JOIN executions e ON e.execution_id = l.execution_id "
            "LEFT JOIN findings f ON f.finding_id = l.finding_id "
            "WHERE i.engagement_id = ? ORDER BY l.created_at",
            (engagement_id,),
        ).fetchall()
    links: dict[str, list[dict]] = {}
    for row in rows:
        links.setdefault(row["item_id"], []).append(dict(row))

    children: dict[str, int] = {}
    for item in items:
        if item["parent_id"]:
            children[item["parent_id"]] = children.get(item["parent_id"], 0) + 1
    for item in items:
        item_links = links.get(item["item_id"], [])
        item["links"] = item_links
        item["status"] = _derive_status(item_links)
        phases: dict[str, set] = {}
        for link in item_links:
            if link.get("execution_id") and link.get("phase"):
                phases.setdefault(link["phase"], set()).add(link["execution_id"])
        item["phase_counts"] = {p: len(ids) for p, ids in phases.items()}
        item["endpoint_count"] = children.get(item["item_id"], 0)
    return items


def get_surface_item(engagement_id: str, item_id: str) -> dict | None:
    return next((i for i in list_surface(engagement_id) if i["item_id"] == item_id), None)
