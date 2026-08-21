"""request_batch — fan one skill out over many bounded shards.

Where ``request_playbook`` chains *heterogeneous* steps for one target,
``request_batch`` queues N executions of the *same* step across a list of shards
— one bounded execution per shard. This is how you tackle work that will never
fit a single execution window (a full nuclei scan, enumeration over a big scope):
split it into sub-window pieces. A chain/fan of bounded executions also sidesteps
the reaper's per-execution ceilings, because each shard is a fresh short run.

Two shard shapes:

* **Different targets → parallel.** The per-target lock only serializes the
  *same* target, so shards on different targets run concurrently across workers.
  e.g. subdomain enum with one shard per domain.
* **Same target → pass ``sequential: true``.** The shards are chained
  (``depends_on``) and offered one at a time; without this the target lock would
  leave all but one QUEUED while workers spin trying to start them. e.g. a full
  nuclei scan split by template group, all against one host.

Each shard is a dict merged over the shared base step: it may override ``target``
and deep-merges into ``arguments`` (plus an optional ``label`` for readability).
Every shard goes through ``request_security_action``'s ``handle_request``, so it
gets the same schema validation, phase policy, and audit logging as a hand-issued
request. Results are per-shard (each writes its own envelope + artifacts); the
orchestrator aggregates them (Findings.md / recon-data.md), same as any fan of
executions.
"""

from tools.request_security_action import handle_request

# Keys consumed by the batch expander itself, not part of a step payload.
_CONTROL_KEYS = {"shards", "sequential", "target", "arguments", "depends_on"}


def handle_request_batch(args):
    shards = args.get("shards")
    if not isinstance(shards, list) or not shards:
        return {"error": "Provide a non-empty 'shards' list (one entry per bounded unit of work)."}

    base_target = args.get("target")
    sequential = bool(args.get("sequential", False))
    base_arguments = args.get("arguments") or {}
    base_depends_on = list(args.get("depends_on") or [])
    # Everything else (phase, agent_role, action_type, skill, justification,
    # expected_output, engagement_id) is the shared step template.
    base_step = {k: v for k, v in args.items() if k not in _CONTROL_KEYS}

    created = []
    previous_id = None
    for index, shard in enumerate(shards, start=1):
        if not isinstance(shard, dict):
            return {
                "error": f"Shard {index} is not an object",
                "created_executions": created,
                "failed_shard": index,
            }

        payload = dict(base_step)
        payload["target"] = shard.get("target") or base_target
        if not payload["target"]:
            return {
                "error": (f"Shard {index} has no target — set shard.target or a base 'target'."),
                "created_executions": created,
                "failed_shard": index,
            }
        # Shallow-merge shard arguments over the base arguments.
        payload["arguments"] = {**base_arguments, **(shard.get("arguments") or {})}

        depends = list(base_depends_on)
        if sequential and previous_id:
            depends.append(previous_id)
        for dep in shard.get("depends_on") or []:
            if dep not in depends:
                depends.append(dep)
        if depends:
            payload["depends_on"] = depends

        result = handle_request(payload)
        if "error" in result:
            return {
                "error": f"Shard {index} rejected: {result['error']}",
                "details": result.get("details"),
                "created_executions": created,
                "failed_shard": index,
                "message": (
                    "Earlier shards were already queued; the batch is incomplete. Fix the "
                    "shard and resubmit the remainder, or cancel the queued executions."
                ),
            }

        previous_id = result["execution_id"]
        created.append(
            {
                "shard": index,
                "label": shard.get("label"),
                "execution_id": previous_id,
                "target": payload["target"],
            }
        )

    return {
        "status": "QUEUED",
        "mode": "sequential" if sequential else "parallel",
        "count": len(created),
        "execution_ids": [c["execution_id"] for c in created],
        "shards": created,
        "message": (
            f"Queued {len(created)} shard executions ("
            + (
                "chained — each runs after the previous COMPLETES"
                if sequential
                else "independent — different targets run in parallel across workers, "
                "same-target shards serialize on the per-target lock"
            )
            + "). Spawn one or more compatible agents, then monitor "
            + ("the last execution_id" if sequential else "each execution_id")
            + " with wait_for_completion. Each shard writes its own envelope/artifacts; "
            "aggregate the shard findings in your notes."
        ),
    }
