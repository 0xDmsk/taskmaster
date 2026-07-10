import uuid

from state.reporting import (
    finding_to_report_dict,
    get_engagement,
    get_finding,
    list_findings,
)
from state.state import create_execution

_REQUIRED_REPORT_FIELDS = (
    "id",
    "title",
    "severity",
    "category",
    "affected",
    "description",
    "impact",
    "proof_of_concept",
    "remediation",
)


def handle_request_reporting_docx(args):
    finding_ids = args.get("finding_ids") or []
    if isinstance(finding_ids, str):
        finding_ids = [finding_ids]
    engagement_id = args.get("engagement_id")
    status = args.get("status")

    if not finding_ids and not engagement_id:
        return {"error": "Provide finding_ids or engagement_id"}

    if finding_ids:
        stored_findings = []
        missing = []
        for finding_id in finding_ids:
            finding = get_finding(finding_id)
            if finding:
                stored_findings.append(finding)
            else:
                missing.append(finding_id)
        if missing:
            return {"error": "Unknown finding_ids", "missing": missing}
    else:
        stored_findings = list_findings(
            engagement_id=engagement_id,
            status=status,
            include_evidence=False,
        )

    if not stored_findings:
        return {"error": "No findings matched the report request"}

    report_findings = [finding_to_report_dict(finding) for finding in stored_findings]
    not_ready = []
    for finding in report_findings:
        missing = [field for field in _REQUIRED_REPORT_FIELDS if not finding.get(field)]
        if missing:
            not_ready.append({"finding_id": finding["id"], "missing": missing})
    if not_ready:
        return {
            "error": "Some findings are not report-ready",
            "not_ready": not_ready,
        }

    engagement = get_engagement(engagement_id) if engagement_id else None
    target = args.get("target")
    if not target:
        if engagement:
            target = engagement.get("slug") or engagement.get("name")
        else:
            target = "taskmaster-reporting"

    report_args = {"findings": report_findings}
    if args.get("template_path"):
        report_args["template_path"] = args["template_path"]
    if args.get("output_dir"):
        report_args["output_dir"] = args["output_dir"]

    request_payload = {
        "agent_role": "reporting",
        "phase": "reporting",
        "target": target,
        "action_type": "report_skill",
        "skill": "reporting.FindingDocxReport",
        "arguments": report_args,
        "justification": (
            "Render a client-facing DOCX report from canonical Taskmaster "
            "reporting findings stored in the database."
        ),
        "expected_output": "JSON envelope with a rendered DOCX artifact path.",
    }

    # Bind the render to an engagement: the explicit arg wins, otherwise inherit
    # it from the findings when they all belong to the same engagement.
    render_engagement_id = engagement_id
    if not render_engagement_id:
        finding_engagements = {
            finding.get("engagement_id")
            for finding in stored_findings
            if finding.get("engagement_id")
        }
        if len(finding_engagements) == 1:
            render_engagement_id = next(iter(finding_engagements))

    execution_id = str(uuid.uuid4())
    create_execution(
        execution_id=execution_id,
        target=target,
        security_phase="reporting",
        request_payload=request_payload,
        created_by="reporting",
        engagement_id=render_engagement_id,
    )

    return {
        "execution_id": execution_id,
        "status": "QUEUED",
        "finding_ids": [finding["finding_id"] for finding in stored_findings],
        "message": (
            "Report render queued from canonical Taskmaster findings. Spawn a "
            "reporting agent unless one is already running, then wait for completion."
        ),
        "recommended_next_steps": [
            "Spawn a reporting agent with spawn_agent agent_type='reporting'",
            "Then call wait_for_completion with this execution_id",
        ],
    }
