import json
import os
import fcntl
from datetime import datetime

import config

AUDIT_DIR = os.path.join(config.WORK_DIR, "audit")
LOG_FILE = os.path.join(AUDIT_DIR, "audit_log.jsonl")
REPORT_FILE = os.path.join(AUDIT_DIR, "session_report.md")


def init_audit():
    os.makedirs(AUDIT_DIR, exist_ok=True)

    try:
        with open(REPORT_FILE, "x") as f:
            f.write(f"# Security Assessment Report\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Execution Summary\n\n")
            f.write("| ID | Phase | Target | Action | Status | Result |\n")
            f.write("|----|-------|--------|--------|--------|--------|\n")
    except FileExistsError:
        pass


def log_event(event_type, data):
    """Logs a raw event to the JSONL file."""
    init_audit()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "data": data,
    }
    with open(LOG_FILE, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(entry) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def update_report(execution_record):
    """Appends or updates an entry in the markdown report."""
    init_audit()
    eid = execution_record.get("execution_id", "N/A")
    phase = execution_record.get("security_phase", "N/A")
    target = execution_record.get("target", "N/A")
    status = execution_record.get("status", "N/A")
    req = execution_record.get("request", {})
    action = req.get("action_type", "N/A")

    # Summary Table Row
    result_summary = "Pending"
    if status == "COMPLETED":
        result_summary = "[Success](#" + eid[:8] + ")"
    elif status == "FAILED":
        result_summary = "[Failed](#" + eid[:8] + ")"

    row = f"| {eid[:8]} | {phase} | {target} | {action} | {status} | {result_summary} |\n"

    with open(REPORT_FILE, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(row)

            # Detailed entry if completed/failed
            if status in ["COMPLETED", "FAILED"]:
                f.write(f"\n### Detailed Result: {eid[:8]}\n\n")
                f.write(f"- **Target:** {target}\n")
                f.write(f"- **Justification:** {req.get('justification', 'N/A')}\n")
                f.write(f"- **Command:** `{req.get('command', 'N/A')}`\n")

                result_text = execution_record.get("result", "")
                if result_text and "[STRUCTURED_DATA]" in result_text:
                    parts = result_text.split("[STRUCTURED_DATA]")
                    f.write(f"\n#### Findings\n\n```json\n{parts[1].strip()}\n```\n\n")
                    f.write(
                        f"#### Raw Output\n\n"
                        f"<details><summary>Click to expand</summary>\n\n"
                        f"```\n{parts[0].strip()}\n```\n\n"
                        f"</details>\n\n"
                    )
                else:
                    f.write(f"\n#### Raw Output\n\n```\n{result_text}\n```\n\n")

                f.write("---\n\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
