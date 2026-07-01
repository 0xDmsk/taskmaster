from state.reporting import finding_to_report_dict, get_finding


def handle_get_reporting_finding(args):
    finding_id = args.get("finding_id")
    if not finding_id:
        return {"error": "finding_id is required"}

    finding = get_finding(finding_id)
    if not finding:
        return {"error": "Finding not found"}

    return {
        "finding": finding,
        "report_shape": finding_to_report_dict(finding),
    }
