import sqlite3

from state.reporting import create_finding, finding_to_report_dict


def handle_create_reporting_finding(args):
    title = args.get("title")
    if not title:
        return {"error": "title is required"}

    try:
        finding = create_finding(
            title=title,
            engagement_id=args.get("engagement_id"),
            finding_id=args.get("finding_id"),
            severity=args.get("severity", "Info"),
            category=args.get("category", "General"),
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

    return {
        "status": "created",
        "finding": finding,
        "report_shape": finding_to_report_dict(finding),
    }
