from datetime import datetime, timezone

from state.state import transition_execution
from state.storage import get_execution_by_id, update_execution

TERMINAL_STATES = {"COMPLETED", "FAILED"}


def handle_mark_execution_complete(args):
    execution_id = args.get("execution_id")
    executor_id = args.get("executor_id")
    result = args.get("result")
    interpretation = args.get("interpretation")
    status = args.get("status", "COMPLETED")

    if not execution_id or not executor_id:
        return {"error": "execution_id and executor_id are required"}

    existing = get_execution_by_id(execution_id)
    if not existing:
        return {"error": "Execution not found"}

    # The worker (operator) already transitions RUNNING -> COMPLETED/FAILED with
    # the raw result. The orchestrator then calls this tool to attach its
    # interpretation. Since terminal states have no self-transition, treat a
    # same-terminal-state call as a metadata attach (interpretation/result)
    # rather than an illegal COMPLETED -> COMPLETED transition. This is what
    # makes the documented "finalize with analysis" step actually work.
    current_status = existing.get("status")
    if current_status in TERMINAL_STATES and status == current_status:
        updates = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": executor_id,
        }
        if result is not None:
            updates["result"] = result
        if interpretation is not None:
            updates["interpretation"] = interpretation
        updated = update_execution(execution_id, updates)
        return {
            "execution_id": execution_id,
            "status": (updated or existing).get("status"),
            "interpretation_attached": interpretation is not None,
        }

    try:
        execution = transition_execution(
            execution_id=execution_id,
            requested_status=status,
            executor_id=executor_id,
            result=result,
            interpretation=interpretation,
        )
    except ValueError as e:
        return {"error": str(e)}

    if not execution:
        return {"error": "Execution not found"}

    return {
        "execution_id": execution_id,
        "status": execution.get("status"),
    }
