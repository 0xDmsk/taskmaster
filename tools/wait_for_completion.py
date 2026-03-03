import os
import time

from state.state import get_execution_state


TERMINAL_STATES = {"COMPLETED", "FAILED"}

DEFAULT_TIMEOUT = int(os.environ.get("WAIT_DEFAULT_TIMEOUT", "600"))
POLL_INTERVAL = int(os.environ.get("WAIT_POLL_INTERVAL", "2"))


def handle_wait_for_completion(args):
    execution_id = args.get("execution_id")

    if not execution_id:
        return {"error": "execution_id is required"}

    timeout_seconds = args.get("timeout_seconds", DEFAULT_TIMEOUT)

    execution = get_execution_state(execution_id)
    if not execution:
        return {"error": "Execution not found", "execution_id": execution_id}

    # Already terminal — return immediately
    status = execution.get("status")
    if status in TERMINAL_STATES:
        return {
            "execution_id": execution_id,
            "status": status,
            "result": execution.get("result"),
        }

    # Poll until terminal or timeout
    elapsed = 0.0
    while elapsed < timeout_seconds:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        execution = get_execution_state(execution_id)
        if not execution:
            return {"error": "Execution disappeared", "execution_id": execution_id}

        status = execution.get("status")
        if status in TERMINAL_STATES:
            return {
                "execution_id": execution_id,
                "status": status,
                "result": execution.get("result"),
            }

    # Timeout
    return {
        "execution_id": execution_id,
        "status": "TIMEOUT",
        "current_status": status,
        "elapsed_seconds": elapsed,
        "message": f"Execution did not complete within {timeout_seconds}s. "
        "Call wait_for_completion again to keep waiting, or investigate.",
    }
