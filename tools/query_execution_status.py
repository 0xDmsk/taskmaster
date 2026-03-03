from state.state import get_execution_state


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

    return {
        "execution_id": execution_id,
        "status": execution.get("status"),
        "security_phase": execution.get("security_phase"),
        "execution": execution,
    }
