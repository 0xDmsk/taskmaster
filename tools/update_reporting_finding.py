import sqlite3

from state.reporting import finding_to_report_dict, update_finding

_ALLOWED_FIELDS = {
    "engagement_id",
    "title",
    "severity",
    "category",
    "status",
    "affected",
    "description",
    "impact",
    "proof_of_concept",
    "remediation",
    "cvss_score",
    "cvss_vector",
    "source_execution_id",
}


def handle_update_reporting_finding(args):
    finding_id = args.get("finding_id")
    if not finding_id:
        return {"error": "finding_id is required"}

    updates = {field: args[field] for field in _ALLOWED_FIELDS if field in args}

    try:
        finding = update_finding(
            finding_id,
            updated_by=args.get("updated_by", "system"),
            **updates,
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}

    if not finding:
        return {"error": "Finding not found"}

    return {
        "status": "updated",
        "finding": finding,
        "report_shape": finding_to_report_dict(finding),
    }
