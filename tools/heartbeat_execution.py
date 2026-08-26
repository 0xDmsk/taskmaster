from state.state import heartbeat_execution


def handle_heartbeat_execution(args):
    execution_id = args.get("execution_id")
    executor_id = args.get("executor_id")

    if not execution_id or not executor_id:
        return {"error": "execution_id and executor_id are required"}

    try:
        execution = heartbeat_execution(execution_id=execution_id, executor_id=executor_id)
    except ValueError as e:
        return {"error": str(e)}

    if not execution:
        return {"error": "Execution not found or not RUNNING"}

    return {
        "execution_id": execution_id,
        "status": execution.get("status"),
        "updated_at": execution.get("updated_at"),
    }
