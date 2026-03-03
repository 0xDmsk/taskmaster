from state.state import transition_execution

def handle_complete_execution(args):
    execution_id = args.get("execution_id")
    executor_id = args.get("executor_id")
    result = args.get("result")

    if not execution_id or not executor_id:
        return {"error": "execution_id and executor_id are required"}

    try:
        execution = transition_execution(
            execution_id=execution_id,
            requested_status="COMPLETED",
            executor_id=executor_id,
            result=result
        )
    except ValueError as e:
        return {"error": str(e)}

    if not execution:
        return {"error": "Execution not found"}

    # Audit Logging
    from audit.audit_manager import log_event, update_report
    log_event("execution_completed", execution)
    update_report(execution)

    return {
        "execution_id": execution_id,
        "status": "COMPLETED"
    }
