from state.state import transition_execution
from state.surface import ingest_after_completion

def handle_complete_execution(args):
    execution_id = args.get("execution_id")
    executor_id = args.get("executor_id")
    result = args.get("result")
    interpretation = args.get("interpretation")

    if not execution_id or not executor_id:
        return {"error": "execution_id and executor_id are required"}

    try:
        execution = transition_execution(
            execution_id=execution_id,
            requested_status="COMPLETED",
            executor_id=executor_id,
            result=result,
            interpretation=interpretation,
        )
    except ValueError as e:
        return {"error": str(e)}

    if not execution:
        return {"error": "Execution not found"}

    # Audit Logging
    from audit.audit_manager import log_event, update_report
    log_event("execution_completed", execution)
    update_report(execution)

    response = {
        "execution_id": execution_id,
        "status": "COMPLETED",
        "executor_id": execution.get("executor_id"),
    }
    ingested = ingest_after_completion(execution_id)
    if ingested:
        response["surface_endpoints_ingested"] = ingested
    return response
