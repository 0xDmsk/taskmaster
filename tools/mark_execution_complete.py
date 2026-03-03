from state.state import transition_execution


def handle_mark_execution_complete(args):
    execution_id = args.get("execution_id")
    executor_id = args.get("executor_id")
    result = args.get("result")
    status = args.get("status", "COMPLETED")

    if not execution_id or not executor_id:
        return {"error": "execution_id and executor_id are required"}

    try:
        execution = transition_execution(
            execution_id=execution_id,
            requested_status=status,
            executor_id=executor_id,
            result=result
        )
    except ValueError as e:
        return {"error": str(e)}

    if not execution:
        return {"error": "Execution not found"}

    return {
        "execution_id": execution_id,
        "status": execution.get("status"),
    }
