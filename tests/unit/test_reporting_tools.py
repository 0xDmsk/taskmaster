import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from server import TOOLS
from tools.create_reporting_engagement import handle_create_reporting_engagement
from tools.create_reporting_finding import handle_create_reporting_finding
from tools.get_reporting_finding import handle_get_reporting_finding
from tools.list_reporting_findings import handle_list_reporting_findings
from tools.request_reporting_docx import handle_request_reporting_docx
from tools.update_reporting_finding import handle_update_reporting_finding
from tools.add_reporting_finding_evidence import handle_add_reporting_finding_evidence
from tools.add_reporting_finding_reference import handle_add_reporting_finding_reference
from state.state import get_execution_state


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


def test_reporting_tools_are_registered():
    assert "create_reporting_engagement" in TOOLS
    assert "create_reporting_finding" in TOOLS
    assert "get_reporting_finding" in TOOLS
    assert "list_reporting_findings" in TOOLS
    assert "request_reporting_docx" in TOOLS
    assert "update_reporting_finding" in TOOLS
    assert "add_reporting_finding_evidence" in TOOLS
    assert "add_reporting_finding_reference" in TOOLS


def test_create_and_fetch_reporting_finding_through_handlers():
    engagement_result = handle_create_reporting_engagement(
        {"name": "Reporting Tool Test", "client_name": "ExampleCo"}
    )
    engagement_id = engagement_result["engagement"]["engagement_id"]

    create_result = handle_create_reporting_finding(
        {
            "engagement_id": engagement_id,
            "title": "Missing authorization on export endpoint",
            "severity": "High",
            "category": "API",
            "status": "confirmed",
            "affected": "GET /api/export",
            "description": "The export endpoint returned another user's data.",
            "impact": "An authenticated user could retrieve records they do not own.",
            "proof_of_concept": "GET /api/export?id=<other-user-id>",
            "remediation": "Authorize the export request against the authenticated user.",
            "references": ["https://cwe.mitre.org/data/definitions/639.html"],
            "evidence": [{"title": "Cross-user export", "body": "HTTP 200 with other user data"}],
        }
    )

    assert create_result["status"] == "created"
    finding_id = create_result["finding"]["finding_id"]
    assert create_result["report_shape"]["id"] == finding_id

    fetched = handle_get_reporting_finding({"finding_id": finding_id})
    assert fetched["finding"]["title"] == "Missing authorization on export endpoint"
    assert fetched["report_shape"]["references"] == [
        "https://cwe.mitre.org/data/definitions/639.html"
    ]

    listed = handle_list_reporting_findings({"engagement_id": engagement_id})
    assert listed["count"] == 1
    assert listed["findings"][0]["finding_id"] == finding_id


def test_create_reporting_finding_validation_error_is_user_facing():
    result = handle_create_reporting_finding(
        {
            "title": "Bad severity",
            "severity": "Severe",
        }
    )

    assert "error" in result
    assert "severity must be one of" in result["error"]


def test_request_reporting_docx_queues_report_skill_from_stored_findings():
    engagement = handle_create_reporting_engagement({"name": "Queued Report Test"})["engagement"]
    finding = handle_create_reporting_finding(
        {
            "engagement_id": engagement["engagement_id"],
            "title": "Verbose errors disclose backend path",
            "severity": "Low",
            "category": "Web",
            "status": "confirmed",
            "affected": "GET /debug/error",
            "description": "The error page disclosed an internal filesystem path.",
            "impact": "The path disclosure gives attackers implementation detail.",
            "proof_of_concept": "GET /debug/error returned /srv/app/current/app.py.",
            "remediation": "Return generic errors and log detailed traces server-side.",
        }
    )["finding"]

    queued = handle_request_reporting_docx({"engagement_id": engagement["engagement_id"]})

    assert queued["status"] == "QUEUED"
    assert queued["finding_ids"] == [finding["finding_id"]]

    execution = get_execution_state(queued["execution_id"])
    request = execution["request"]
    assert request["action_type"] == "report_skill"
    assert request["skill"] == "reporting.FindingDocxReport"
    assert request["arguments"]["findings"][0]["id"] == finding["finding_id"]
    assert request["arguments"]["findings"][0]["title"] == ("Verbose errors disclose backend path")


def test_update_reporting_finding_and_attach_evidence_reference():
    finding = handle_create_reporting_finding(
        {
            "title": "Draft finding",
            "severity": "Info",
            "category": "Web",
            "status": "draft",
        }
    )["finding"]

    updated = handle_update_reporting_finding(
        {
            "finding_id": finding["finding_id"],
            "title": "Reviewed finding",
            "severity": "Medium",
            "category": "API",
            "status": "needs_review",
            "affected": "POST /api/review",
            "description": "The reviewed behavior needs a second tester.",
            "impact": "The issue may expose another user's record.",
            "proof_of_concept": "Replay POST /api/review with another ID.",
            "remediation": "Bind the request to the authenticated user.",
            "updated_by": "dashboard",
        }
    )

    assert updated["status"] == "updated"
    assert updated["finding"]["severity"] == "Medium"
    assert updated["finding"]["updated_by"] == "dashboard"

    evidence = handle_add_reporting_finding_evidence(
        {
            "finding_id": finding["finding_id"],
            "kind": "request",
            "title": "Replay request",
            "body": "POST /api/review",
            "artifact_path": "/loot/replay.txt",
        }
    )
    reference = handle_add_reporting_finding_reference(
        {
            "finding_id": finding["finding_id"],
            "label": "CWE-639",
            "url": "https://cwe.mitre.org/data/definitions/639.html",
        }
    )

    assert evidence["status"] == "created"
    assert reference["status"] == "created"

    fetched = handle_get_reporting_finding({"finding_id": finding["finding_id"]})
    assert fetched["finding"]["evidence"][0]["artifact_path"] == "/loot/replay.txt"
    assert fetched["finding"]["references"][0]["label"] == "CWE-639"


def test_request_reporting_docx_rejects_incomplete_findings():
    finding = handle_create_reporting_finding(
        {
            "title": "Incomplete report finding",
            "severity": "Info",
            "category": "Web",
            "status": "confirmed",
        }
    )["finding"]

    result = handle_request_reporting_docx({"finding_ids": finding["finding_id"]})

    assert result["error"] == "Some findings are not report-ready"
    assert result["not_ready"][0]["finding_id"] == finding["finding_id"]
    assert "affected" in result["not_ready"][0]["missing"]
