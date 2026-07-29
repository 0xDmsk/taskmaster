"""Tests for the finding-template library and the pwndoc import mapping."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from state.reporting import (
    create_finding,
    create_finding_template,
    delete_finding_template,
    finding_to_template_payload,
    get_finding,
    get_finding_template,
    list_finding_templates,
    template_to_finding_payload,
    update_finding_template,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


def test_create_and_get_template_normalizes_refs_and_category():
    tpl = create_finding_template(
        title="Reflected XSS",
        severity="High",
        category="not-a-real-category",  # coerced to Other
        description="User input reflected unescaped.",
        impact="Session theft.",
        remediation="Contextually encode output.",
        references=["https://owasp.org/xss", {"label": "CWE", "url": "https://cwe.mitre.org/79"}],
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N",
    )
    fetched = get_finding_template(tpl["template_id"])
    assert fetched["title"] == "Reflected XSS"
    assert fetched["severity"] == "High"
    assert fetched["category"] == "Other"  # coerced, not rejected
    assert fetched["references"] == [
        {"label": None, "url": "https://owasp.org/xss"},
        {"label": "CWE", "url": "https://cwe.mitre.org/79"},
    ]


def test_create_template_requires_title():
    with pytest.raises(ValueError):
        create_finding_template(title="   ")


def test_create_template_rejects_bad_severity():
    with pytest.raises(ValueError):
        create_finding_template(title="X", severity="Spicy")


def test_list_filters_by_severity_category_and_query():
    create_finding_template(title="SQL Injection", severity="High", category="Web",
                            description="tautology login bypass")
    create_finding_template(title="Verbose errors", severity="Low", category="Web",
                            description="stack traces leaked")
    create_finding_template(title="Open S3 bucket", severity="High", category="Cloud-AWS")

    assert len(list_finding_templates()) == 3
    assert len(list_finding_templates(severity="High")) == 2
    assert len(list_finding_templates(category="Web")) == 2
    hits = list_finding_templates(query="tautology")
    assert len(hits) == 1 and hits[0]["title"] == "SQL Injection"


def test_update_and_delete_template():
    tpl = create_finding_template(title="Missing headers", severity="Info")
    updated = update_finding_template(
        tpl["template_id"], severity="Low", remediation="Add CSP.",
        references=["https://example.com/csp"], updated_by="tester",
    )
    assert updated["severity"] == "Low"
    assert updated["remediation"] == "Add CSP."
    assert updated["references"] == [{"label": None, "url": "https://example.com/csp"}]
    assert delete_finding_template(tpl["template_id"]) is True
    assert get_finding_template(tpl["template_id"]) is None


def test_instantiate_template_into_finding_copies_content():
    tpl = create_finding_template(
        title="IDOR on export", severity="High", category="API",
        description="Returns other users' data.", impact="Data exposure.",
        remediation="Authorize per-user.", references=["https://cwe.mitre.org/639"],
    )
    payload = template_to_finding_payload(tpl)
    # Template carries no instance-specific fields.
    assert "engagement_id" not in payload
    assert "status" not in payload
    finding = create_finding(engagement_id=None, affected="GET /export", **payload)

    stored = get_finding(finding["finding_id"])
    assert stored["title"] == "IDOR on export"
    assert stored["severity"] == "High"
    assert stored["category"] == "API"
    assert stored["remediation"] == "Authorize per-user."
    assert stored["affected"] == "GET /export"  # instance-specific, supplied by caller
    assert [r["url"] for r in stored["references"]] == ["https://cwe.mitre.org/639"]


def test_save_finding_as_template_drops_instance_fields():
    finding = create_finding(
        title="Weak TLS on api.example.com", severity="Medium", category="Infrastructure",
        affected="api.example.com:443", description="TLS 1.0 enabled.",
        remediation="Disable legacy TLS.", status="confirmed",
        references=[{"label": "RFC", "url": "https://www.rfc-editor.org/rfc/rfc8996"}],
    )
    payload = finding_to_template_payload(get_finding(finding["finding_id"]))
    assert "affected" not in payload
    assert "status" not in payload
    assert "engagement_id" not in payload

    tpl = create_finding_template(source="finding", **payload)
    stored = get_finding_template(tpl["template_id"])
    assert stored["title"] == "Weak TLS on api.example.com"
    assert stored["source"] == "finding"
    assert stored["references"] == [
        {"label": "RFC", "url": "https://www.rfc-editor.org/rfc/rfc8996"}
    ]


def test_pwndoc_html_to_markdown_mapping():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts")))
    from import_pwndoc_templates import clean_title, html_to_markdown, map_vulnerability

    assert clean_title("BHI-OFFSEC-25.05.F01 Insecure Cookies") == "Insecure Cookies"

    md = html_to_markdown(
        "<p>Intro para.</p><ul><li><p>First <strong>bold</strong> item</p></li>"
        "<li><p>Second item</p></li></ul>"
    )
    assert "Intro para." in md
    assert "- First **bold** item" in md
    assert "- Second item" in md
    # A bullet must not be left dangling before its wrapped-<p> text.
    assert "- \n" not in md

    vuln = {
        "cvssv3": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "category": "Web",
        "details": [
            {
                "locale": "en",
                "title": "BHI-OFFSEC-XX.XX.FXX Information Disclosure",
                "description": "<p>Server banner leaked.</p>",
                "observation": "<p>Aids fingerprinting.</p>",
                "remediation": "<p>Suppress the header.</p>",
                "references": ["https://owasp.org/x", "not-a-url"],
            }
        ],
    }
    payload = map_vulnerability(vuln)
    assert payload["title"] == "Information Disclosure"
    assert payload["category"] == "Web"
    assert payload["severity"] == "Info"  # pwndoc templates carry no severity
    assert payload["impact"] == "Aids fingerprinting."
    assert payload["cvss_vector"].startswith("CVSS:3.1")
    assert payload["references"] == ["https://owasp.org/x"]  # non-URL dropped
