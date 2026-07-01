import sqlite3

from state.reporting import add_finding_evidence, get_finding


def handle_add_reporting_finding_evidence(args):
    finding_id = args.get("finding_id")
    if not finding_id:
        return {"error": "finding_id is required"}

    if not get_finding(finding_id):
        return {"error": "Finding not found"}

    try:
        evidence = add_finding_evidence(
            finding_id,
            kind=args.get("kind", "note"),
            title=args.get("title"),
            body=args.get("body"),
            artifact_path=args.get("artifact_path"),
            url=args.get("url"),
            source_execution_id=args.get("source_execution_id"),
            created_by=args.get("created_by", "system"),
            sort_order=args.get("sort_order"),
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}

    return {"status": "created", "evidence": evidence}
