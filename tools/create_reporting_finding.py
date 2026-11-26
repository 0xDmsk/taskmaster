import sqlite3

from state.reporting import create_finding, finding_to_report_dict
from state.surface import link_finding_surface, resolve_surface_refs


def handle_create_reporting_finding(args):
    title = args.get("title")
    if not title:
        return {"error": "title is required"}

    surface_refs = args.get("surface_refs") or []
    if surface_refs:
        if not args.get("engagement_id"):
            return {"error": "surface_refs requires engagement_id"}
        # Validate before creating, so a mistyped EP-n doesn't leave a finding behind.
        try:
            resolve_surface_refs(args["engagement_id"], surface_refs)
        except ValueError as exc:
            return {"error": str(exc)}

    try:
        finding = create_finding(
            title=title,
            engagement_id=args.get("engagement_id"),
            finding_id=args.get("finding_id"),
            severity=args.get("severity", "Info"),
            category=args.get("category"),
            status=args.get("status", "draft"),
            affected=args.get("affected"),
            affected_assets=args.get("affected_assets"),
            description=args.get("description", ""),
            impact=args.get("impact", ""),
            proof_of_concept=args.get("proof_of_concept", ""),
            remediation=args.get("remediation", ""),
            cvss=args.get("cvss"),
            cvss_score=args.get("cvss_score"),
            cvss_vector=args.get("cvss_vector"),
            references=args.get("references"),
            evidence=args.get("evidence"),
            source_execution_id=args.get("source_execution_id"),
            created_by=args.get("created_by", "system"),
        )
    except (sqlite3.IntegrityError, ValueError) as exc:
        return {"error": str(exc)}

    result = {
        "status": "created",
        "finding": finding,
        "report_shape": finding_to_report_dict(finding),
    }
    if surface_refs:
        result["surface_refs"] = link_finding_surface(
            finding["finding_id"], args["engagement_id"], surface_refs
        )
    return result
