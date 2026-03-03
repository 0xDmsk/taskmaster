from state.state import transition_execution

def handle_claim_execution(args):
    execution_id = args.get("execution_id")
    executor_id = args.get("executor_id")

    if not execution_id or not executor_id:
        return {"error": "execution_id and executor_id are required"}

    try:
        execution = transition_execution(
            execution_id=execution_id,
            requested_status="CLAIMED",
            executor_id=executor_id
        )
    except ValueError as e:
        return {"error": str(e)}

    if not execution:
        return {"error": "Execution not found"}

    return {
        "execution_id": execution_id,
        "status": "CLAIMED"
    }
