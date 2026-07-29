"""request_playbook — expand a playbook (or inline steps) into a dependency chain.

Rather than hand-sequencing spawn/wait for each step, the orchestrator submits
one call and Taskmaster queues a linear chain of executions where step N depends
on step N-1. Workers pick up each step only once the previous one COMPLETES; if
any step fails, the rest of the chain is cancelled automatically (see
``state.state.cancel_blocked_dependents``).

Each step is reused through ``request_security_action``'s ``handle_request`` so
every step gets the same schema validation, phase policy, planning guardrails,
and audit logging as a normal request.
"""

from policies.playbooks import get_playbook, list_playbooks
from tools.request_security_action import handle_request


def handle_request_playbook(args):
    target = args.get("target")
    name = args.get("playbook")
    steps = args.get("steps")
    engagement_id = args.get("engagement_id")

    # Discovery affordance: no playbook and no steps → list what's available.
    if not name and not steps:
        return {
            "available_playbooks": list_playbooks(),
            "message": (
                "Provide 'playbook' (a built-in name) or 'steps' (an inline list of "
                "request_security_action step payloads), plus a 'target'."
            ),
        }

    if not target:
        return {"error": "target is required"}

    if name:
        playbook = get_playbook(name)
        if not playbook:
            return {
                "error": f"Unknown playbook '{name}'",
                "available_playbooks": [p["name"] for p in list_playbooks()],
            }
        steps = playbook["steps"]

    if not isinstance(steps, list) or not steps:
        return {"error": "Provide a known 'playbook' name or a non-empty 'steps' list"}

    created = []
    previous_id = None
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            return {
                "error": f"Playbook step {index} is not an object",
                "created_executions": created,
                "failed_step": index,
            }
        payload = dict(step)
        payload["target"] = target
        if engagement_id:
            payload["engagement_id"] = engagement_id
        # Chain each step to its predecessor. An explicit depends_on on the step
        # is preserved and extended so a step can also gate on outside work.
        if previous_id:
            existing = list(payload.get("depends_on") or [])
            if previous_id not in existing:
                existing.append(previous_id)
            payload["depends_on"] = existing

        result = handle_request(payload)
        if "error" in result:
            return {
                "error": f"Playbook step {index} rejected: {result['error']}",
                "details": result.get("details"),
                "created_executions": created,
                "failed_step": index,
                "message": (
                    "Earlier steps in this chain were already queued; the chain is "
                    "incomplete. Fix the step and resubmit the remainder, or cancel the "
                    "queued executions."
                ),
            }

        previous_id = result["execution_id"]
        created.append(
            {
                "step": index,
                "execution_id": previous_id,
                "phase": payload.get("phase"),
                "action": payload.get("skill") or payload.get("action_type"),
            }
        )

    return {
        "status": "QUEUED",
        "playbook": name or "inline",
        "target": target,
        "execution_ids": [c["execution_id"] for c in created],
        "chain": created,
        "message": (
            f"Queued {len(created)} chained executions for {target}. Each step waits "
            "for the previous to COMPLETE (and is cancelled if a prerequisite fails). "
            "Spawn a compatible agent; the worker will claim each step as it unblocks, "
            "then monitor the last execution_id with wait_for_completion."
        ),
    }
