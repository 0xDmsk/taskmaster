from datetime import datetime, timezone
from typing import Optional, Dict

from state.storage import (
    get_execution_by_id,
    update_execution,
    append_execution,
    load_executions,
    is_target_busy_and_update,
)
from policies.state_policy import is_lifecycle_allowed


def create_execution(
    execution_id: str,
    target: str,
    security_phase: str,
    request_payload: dict,
    created_by: str = "system",
    engagement_id: str | None = None,
    depends_on: list | None = None,
) -> dict:
    """
    Create a new execution in QUEUED status.

    ``engagement_id`` optionally binds the execution to a reporting engagement so
    the dashboard can scope metrics and lists to it unambiguously (executions on
    shared scope no longer collide across engagements).

    ``depends_on`` is an optional list of prerequisite execution_ids. The
    execution is withheld from workers until every prerequisite has COMPLETED,
    and is CANCELLED if any prerequisite fails (see cancel_blocked_dependents).
    """
    record = {
        "execution_id": execution_id,
        "target": target,
        "security_phase": security_phase,
        "status": "QUEUED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": created_by,
        "updated_at": None,
        "updated_by": None,
        "executor_id": None,
        "request": request_payload,
        "result": None,
        "engagement_id": engagement_id,
        "depends_on": list(depends_on) if depends_on else None,
    }

    append_execution(record)
    return record


def dependencies_satisfied(execution: dict) -> bool:
    """True when every prerequisite of ``execution`` has COMPLETED (or it has none)."""
    deps = execution.get("depends_on") or []
    if not deps:
        return True
    by_id = {e["execution_id"]: e for e in load_executions()}
    return all(by_id.get(dep, {}).get("status") == "COMPLETED" for dep in deps)


def cancel_blocked_dependents(execution_id: str, reason: str | None = None) -> list:
    """Recursively CANCEL QUEUED/CLAIMED executions blocked by a dead prerequisite.

    When an execution can no longer reach COMPLETED (it FAILED or was CANCELLED),
    anything depending on it can never run. Marking those dependents CANCELLED
    keeps dead work out of the queue and off the target lock, and recursion
    handles multi-step chains. Returns the cancelled execution_ids.
    """
    reason = reason or f"Cancelled: dependency {execution_id} did not complete"
    now = datetime.now(timezone.utc).isoformat()
    cancelled = []
    for e in load_executions():
        deps = e.get("depends_on") or []
        if execution_id in deps and e.get("status") in ("QUEUED", "CLAIMED"):
            update_execution(
                e["execution_id"],
                {
                    "status": "CANCELLED",
                    "updated_at": now,
                    "updated_by": "dependency",
                    "result": reason,
                },
            )
            cancelled.append(e["execution_id"])
            cancelled.extend(cancel_blocked_dependents(e["execution_id"], reason))
    return cancelled


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
    interpretation: Optional[str] = None,
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

    # Dependency gate: a QUEUED execution cannot be claimed until every
    # prerequisite has COMPLETED. Workers only see ready tasks via
    # get_queued_executions, but a direct claim must not bypass the gate.
    if current_status == "QUEUED" and requested_status == "CLAIMED":
        if not dependencies_satisfied(execution):
            raise ValueError(f"Execution {execution_id} has unmet dependencies; not ready to claim")

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
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": executor_id,
    }

    # Bind executor_id on claim (first bind)
    if current_status == "QUEUED" and requested_status == "CLAIMED":
        updates["executor_id"] = executor_id

    if result is not None:
        updates["result"] = result

    if interpretation is not None:
        updates["interpretation"] = interpretation

    # Atomic target-busy check + update for RUNNING transitions
    if requested_status == "RUNNING":
        busy, updated = is_target_busy_and_update(target, execution_id, updates)
        if busy:
            raise ValueError(f"Target {target} is currently busy with another execution.")
        return updated

    updated = update_execution(execution_id, updates)
    # A dead execution can never satisfy its dependents — cancel them so the
    # chain doesn't hang QUEUED forever.
    if updated and requested_status in ("FAILED", "CANCELLED"):
        cancel_blocked_dependents(
            execution_id,
            f"Cancelled: dependency {execution_id} {requested_status.lower()}",
        )
    return updated


def heartbeat_execution(execution_id: str, executor_id: str) -> Optional[dict]:
    """
    Refresh ``updated_at`` on a RUNNING execution without changing status.

    Long skill runs (e.g. a nuclei scan near the wall-clock ceiling) block the
    worker's main loop for the whole duration, so without a periodic touch
    ``updated_at`` freezes at RUNNING-transition time and the reaper's
    stale-heartbeat check (state/../tools/reaper.py) can't tell a legitimately
    long-running scan from a hung one. Callers must own the execution
    (executor_id match) and it must still be RUNNING — a heartbeat is not a
    state transition and never touches target locking or lifecycle policy.
    """
    execution = get_execution_by_id(execution_id)
    if not execution:
        return None
    if execution.get("status") != "RUNNING":
        return None
    if execution.get("executor_id") != executor_id:
        raise ValueError(
            f"Executor mismatch: execution owned by {execution.get('executor_id')}, "
            f"caller is {executor_id}"
        )
    return update_execution(
        execution_id,
        {"updated_at": datetime.now(timezone.utc).isoformat()},
    )


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
    """Return QUEUED executions that are ready to run (all dependencies COMPLETED).

    Executions still waiting on an unfinished prerequisite are withheld from
    workers until it completes. A dependent whose prerequisite fails is
    CANCELLED elsewhere (see cancel_blocked_dependents), so it never lingers
    here as permanently-blocked QUEUED work.
    """
    executions = load_executions()
    by_id = {e["execution_id"]: e for e in executions}
    ready = []
    for e in executions:
        if e.get("status") != "QUEUED":
            continue
        deps = e.get("depends_on") or []
        if all(by_id.get(dep, {}).get("status") == "COMPLETED" for dep in deps):
            ready.append(e)
    return ready
