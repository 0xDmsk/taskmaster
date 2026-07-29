"""Tests for the dashboard's table-driven Router (dashboard/webapp.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

from dashboard.webapp import ROUTER


@pytest.mark.parametrize(
    "method,path,expected_handler,expected_cap",
    [
        ("GET", "/overview", "page_overview", {}),
        ("GET", "/executions", "page_executions", {}),
        ("GET", "/targets", "page_targets", {}),
        ("GET", "/agents", "page_agents", {}),
        ("GET", "/observations", "page_observations", {}),
        ("GET", "/findings", "redirect_observations", {}),
        ("GET", "/reporting/engagements", "page_engagements", {}),
        ("GET", "/reporting/findings/new", "page_report_finding_new", {}),
        ("GET", "/api/stats", "api_stats", {}),
        ("GET", "/api/executions", "api_executions", {}),
        ("GET", "/api/agents", "api_agents", {}),
        ("GET", "/api/agents/history", "api_agents_history", {}),
        ("GET", "/api/observations", "api_observations", {}),
        ("GET", "/api/findings", "api_observations", {}),
        ("GET", "/api/reporting/templates", "api_finding_templates", {}),
        ("GET", "/reporting/templates", "page_finding_templates", {}),
        ("GET", "/reporting/templates/new", "page_finding_template_new", {}),
        ("GET", "/reporting/findings", "redirect_engagements", {}),
        ("GET", "/static/style.css", "serve_static", {"rest": "style.css"}),
        ("GET", "/reporting/download", "get_download", {}),
        # Path-parameterized GET routes.
        (
            "GET",
            "/api/executions/abc-123/detail",
            "api_execution_detail",
            {"eid": "abc-123"},
        ),
        ("GET", "/api/executions/abc-123", "api_execution", {"eid": "abc-123"}),
        ("GET", "/api/targets/detail", "api_target_detail", {}),
        ("GET", "/api/agents/kali-x/detail", "api_agent_detail", {"executor_id": "kali-x"}),
        (
            "GET",
            "/reporting/engagements/eng-1",
            "page_engagement_workspace",
            {"engagement_id": "eng-1"},
        ),
        (
            "GET",
            "/reporting/findings/f-1/edit",
            "page_report_finding_edit",
            {"finding_id": "f-1"},
        ),
        (
            "GET",
            "/reporting/templates/tpl-1/edit",
            "page_finding_template_edit",
            {"template_id": "tpl-1"},
        ),
        (
            "GET",
            "/reporting/threat-models/tm-9/export",
            "get_threat_model_export",
            {"tm_id": "tm-9"},
        ),
        (
            "GET",
            "/api/reporting/engagements/eng-1/findings",
            "api_engagement_findings",
            {"engagement_id": "eng-1"},
        ),
        # POST routes.
        ("POST", "/reporting/engagements", "post_create_engagement", {}),
        ("POST", "/reporting/findings", "post_create_finding", {}),
        ("POST", "/reporting/reports/docx", "post_request_docx", {}),
        (
            "POST",
            "/reporting/engagements/eng-1/assets",
            "post_add_asset",
            {"engagement_id": "eng-1"},
        ),
        (
            "POST",
            "/reporting/engagements/eng-1/assets/asset-2/delete",
            "post_delete_asset",
            {"engagement_id": "eng-1", "asset_id": "asset-2"},
        ),
        (
            "POST",
            "/reporting/findings/f-1/status",
            "post_finding_status",
            {"finding_id": "f-1"},
        ),
        (
            "POST",
            "/reporting/findings/f-1/evidence",
            "post_finding_evidence",
            {"finding_id": "f-1"},
        ),
        (
            "POST",
            "/reporting/findings/f-1/references",
            "post_finding_reference",
            {"finding_id": "f-1"},
        ),
        (
            "POST",
            "/reporting/findings/f-1/save-as-template",
            "post_finding_save_as_template",
            {"finding_id": "f-1"},
        ),
        ("POST", "/reporting/findings/f-1", "post_update_finding", {"finding_id": "f-1"}),
        ("POST", "/reporting/templates", "post_create_template", {}),
        (
            "POST",
            "/reporting/templates/tpl-1/delete",
            "post_delete_template",
            {"template_id": "tpl-1"},
        ),
        ("POST", "/reporting/templates/tpl-1/use", "post_use_template", {"template_id": "tpl-1"}),
        ("POST", "/reporting/templates/tpl-1", "post_update_template", {"template_id": "tpl-1"}),
        (
            "POST",
            "/executions/exec-1/engagement",
            "post_execution_engagement",
            {"execution_id": "exec-1"},
        ),
    ],
)
def test_router_matches_expected_handler(method, path, expected_handler, expected_cap):
    handler, cap = ROUTER.match(method, path)
    assert handler == expected_handler
    assert cap == expected_cap


def test_router_specific_before_generic_for_findings():
    """/reporting/findings/new must not be captured by the /<id>/edit or update routes."""
    handler, cap = ROUTER.match("GET", "/reporting/findings/new")
    assert handler == "page_report_finding_new"
    assert cap == {}


def test_router_returns_none_for_unknown_path():
    assert ROUTER.match("GET", "/nope") == (None, None)


def test_router_is_method_scoped():
    # A GET-only path should not match under POST.
    assert ROUTER.match("POST", "/executions") == (None, None)
    # A POST-only path should not match under GET.
    assert ROUTER.match("GET", "/reporting/reports/docx") == (None, None)
