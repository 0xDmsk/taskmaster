import uuid
from jsonschema import validate, ValidationError

from state.state import get_target_state, create_execution
from policies.state_policy import is_security_phase_allowed
from policies.command_validator import validate_command


REQUEST_SECURITY_ACTION_SCHEMA = {
    "type": "object",
    "required": [
        "agent_role",
        "phase",
        "target",
        "action_type",
        "tool",
        "command",
        "justification",
        "expected_output"
    ],
    "properties": {
        "agent_role": {
            "type": "string",
            "enum": [
                "recon",
                "enumeration",
                "exploitation",
                "post_exploitation",
                "reporting"
            ]
        },
        "phase": {
            "type": "string"
        },
        "target": {
            "type": "string"
        },
        "action_type": {
            "type": "string"
        },
        "tool": {
            "type": "string"
        },
        "command": {
            "type": "string"
        },
        "justification": {
            "type": "string",
            "minLength": 50
        },
        "expected_output": {
            "type": "string"
        }
    }
}


def handle_request(payload):
    # 1. Schema validation
    try:
        validate(instance=payload, schema=REQUEST_SECURITY_ACTION_SCHEMA)
    except ValidationError as e:
        return {
            "error": "Schema validation failed",
            "details": e.message
        }

    target = payload["target"]
    requested_phase = payload["phase"]

    # 2. Platform constraint validation
    command = payload.get("command", "")
    constraint_result = validate_command(command)

    if not constraint_result["allowed"]:
        blocks = [v for v in constraint_result["violations"] if v["severity"] == "block"]
        return {
            "error": "Platform constraint violation",
            "details": (
                "This command will fail or produce unreliable results in the macOS container VM. "
                "See policies/platform_constraints.md for full details."
            ),
            "violations": blocks,
        }

    # Attach warnings to the response later if there are non-blocking violations
    warnings = [v for v in constraint_result["violations"] if v["severity"] == "warn"]

    # 3. Target phase policy enforcement
    state = get_target_state(target)

    if not is_security_phase_allowed(state["last_phase"], requested_phase):
        return {
            "error": "Policy violation",
            "details": (
                f"Cannot transition from "
                f"{state['last_phase']} to {requested_phase} "
                f"for target {target}"
            )
        }

    # 4. Create execution
    execution_id = str(uuid.uuid4())

    record = create_execution(
        execution_id=execution_id,
        target=target,
        security_phase=requested_phase,
        request_payload=payload,
        created_by=payload.get("agent_role", "unknown")
    )

    # 5. Audit Logging
    from audit.audit_manager import log_event, update_report
    log_event("request_created", record)
    update_report(record)

    result = {
        "execution_id": execution_id,
        "status": "QUEUED",
        "message": "Security action accepted for processing",
    }

    if warnings:
        result["platform_warnings"] = [
            {"message": w["message"], "suggestion": w["suggestion"]}
            for w in warnings
        ]

    return result
