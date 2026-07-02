import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dashboard import render
from dashboard.api import (
    get_report_finding_detail,
    get_report_finding_options,
    get_report_findings,
)
from server import TaskmasterHTTPHandler
from state.reporting import create_engagement, create_finding


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


def _seed_report_finding():
    engagement = create_engagement("ExampleCo Web Assessment", client_name="ExampleCo")
    finding = create_finding(
        engagement_id=engagement["engagement_id"],
        title="Missing authorization on export endpoint",
        severity="High",
        category="API",
        status="confirmed",
        affected="GET /api/export",
        description="The export endpoint returned another user's data.",
        impact="An authenticated user could retrieve records they do not own.",
        proof_of_concept="GET /api/export?id=<other-user-id>",
        remediation="Authorize each export request against the authenticated user.",
        references=[{"label": "CWE-639", "url": "https://cwe.mitre.org/data/definitions/639.html"}],
        evidence=[{"title": "Replay response", "artifact_path": "/loot/export-response.txt"}],
    )
    return engagement, finding


def test_report_findings_api_filters_and_enriches_rows():
    engagement, finding = _seed_report_finding()

    rows = get_report_findings(
        engagement_id=engagement["engagement_id"],
        status="confirmed",
        severity="High",
        query="export",
    )

    assert len(rows) == 1
    assert rows[0]["finding_id"] == finding["finding_id"]
    assert rows[0]["engagement"]["name"] == "ExampleCo Web Assessment"
    assert rows[0]["evidence_count"] == 1
    assert rows[0]["reference_count"] == 1
    assert get_report_findings(query="does-not-match") == []


def test_report_findings_templates_render_list_and_edit_form():
    engagement, finding = _seed_report_finding()
    options = get_report_finding_options()
    rows = get_report_findings(engagement_id=engagement["engagement_id"])

    list_html = render(
        "report_findings.html",
        page="report_findings",
        stats={},
        findings=rows,
        options=options,
        filters={
            "engagement_id": engagement["engagement_id"],
            "status": "",
            "severity": "",
            "q": "",
        },
        message=None,
        error=None,
    )

    assert "Report Findings" in list_html
    assert "Missing authorization on export endpoint" in list_html
    assert "/reporting/findings/new" in list_html
    assert "Queue DOCX" in list_html
    assert '<div id="report-findings-list">' in list_html
    assert '<div id="report-findings-list"\n     hx-get=' not in list_html
    assert 'hx-target="#report-findings-list"' in list_html

    detail = get_report_finding_detail(finding["finding_id"])
    form_html = render(
        "report_finding_form.html",
        page="report_findings",
        stats={},
        mode="edit",
        finding=detail,
        options=options,
        message=None,
        error=None,
    )

    assert "Edit Report Finding" in form_html
    assert "Replay response" in form_html
    assert "CWE-639" in form_html
    assert f"/reporting/findings/{finding['finding_id']}/evidence" in form_html


def test_report_findings_page_route_renders_query_filter():
    engagement, _finding = _seed_report_finding()
    handler = object.__new__(TaskmasterHTTPHandler)
    handler.path = (
        "/reporting/findings?"
        f"engagement_id={engagement['engagement_id']}&status=confirmed&q=export"
    )
    handler.headers = {}
    response = {}

    handler._send_html = lambda status, html: response.update({"status": status, "html": html})

    TaskmasterHTTPHandler.do_GET(handler)

    assert response["status"] == 200
    assert "Report Findings" in response["html"]
    assert "Missing authorization on export endpoint" in response["html"]
