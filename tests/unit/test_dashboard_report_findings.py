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
from dashboard.webapp import DashboardHandler
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


def test_report_finding_edit_form_still_renders():
    """The finding create/edit form survives the flat-list removal (engagement flow)."""
    _engagement, finding = _seed_report_finding()
    options = get_report_finding_options()

    detail = get_report_finding_detail(finding["finding_id"])
    form_html = render(
        "report_finding_form.html",
        page="engagements",
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
    # Save-as-template action is available on the edit page.
    assert f"/reporting/findings/{finding['finding_id']}/save-as-template" in form_html


def test_findings_flat_route_redirects_to_engagements():
    """The removed flat findings list redirects rather than 404s."""
    handler = object.__new__(DashboardHandler)
    handler.path = "/reporting/findings"
    handler.headers = {}
    calls = []
    handler.send_response = lambda status: calls.append(("status", status))
    handler.send_header = lambda k, v: calls.append(("header", k, v))
    handler.end_headers = lambda: calls.append(("end",))

    DashboardHandler.do_GET(handler)

    assert ("status", 302) in calls
    assert ("header", "Location", "/reporting/engagements") in calls
