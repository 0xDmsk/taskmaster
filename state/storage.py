import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import config

_DB_PATH = os.environ.get("STATE_DB", os.path.join(config.STATE_DIR, "executions.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    target TEXT NOT NULL,
    security_phase TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT,
    updated_by TEXT,
    executor_id TEXT,
    request TEXT NOT NULL DEFAULT '{}',
    result TEXT,
    interpretation TEXT,
    engagement_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_target_status ON executions (target, status);
CREATE INDEX IF NOT EXISTS idx_status ON executions (status);

CREATE TABLE IF NOT EXISTS engagements (
    engagement_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT,
    client_name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_engagements_slug
    ON engagements (slug)
    WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_engagements_status ON engagements (status);

CREATE TABLE IF NOT EXISTS report_assets (
    asset_id TEXT PRIMARY KEY,
    engagement_id TEXT,
    kind TEXT NOT NULL DEFAULT 'host',
    value TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (engagement_id) REFERENCES engagements (engagement_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_report_assets_engagement
    ON report_assets (engagement_id);
CREATE INDEX IF NOT EXISTS idx_report_assets_value ON report_assets (value);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    engagement_id TEXT,
    title TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'Info',
    category TEXT NOT NULL DEFAULT 'TBD',
    status TEXT NOT NULL DEFAULT 'draft',
    affected TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    impact TEXT NOT NULL DEFAULT '',
    proof_of_concept TEXT NOT NULL DEFAULT '',
    remediation TEXT NOT NULL DEFAULT '',
    cvss_score TEXT,
    cvss_vector TEXT,
    source_execution_id TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (engagement_id) REFERENCES engagements (engagement_id)
        ON DELETE SET NULL,
    FOREIGN KEY (source_execution_id) REFERENCES executions (execution_id)
        ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_engagement ON findings (engagement_id);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings (status);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings (severity);
CREATE INDEX IF NOT EXISTS idx_findings_source_execution
    ON findings (source_execution_id);

CREATE TABLE IF NOT EXISTS finding_evidence (
    evidence_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL,
    source_execution_id TEXT,
    kind TEXT NOT NULL DEFAULT 'note',
    title TEXT,
    body TEXT,
    artifact_path TEXT,
    url TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    FOREIGN KEY (finding_id) REFERENCES findings (finding_id)
        ON DELETE CASCADE,
    FOREIGN KEY (source_execution_id) REFERENCES executions (execution_id)
        ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_finding_evidence_finding
    ON finding_evidence (finding_id, sort_order);

CREATE TABLE IF NOT EXISTS finding_references (
    reference_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL,
    label TEXT,
    url TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (finding_id) REFERENCES findings (finding_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_finding_references_finding
    ON finding_references (finding_id, sort_order);

CREATE TABLE IF NOT EXISTS report_templates (
    template_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    engine TEXT NOT NULL DEFAULT 'docxtpl',
    path TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    engagement_id TEXT,
    template_id TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    output_path TEXT,
    generated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (engagement_id) REFERENCES engagements (engagement_id)
        ON DELETE SET NULL,
    FOREIGN KEY (template_id) REFERENCES report_templates (template_id)
        ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_engagement ON reports (engagement_id);

CREATE TABLE IF NOT EXISTS threat_models (
    threat_model_id TEXT PRIMARY KEY,
    engagement_id TEXT,
    title TEXT NOT NULL,
    methodology TEXT NOT NULL DEFAULT 'STRIDE',
    status TEXT NOT NULL DEFAULT 'draft',
    review_date TEXT,
    scope TEXT NOT NULL DEFAULT '',
    out_of_scope TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (engagement_id) REFERENCES engagements (engagement_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_threat_models_engagement
    ON threat_models (engagement_id);

-- Threat model entries: one table per entity type in the evidence-grounded
-- model. Cross-references between entities (e.g. an attack path's impacted
-- assets) are stored as human-readable ref strings ("CA-1, CA-4") the LLM
-- authors, matching the reference document format. Every table shares
-- (entry_id, threat_model_id, ref, sort_order, audit columns).

CREATE TABLE IF NOT EXISTS tm_assumptions (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ASSUMED',
    context TEXT NOT NULL DEFAULT '',
    impact TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_roles (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_assets (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_terminal_goals (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_attack_surface (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_trust_boundaries (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    boundary TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    authn TEXT NOT NULL DEFAULT '',
    authz TEXT NOT NULL DEFAULT '',
    encryption TEXT NOT NULL DEFAULT '',
    validation TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_attack_paths (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    threat_category TEXT NOT NULL DEFAULT '',
    impacted_assets TEXT NOT NULL DEFAULT '',
    abused_surface TEXT NOT NULL DEFAULT '',
    preconditions TEXT NOT NULL DEFAULT '',
    existing_controls TEXT NOT NULL DEFAULT '',
    gaps TEXT NOT NULL DEFAULT '',
    likelihood TEXT NOT NULL DEFAULT 'Medium',
    impact TEXT NOT NULL DEFAULT 'Medium',
    priority TEXT NOT NULL DEFAULT 'Medium',
    evidence TEXT NOT NULL DEFAULT '',
    source_execution_id TEXT,
    finding_id TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE,
    FOREIGN KEY (source_execution_id) REFERENCES executions (execution_id) ON DELETE SET NULL,
    FOREIGN KEY (finding_id) REFERENCES findings (finding_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tm_test_objectives (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    attack_path_ref TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Not Started',
    objective TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'Medium',
    environment TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_existing_mitigations (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    mitigation TEXT NOT NULL DEFAULT '',
    control_type TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    related_paths TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_recommended_mitigations (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    recommendation TEXT NOT NULL DEFAULT '',
    control_type TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    related_paths TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_open_questions (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'REMAINING OPEN QUESTION',
    question TEXT NOT NULL DEFAULT '',
    resolution TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tm_evidence_notes (
    entry_id TEXT PRIMARY KEY,
    threat_model_id TEXT NOT NULL,
    ref TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system',
    updated_at TEXT NOT NULL,
    updated_by TEXT,
    FOREIGN KEY (threat_model_id) REFERENCES threat_models (threat_model_id) ON DELETE CASCADE
);
"""

# Online-migration columns, keyed by table. Adding a column to an existing table
# here (rather than only in _SCHEMA) is required because CREATE TABLE IF NOT
# EXISTS is a no-op on a table that already exists in a legacy database.
_REQUIRED_COLUMNS = {
    "executions": {
        "interpretation": "TEXT",
        "engagement_id": "TEXT",
    },
    "threat_models": {
        "review_date": "TEXT",
        "scope": "TEXT NOT NULL DEFAULT ''",
        "out_of_scope": "TEXT NOT NULL DEFAULT ''",
    },
}


def _db_path():
    """Return current DB path (re-reads env for test overrides)."""
    return os.environ.get("STATE_DB", _DB_PATH)


def _ensure_db():
    """Create the database directory, schema, and auto-migrate from JSON if needed."""
    db = _db_path()
    os.makedirs(os.path.dirname(db), exist_ok=True)

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    _add_missing_columns(conn)
    conn.commit()
    conn.close()

    # Auto-migrate from legacy JSON file
    json_file = os.path.join(os.path.dirname(db), "executions.json")
    if os.path.exists(json_file):
        _migrate_from_json(json_file, db)


def _add_missing_columns(conn):
    """Online migration: add new columns to legacy DBs without dropping data."""
    for table, columns in _REQUIRED_COLUMNS.items():
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not info:
            # Table not present yet; CREATE TABLE IF NOT EXISTS creates it fresh
            # (with all columns) on a new database, so nothing to migrate.
            continue
        existing = {row[1] for row in info}
        for column, sql_type in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
    # Indexes on migrated columns are created here (not in _SCHEMA) so they run
    # after the column exists on legacy databases.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_engagement ON executions (engagement_id)"
    )


def _migrate_from_json(json_file, db):
    """Import records from executions.json into SQLite, then rename the JSON file."""
    try:
        with open(json_file, "r") as f:
            records = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    if not records:
        os.rename(json_file, json_file + ".migrated")
        return

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()

    # Only migrate if DB is empty
    count = cursor.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
    if count > 0:
        conn.close()
        return

    for r in records:
        cursor.execute(
            """INSERT OR IGNORE INTO executions
               (execution_id, target, security_phase, status,
                created_at, created_by, updated_at, updated_by,
                executor_id, request, result)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                r.get("execution_id"),
                r.get("target"),
                r.get("security_phase"),
                r.get("status", "QUEUED"),
                r.get("created_at"),
                r.get("created_by", "system"),
                r.get("updated_at"),
                r.get("updated_by"),
                r.get("executor_id"),
                json.dumps(r.get("request", {})),
                r.get("result"),
            ),
        )

    conn.commit()
    conn.close()
    os.rename(json_file, json_file + ".migrated")


@contextmanager
def _connect():
    """Yield a connection with WAL mode and busy timeout."""
    _ensure_db()
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_dict(row):
    """Convert a sqlite3.Row to the dict format the rest of the codebase expects."""
    d = dict(row)
    # Deserialize the request JSON string back into a dict
    if "request" in d and isinstance(d["request"], str):
        try:
            d["request"] = json.loads(d["request"])
        except (json.JSONDecodeError, TypeError):
            d["request"] = {}
    return d


def load_executions():
    """Return all execution records as a list of dicts."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM executions ORDER BY created_at").fetchall()
        return [_row_to_dict(r) for r in rows]


def append_execution(record):
    """Insert a new execution record."""
    with _connect() as conn:
        conn.execute(
            """INSERT INTO executions
               (execution_id, target, security_phase, status,
                created_at, created_by, updated_at, updated_by,
                executor_id, request, result, engagement_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["execution_id"],
                record["target"],
                record["security_phase"],
                record.get("status", "QUEUED"),
                record["created_at"],
                record.get("created_by", "system"),
                record.get("updated_at"),
                record.get("updated_by"),
                record.get("executor_id"),
                json.dumps(record.get("request", {})),
                record.get("result"),
                record.get("engagement_id"),
            ),
        )


def get_execution_by_id(execution_id):
    """Fetch a single execution by ID, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM executions WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def update_execution(execution_id, updates):
    """Apply a dict of updates to an execution. Returns the updated record or None."""
    with _connect() as conn:
        # Serialize request if present
        if "request" in updates and not isinstance(updates["request"], str):
            updates = dict(updates)
            updates["request"] = json.dumps(updates["request"])

        set_clauses = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [execution_id]

        conn.execute(f"UPDATE executions SET {set_clauses} WHERE execution_id = ?", values)

        row = conn.execute(
            "SELECT * FROM executions WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def is_target_busy_and_update(target, execution_id, updates):
    """Atomically check if target has a RUNNING execution and apply updates if not.

    Returns (busy: bool, updated_record: dict | None).
    - If busy: (True, None)
    - If not busy and update succeeds: (False, updated_record)
    - If execution not found: (False, None)
    """
    with _connect() as conn:
        # Single transaction — no TOCTOU gap
        busy = conn.execute(
            "SELECT 1 FROM executions WHERE target = ? AND status = 'RUNNING' LIMIT 1",
            (target,),
        ).fetchone()

        if busy:
            return True, None

        # Serialize request if present
        if "request" in updates and not isinstance(updates["request"], str):
            updates = dict(updates)
            updates["request"] = json.dumps(updates["request"])

        set_clauses = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [execution_id]

        cursor = conn.execute(f"UPDATE executions SET {set_clauses} WHERE execution_id = ?", values)

        if cursor.rowcount == 0:
            return False, None

        row = conn.execute(
            "SELECT * FROM executions WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        return False, _row_to_dict(row) if row else None


def find_stale_executions(timeout_minutes=30):
    """Find executions stuck in RUNNING or CLAIMED longer than timeout_minutes."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM executions
               WHERE status IN ('RUNNING', 'CLAIMED')
                 AND updated_at < ?
               ORDER BY updated_at""",
            (cutoff,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
