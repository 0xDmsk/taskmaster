import sqlite3

from state.reporting import finding_to_report_dict, get_finding, update_finding
from state.surface import link_finding_surface, resolve_surface_refs

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

    # surface_refs adds 'affects' links; it never removes existing ones.
    surface_refs = args.get("surface_refs") or []
    if surface_refs:
        current = get_finding(finding_id)
        if not current:
            return {"error": "Finding not found"}
        engagement_id = updates.get("engagement_id") or current.get("engagement_id")
        if not engagement_id:
            return {"error": "surface_refs requires the finding to belong to an engagement"}
        try:
            resolve_surface_refs(engagement_id, surface_refs)
        except ValueError as exc:
            return {"error": str(exc)}

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

    result = {
        "status": "updated",
        "finding": finding,
        "report_shape": finding_to_report_dict(finding),
    }
    if surface_refs:
        result["surface_refs"] = link_finding_surface(
            finding_id, finding["engagement_id"], surface_refs
        )
    return result
