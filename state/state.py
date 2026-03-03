from datetime import datetime
from typing import Optional, Dict

from state.storage import (
    get_execution_by_id,
    update_execution,
    append_execution,
    load_executions,
    is_target_busy_and_update,
    find_stale_executions,
)
from policies.state_policy import is_lifecycle_allowed


def create_execution(
    execution_id: str,
    target: str,
    security_phase: str,
    request_payload: dict,
    created_by: str = "system",
) -> dict:
    """
    Create a new execution in QUEUED status.
    """
    record = {
        "execution_id": execution_id,
        "target": target,
        "security_phase": security_phase,
        "status": "QUEUED",
        "created_at": datetime.utcnow().isoformat(),
        "created_by": created_by,
        "updated_at": None,
        "updated_by": None,
        "executor_id": None,
        "request": request_payload,
        "result": None,
    }

    append_execution(record)
    return record


def is_target_busy(target: str) -> bool:
    """
    Checks if there is any execution currently RUNNING for the given target.
    """
    executions = load_executions()
    for e in executions:
        if e.get("target") == target and e.get("status") == "RUNNING":
            return True
    return False


def transition_execution(
    execution_id: str,
    requested_status: str,
    executor_id: str,
    result: Optional[str] = None,
) -> Optional[dict]:
    """
    Attempt to transition an execution to a new lifecycle status.
    Enforces lifecycle policy, target locking, and executor_id ownership.
    """

    execution = get_execution_by_id(execution_id)
    if not execution:
        return None

    current_status = execution.get("status")
    target = execution.get("target")

    if not is_lifecycle_allowed(current_status, requested_status):
        raise ValueError(f"Illegal transition {current_status} -> {requested_status}")

    # Executor ownership verification:
    # CLAIMED→RUNNING and RUNNING→COMPLETED/FAILED must match the executor who claimed/started.
    if current_status in ("CLAIMED", "RUNNING"):
        stored_executor = execution.get("executor_id")
        if stored_executor and stored_executor != executor_id:
            raise ValueError(
                f"Executor mismatch: execution owned by {stored_executor}, "
                f"caller is {executor_id}"
            )

    updates = {
        "status": requested_status,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": executor_id,
    }

    # Bind executor_id on claim (first bind)
    if current_status == "QUEUED" and requested_status == "CLAIMED":
        updates["executor_id"] = executor_id

    if result is not None:
        updates["result"] = result

    # Atomic target-busy check + update for RUNNING transitions
    if requested_status == "RUNNING":
        busy, updated = is_target_busy_and_update(target, execution_id, updates)
        if busy:
            raise ValueError(
                f"Target {target} is currently busy with another execution."
            )
        return updated

    return update_execution(execution_id, updates)


def get_execution_state(execution_id: str) -> Optional[dict]:
    """
    Read-only accessor.
    """
    return get_execution_by_id(execution_id)


def get_target_state(target: str) -> Dict[str, Optional[str]]:
    """
    Returns the last known security phase for a target.
    """
    executions = load_executions()
    target_execs = [e for e in executions if e.get("target") == target]

    if not target_execs:
        return {"last_phase": None}

    # Assuming the last created execution reflects the current intent/state
    # We sort by created_at just in case, though append order should suffice.
    target_execs.sort(key=lambda x: x.get("created_at", ""))

    last_exec = target_execs[-1]
    return {"last_phase": last_exec.get("security_phase")}


def get_queued_executions():
    """
    Returns a list of all executions currently in QUEUED status.
    """
    executions = load_executions()
    return [e for e in executions if e.get("status") == "QUEUED"]
