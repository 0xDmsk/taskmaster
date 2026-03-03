from datetime import datetime

from state.storage import (
    get_execution_by_id,
    update_execution,
    find_stale_executions,
)
from audit.audit_manager import log_event


def handle_recover_execution(args):
    """
    Recover stuck executions.

    Single recovery: provide execution_id to force-transition RUNNING/CLAIMED -> FAILED.
    Bulk recovery: set recover_stale=true to fail all executions stuck longer than
    timeout_minutes (default 30).
    """
    execution_id = args.get("execution_id")
    recover_stale = args.get("recover_stale", False)
    timeout_minutes = args.get("timeout_minutes", 30)
    reason = args.get("reason", "Manual recovery — execution stuck or agent crashed")

    recovered = []

    if execution_id:
        result = _recover_single(execution_id, reason)
        if "error" in result:
            return result
        recovered.append(result)

    elif recover_stale:
        stale = find_stale_executions(timeout_minutes=timeout_minutes)
        for execution in stale:
            eid = execution["execution_id"]
            result = _recover_single(
                eid, f"Auto-recovery: stuck > {timeout_minutes}min"
            )
            if "error" not in result:
                recovered.append(result)

    else:
        return {"error": "Provide execution_id or set recover_stale=true"}

    return {
        "status": "success",
        "recovered_count": len(recovered),
        "recovered": recovered,
    }


def _recover_single(execution_id, reason):
    """Force-transition a single RUNNING or CLAIMED execution to FAILED."""
    execution = get_execution_by_id(execution_id)
    if not execution:
        return {"error": f"Execution {execution_id} not found"}

    status = execution.get("status")
    if status not in ("RUNNING", "CLAIMED"):
        return {
            "error": f"Execution {execution_id} is {status}, not RUNNING or CLAIMED"
        }

    updates = {
        "status": "FAILED",
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": "recovery_tool",
        "result": reason,
    }

    updated = update_execution(execution_id, updates)
    if not updated:
        return {"error": f"Failed to update execution {execution_id}"}

    log_event(
        "execution_recovered",
        {
            "execution_id": execution_id,
            "previous_status": status,
            "reason": reason,
        },
    )

    return {
        "execution_id": execution_id,
        "previous_status": status,
        "new_status": "FAILED",
        "reason": reason,
    }
