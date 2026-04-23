from state.state import get_queued_executions
from targeting import targets_match

def handle_list_queued_executions(args):
    """
    Returns all executions currently in QUEUED status.
    Supports optional 'target' filter.
    """
    target = args.get("target")
    queued = get_queued_executions()

    if target:
        queued = [e for e in queued if targets_match(target, e.get("target"))]

    return {
        "count": len(queued),
        "executions": queued
    }
