from state.state import get_execution_state


TERMINAL_STATES = {"COMPLETED", "FAILED"}


def handle_fetch_execution_result(args):
    execution_id = args.get("execution_id")

    if not execution_id:
        return {"error": "execution_id is required"}

    execution = get_execution_state(execution_id)

    if not execution:
        return {"error": "Execution not found"}

    status = execution.get("status")

    if status not in TERMINAL_STATES:
        return {
            "error": "Execution not finished",
            "status": status,
        }

    return {
        "execution_id": execution_id,
        "status": status,
        "result": execution.get("result"),
    }
