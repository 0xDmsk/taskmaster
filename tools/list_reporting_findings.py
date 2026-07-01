from state.reporting import finding_to_report_dict, list_findings


def handle_list_reporting_findings(args):
    findings = list_findings(
        engagement_id=args.get("engagement_id"),
        status=args.get("status"),
        include_evidence=args.get("include_evidence", True),
    )
    return {
        "findings": findings,
        "report_shapes": [finding_to_report_dict(finding) for finding in findings],
        "count": len(findings),
    }
