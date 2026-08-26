"""resplit_timed_out_shard — narrow a timed-out nuclei shard and requeue it.

A shard (from request_batch or a plain request_security_action) that comes
back with findings.timed_out=true didn't cover its full scope — the
wall-clock killed it before nuclei finished. There is no per-template resume
checkpoint to pick up from (nuclei is hard-killed via SIGKILL on timeout, not
signaled, so it never gets a chance to write one — see skills/base.py,
skills/web.py execute_shell overrides). The practical fix is the same one a
human operator reaches for: shrink the scope and try again. This tool
automates exactly that shrink instead of relying on prose in
OPERATIONAL_GUIDE.md being re-derived by the orchestrating LLM every time.

Two narrowing strategies, chosen by skill:

* web.NucleiScan — split a comma-separated `tags` argument into N roughly
  even groups and requeue them as a fresh request_batch (sequential by
  default, since a resplit is almost always against the same host that just
  timed out).
* mobile.MobileNucleiScan — there's no tag list to split (it scans a file
  tree, not URLs); the documented lever is first_party scoping. If the
  original run didn't set first_party, requeue once with first_party=true.
  If it already did, deepen first_party_depth by one. Each step trades
  coverage for completion — the original full-tree attempt's partial results
  are still worth keeping, this just gets a cleaner rerun.

Anything else (no splittable tags, unrecognized skill) returns
`splittable: false` with the reason, rather than guessing — the caller
decides the next move.
"""

import json

from state.storage import get_execution_by_id
from tools.request_batch import handle_request_batch
from tools.request_security_action import handle_request

_EXCLUDED_BASE_KEYS = ("target", "arguments", "depends_on")


def _parse_envelope(execution):
    result = execution.get("result")
    if isinstance(result, dict):
        return result
    if isinstance(result, str) and result.strip():
        try:
            parsed = json.loads(result)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _split_evenly(items, n):
    n = max(1, min(n, len(items)))
    groups = [[] for _ in range(n)]
    for i, item in enumerate(items):
        groups[i % n].append(item)
    return [g for g in groups if g]


def handle_resplit_timed_out_shard(args):
    execution_id = args.get("execution_id")
    if not execution_id:
        return {"error": "execution_id is required"}

    execution = get_execution_by_id(execution_id)
    if not execution:
        return {"error": f"No execution found for {execution_id}"}

    findings = _parse_envelope(execution).get("findings") or {}
    if not findings.get("timed_out"):
        return {
            "error": (
                f"Execution {execution_id} is not marked timed_out — nothing to resplit. "
                "Only requeue a shard that actually hit its wall-clock."
            )
        }

    request = execution.get("request") or {}
    skill = request.get("skill", "")
    base_arguments = dict(request.get("arguments") or {})
    target = request.get("target") or execution.get("target")
    base_step = {k: v for k, v in request.items() if k not in _EXCLUDED_BASE_KEYS}
    base_step.setdefault(
        "justification",
        f"Automated resplit of timed-out execution {execution_id} — original scope did "
        "not finish within its wall-clock; narrowing scope to converge.",
    )

    split_factor = int(args.get("split_factor", 2))
    sequential = bool(args.get("sequential", True))

    if skill == "web.NucleiScan":
        tags = base_arguments.get("tags")
        tag_list = [t.strip() for t in str(tags).split(",") if t.strip()] if tags else []
        if len(tag_list) < 2:
            return {
                "splittable": False,
                "execution_id": execution_id,
                "reason": (
                    "No multi-value 'tags' argument to split (single tag, or scoped by "
                    "'templates' path instead). Narrow manually — e.g. raise 'timeout', "
                    "set 'rate_limit', or pick a narrower 'templates' directory."
                ),
            }

        groups = _split_evenly(tag_list, split_factor)
        remaining_arguments = {k: v for k, v in base_arguments.items() if k != "tags"}
        shards = [
            {"label": f"resplit-{i}", "arguments": {"tags": ",".join(group)}}
            for i, group in enumerate(groups, start=1)
        ]

        batch_payload = dict(base_step)
        batch_payload["target"] = target
        batch_payload["arguments"] = remaining_arguments
        batch_payload["shards"] = shards
        batch_payload["sequential"] = sequential

        result = handle_request_batch(batch_payload)
        result["splittable"] = True
        result["strategy"] = "tags_split"
        result["source_execution_id"] = execution_id
        return result

    if skill == "mobile.MobileNucleiScan":
        new_arguments = dict(base_arguments)
        if not base_arguments.get("first_party"):
            new_arguments["first_party"] = True
            strategy = "first_party_scope"
        else:
            depth = int(base_arguments.get("first_party_depth", 2))
            new_arguments["first_party_depth"] = depth + 1
            strategy = "deepen_first_party_depth"

        payload = dict(base_step)
        payload["target"] = target
        payload["arguments"] = new_arguments

        result = handle_request(payload)
        result["splittable"] = True
        result["strategy"] = strategy
        result["source_execution_id"] = execution_id
        return result

    return {
        "splittable": False,
        "execution_id": execution_id,
        "reason": (
            f"No known narrowing strategy for skill {skill!r}. Only web.NucleiScan "
            "(split by tags) and mobile.MobileNucleiScan (first_party scoping) are "
            "automated; resubmit manually with a narrower scope or a longer 'timeout'."
        ),
    }
