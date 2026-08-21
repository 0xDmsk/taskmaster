"""aggregate_executions — merge the results of a fan of executions into one view.

`request_batch` fans one skill over many shards; each shard writes its own
envelope. This read-only tool pulls those envelopes back and merges their
`findings` into a single structure so the orchestrator sees the whole scan at
once instead of N separate results:

* list-valued findings (e.g. `results`, `subdomains`, `secret_matches`,
  `endpoints`) are concatenated and de-duplicated, with a recomputed `<key>_count`;
* numeric findings are summed;
* boolean findings (e.g. `timed_out`) are OR-ed — so any shard that timed out
  makes the aggregate `timed_out`;
* scalar/string findings collapse to the single value, or a sorted list if the
  shards disagree.

It also reports per-shard status and an `overall_status` that is honest about
completeness: `incomplete` if any shard failed/cancelled/missing, `partial` if
any shard timed out, `complete` only when every shard COMPLETED cleanly. This is
purely additive — it does not modify the executions.
"""

import json

from state.storage import get_execution_by_id

_TERMINAL_OK = "COMPLETED"
_BAD_STATES = {"FAILED", "CANCELLED"}


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


def _dedup(items):
    seen = set()
    out = []
    for item in items:
        key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else repr(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def handle_aggregate_executions(args):
    ids = args.get("execution_ids")
    if not isinstance(ids, list) or not ids:
        return {"error": "Provide a non-empty 'execution_ids' list."}

    shards = []
    lists = {}
    numbers = {}
    booleans = {}
    scalars = {}
    artifacts = []
    errors = []
    missing = []
    any_bad = False
    any_timed_out = False
    all_completed = True

    for eid in ids:
        execution = get_execution_by_id(eid)
        if not execution:
            missing.append(eid)
            all_completed = False
            continue

        env = _parse_envelope(execution)
        findings = env.get("findings") or {}
        status = execution.get("status")
        timed_out = bool(findings.get("timed_out"))
        any_timed_out = any_timed_out or timed_out
        if status in _BAD_STATES:
            any_bad = True
        if status != _TERMINAL_OK:
            all_completed = False

        shards.append(
            {
                "execution_id": eid,
                "target": execution.get("target"),
                "skill": env.get("skill"),
                "status": status,
                "timed_out": timed_out,
            }
        )
        artifacts.extend(env.get("artifacts") or [])
        for err in env.get("errors") or []:
            errors.append(f"[{eid}] {err}")

        for key, value in findings.items():
            if isinstance(value, list):
                lists.setdefault(key, []).extend(value)
            elif isinstance(value, bool):
                booleans[key] = booleans.get(key, False) or value
            elif isinstance(value, (int, float)):
                # Skip count-like numbers: summing them double-counts once the
                # underlying lists are de-duplicated. Merged lists get their own
                # recomputed <key>_count below. Genuine numeric metrics
                # (e.g. files_scanned) still sum.
                if "count" in key.lower():
                    continue
                numbers[key] = numbers.get(key, 0) + value
            elif value is not None:
                scalars.setdefault(key, set()).add(value if isinstance(value, str) else repr(value))

    # Assemble merged findings. Deduped lists win over any summed *_count so the
    # count always matches the merged list length.
    merged = {}
    for key, values in lists.items():
        deduped = _dedup(values)
        merged[key] = deduped
        merged[f"{key}_count"] = len(deduped)
    for key, total in numbers.items():
        merged.setdefault(key, total)
    for key, value in booleans.items():
        merged[key] = value
    for key, distinct in scalars.items():
        merged[key] = next(iter(distinct)) if len(distinct) == 1 else sorted(distinct)

    if missing or any_bad:
        overall = "incomplete"
    elif not all_completed:
        overall = "in_progress"
    elif any_timed_out:
        overall = "partial"
    else:
        overall = "complete"

    return {
        "overall_status": overall,
        "any_timed_out": any_timed_out,
        "shard_count": len(shards),
        "missing_execution_ids": missing,
        "shards": shards,
        "findings": merged,
        "artifacts": _dedup(artifacts),
        "errors": errors,
        "note": (
            "Merged view of a fan of executions: list findings are deduped, numbers "
            "summed, booleans OR-ed. overall_status is 'partial' if any shard timed "
            "out and 'incomplete' if any failed/missing — treat those as coverage "
            "gaps, not a clean result."
        ),
    }
