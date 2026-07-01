import sqlite3

from state.reporting import add_finding_reference, get_finding


def handle_add_reporting_finding_reference(args):
    finding_id = args.get("finding_id")
    url = args.get("url")
    if not finding_id:
        return {"error": "finding_id is required"}
    if not url:
        return {"error": "url is required"}

    if not get_finding(finding_id):
        return {"error": "Finding not found"}

    try:
        reference = add_finding_reference(
            finding_id,
            url,
            label=args.get("label"),
            sort_order=args.get("sort_order"),
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}

    return {"status": "created", "reference": reference}
