#!/usr/bin/env python3
"""Export Taskmaster's reporting tables to JSON for the shared Google Sites app.

The shared findings site (``integrations/google_sites/``) imports this file on its
"Import from Taskmaster" page. Records keep their Taskmaster ids, so exporting
and importing the same engagement again refreshes it instead of duplicating it.

    uv run python scripts/export_reporting_json.py -o taskmaster-export.json
    uv run python scripts/export_reporting_json.py --engagement eng_abc --engagement eng_def -o out.json

Reads the database at ``STATE_DB`` (default ``<WORK_DIR>/runtime/state/executions.db``,
with ``WORK_DIR`` from ``TASKMASTER_WORK_DIR`` or the current directory). Use
``--db`` to point at another engagement folder's database.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from state import storage

FORMAT = "taskmaster-reporting-export"

# table -> (columns, engagement filter SQL)
TABLES = {
    "engagements": (
        "engagement_id, name, client_name, status, summary, created_at, updated_at",
        "engagement_id IN ({ids})",
    ),
    "report_assets": (
        "asset_id, engagement_id, kind, value, description, created_at, updated_at",
        "engagement_id IN ({ids})",
    ),
    "findings": (
        "finding_id, engagement_id, title, severity, category, status, affected, description,"
        " impact, proof_of_concept, remediation, cvss_score, cvss_vector, source_execution_id,"
        " created_at, created_by, updated_at, updated_by",
        "engagement_id IN ({ids})",
    ),
    "finding_evidence": (
        "evidence_id, finding_id, kind, title, body, artifact_path, url, sort_order,"
        " created_at, created_by",
        "finding_id IN (SELECT finding_id FROM findings WHERE engagement_id IN ({ids}))",
    ),
    "finding_references": (
        "reference_id, finding_id, label, url, sort_order, created_at",
        "finding_id IN (SELECT finding_id FROM findings WHERE engagement_id IN ({ids}))",
    ),
}


def export(db_path: str, engagement_ids: list[str] | None) -> dict:
    if not os.path.exists(db_path):
        raise SystemExit(f"No Taskmaster database at {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    out: dict = {
        "format": FORMAT,
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        for table, (columns, where) in TABLES.items():
            sql = f"SELECT {columns} FROM {table}"
            params: list[str] = []
            if engagement_ids:
                sql += " WHERE " + where.format(ids=",".join("?" * len(engagement_ids)))
                params = list(engagement_ids)
            out[table] = [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", default=storage._db_path(), help="Path to executions.db")
    parser.add_argument(
        "--engagement",
        action="append",
        dest="engagements",
        help="Engagement id to export (repeatable; default: all engagements)",
    )
    parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    args = parser.parse_args()

    data = export(args.db, args.engagements)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    counts = ", ".join(f"{len(data[t])} {t}" for t in TABLES)
    print(f"Exported {counts}", file=sys.stderr)


if __name__ == "__main__":
    main()
