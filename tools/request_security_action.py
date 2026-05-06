import uuid
from jsonschema import validate, ValidationError

from state.state import get_target_state, create_execution
from policies.state_policy import is_security_phase_allowed
from targeting import _target_parts

REQUEST_SECURITY_ACTION_SCHEMA = {
    "type": "object",
    "required": [
        "agent_role",
        "phase",
        "target",
        "action_type",
        "justification",
        "expected_output",
    ],
    "properties": {
        "agent_role": {
            "type": "string",
            "enum": [
                "recon",
                "enumeration",
                "exploitation",
                "post_exploitation",
                "reporting",
            ],
        },
        "phase": {"type": "string"},
        "target": {"type": "string"},
        "action_type": {"type": "string", "enum": ["skill", "python", "playwright", "playwright_skill"]},
        "skill": {"type": "string"},
        "arguments": {"type": "object"},
        "command": {"type": "string"},
        "script": {"type": "string"},
        "allow_complex_tooling": {"type": "boolean"},
        "justification": {"type": "string", "minLength": 50},
        "expected_output": {"type": "string"},
    },
}


PASSIVE_WEB_SKILLS = {"web.HttpxDetect"}
PASSIVE_WEB_KEYWORDS = {
    "passive",
    "minimal",
    "simple",
    "lightweight",
    "headers",
    "header",
    "title",
    "status code",
    "status",
    "final url",
    "html",
    "metadata",
    "scripts",
    "forms",
    "links",
    "technology",
    "fingerprint",
    "fetch",
    "reachable",
}


def _is_url_target(target: str) -> bool:
    return bool(_target_parts(target).get("host")) and "://" in target


def _should_prefer_python_guardrail(payload: dict) -> bool:
    if payload.get("allow_complex_tooling"):
        return False

    if payload.get("action_type") != "skill":
        return False

    if payload.get("skill") not in PASSIVE_WEB_SKILLS:
        return False

    if payload.get("phase") not in {"reconnaissance", "enumeration"}:
        return False

    target = payload.get("target", "")
    if not _is_url_target(target):
        return False

    free_text = " ".join(
        [
            payload.get("justification", ""),
            payload.get("expected_output", ""),
        ]
    ).lower()
    return any(keyword in free_text for keyword in PASSIVE_WEB_KEYWORDS)


def handle_request(payload):
    # 1. Schema validation
    try:
        validate(instance=payload, schema=REQUEST_SECURITY_ACTION_SCHEMA)
    except ValidationError as e:
        return {
            "error": "Schema validation failed",
            "details": e.message,
        }

    # 2. Conditional validation based on action_type
    action_type = payload.get("action_type")

    if action_type == "skill":
        if not payload.get("skill"):
            return {
                "error": "Validation failed",
                "details": "'skill' field is required when action_type is 'skill'",
            }
    elif action_type == "python":
        if not payload.get("command"):
            return {
                "error": "Validation failed",
                "details": "'command' field is required when action_type is 'python'",
            }
    elif action_type == "playwright_skill":
        if not payload.get("skill"):
            return {
                "error": "Validation failed",
                "details": "'skill' field is required when action_type is 'playwright_skill'",
            }
    elif action_type == "playwright":
        if not payload.get("script"):
            return {
                "error": "Validation failed",
                "details": "'script' field is required when action_type is 'playwright'",
            }

    if _should_prefer_python_guardrail(payload):
        return {
            "error": "Planning guardrail triggered",
            "details": (
                "This request describes simple passive web reconnaissance against a URL target, "
                "but uses an external skill. Prefer action_type 'python' for lightweight fetch/"
                "parse tasks and reserve web.HttpxDetect for cases where external fingerprinting "
                "is explicitly required."
            ),
            "suggestion": (
                "Resubmit as action_type 'python', or set allow_complex_tooling=true if you "
                "intentionally want the external tool path."
            ),
        }

    target = payload["target"]
    requested_phase = payload["phase"]

    # 3. Platform constraint validation (only for python with shell commands)
    command = payload.get("command", "")
    if action_type == "python" and command:  # playwright types run in their own container
        from policies.command_validator import validate_command

        constraint_result = validate_command(command)

        if not constraint_result["allowed"]:
            blocks = [v for v in constraint_result["violations"] if v["severity"] == "block"]
            return {
                "error": "Platform constraint violation",
                "details": (
                    "This command will fail or produce unreliable results in the macOS "
                    "container VM. See policies/platform_constraints.md for full details."
                ),
                "violations": blocks,
            }

        warnings = [v for v in constraint_result["violations"] if v["severity"] == "warn"]
    else:
        warnings = []

    # 4. Target phase policy enforcement
    state = get_target_state(target)

    if not is_security_phase_allowed(state["last_phase"], requested_phase):
        return {
            "error": "Policy violation",
            "details": (
                f"Cannot transition from "
                f"{state['last_phase']} to {requested_phase} "
                f"for target {target}"
            ),
        }

    # 5. Create execution
    execution_id = str(uuid.uuid4())

    record = create_execution(
        execution_id=execution_id,
        target=target,
        security_phase=requested_phase,
        request_payload=payload,
        created_by=payload.get("agent_role", "unknown"),
    )

    # 6. Audit Logging
    from audit.audit_manager import log_event, update_report

    log_event("request_created", record)
    update_report(record)

    result = {
        "execution_id": execution_id,
        "status": "QUEUED",
        "message": (
            "Security action accepted for processing. This only queued the "
            "execution; spawn a compatible agent unless you have already "
            "verified a matching live worker for this target."
        ),
        "recommended_next_steps": [
            "Spawn a compatible agent with spawn_agent unless a matching live worker is already running",
            "Then call wait_for_completion with this execution_id",
        ],
    }

    if warnings:
        result["platform_warnings"] = [
            {"message": w["message"], "suggestion": w["suggestion"]} for w in warnings
        ]

    return result
