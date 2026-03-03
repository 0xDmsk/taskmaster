import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

import config

_DB_PATH = os.environ.get(
    "STATE_DB", os.path.join(config.WORK_DIR, "state", "executions.db")
)

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
    result TEXT
);
CREATE INDEX IF NOT EXISTS idx_target_status ON executions (target, status);
CREATE INDEX IF NOT EXISTS idx_status ON executions (status);
"""


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
    conn.executescript(_SCHEMA)
    conn.close()

    # Auto-migrate from legacy JSON file
    json_file = os.path.join(os.path.dirname(db), "executions.json")
    if os.path.exists(json_file):
        _migrate_from_json(json_file, db)


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
                executor_id, request, result)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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

        conn.execute(
            f"UPDATE executions SET {set_clauses} WHERE execution_id = ?", values
        )

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

        cursor = conn.execute(
            f"UPDATE executions SET {set_clauses} WHERE execution_id = ?", values
        )

        if cursor.rowcount == 0:
            return False, None

        row = conn.execute(
            "SELECT * FROM executions WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        return False, _row_to_dict(row) if row else None


def find_stale_executions(timeout_minutes=30):
    """Find executions stuck in RUNNING or CLAIMED longer than timeout_minutes."""
    cutoff = (datetime.utcnow() - timedelta(minutes=timeout_minutes)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM executions
               WHERE status IN ('RUNNING', 'CLAIMED')
                 AND updated_at < ?
               ORDER BY updated_at""",
            (cutoff,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
