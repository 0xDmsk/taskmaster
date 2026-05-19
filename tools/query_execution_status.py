from datetime import datetime

from state.state import get_execution_state


def _seconds_since(iso_ts):
    if not iso_ts:
        return None
    try:
        return (datetime.utcnow() - datetime.fromisoformat(iso_ts)).total_seconds()
    except (TypeError, ValueError):
        return None


def handle_query_execution_status(args):
    execution_id = args.get("execution_id")

    if not execution_id:
        return {"error": "execution_id is required"}

    execution = get_execution_state(execution_id)

    if not execution:
        return {
            "error": "Execution not found",
            "execution_id": execution_id,
        }

    if args.get("verbose"):
        return {
            "execution_id": execution_id,
            "status": execution.get("status"),
            "security_phase": execution.get("security_phase"),
            "execution": execution,
        }

    last_activity = execution.get("updated_at") or execution.get("created_at")
    return {
        "execution_id": execution_id,
        "status": execution.get("status"),
        "security_phase": execution.get("security_phase"),
        "target": execution.get("target"),
        "executor_id": execution.get("executor_id"),
        "updated_at": execution.get("updated_at"),
        "seconds_since_update": _seconds_since(last_activity),
        "has_result": bool(execution.get("result")),
        "has_interpretation": bool(execution.get("interpretation")),
    }
