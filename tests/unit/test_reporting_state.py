import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from state.reporting import (
    add_finding_evidence,
    add_finding_reference,
    create_asset,
    create_engagement,
    create_finding,
    finding_to_report_dict,
    get_finding,
    list_assets,
    list_engagements,
    list_findings,
    normalize_report_markdown,
    update_finding,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


class TestEngagements:
    def test_create_engagement_generates_unique_slug(self):
        first = create_engagement("Private Dining Assessment", client_name="ExampleCo")
        second = create_engagement("Private Dining Assessment")

        assert first["name"] == "Private Dining Assessment"
        assert first["client_name"] == "ExampleCo"
        assert first["slug"] == "private-dining-assessment"
        assert second["slug"] == "private-dining-assessment-2"

        engagements = list_engagements()
        assert {e["engagement_id"] for e in engagements} == {
            first["engagement_id"],
            second["engagement_id"],
        }

    def test_create_asset_attaches_to_engagement(self):
        engagement = create_engagement("External Test")

        asset = create_asset(
            "https://app.example.test",
            engagement_id=engagement["engagement_id"],
            kind="url",
            description="Primary application",
        )

        assert asset["kind"] == "url"
        assert asset["engagement_id"] == engagement["engagement_id"]
        assert list_assets(engagement["engagement_id"])[0]["value"] == "https://app.example.test"


class TestFindings:
    def test_create_finding_with_evidence_and_references(self):
        engagement = create_engagement("API Test")

        finding = create_finding(
            engagement_id=engagement["engagement_id"],
            title="Caller-controlled price accepted by checkout API",
            severity="High",
            category="API",
            status="confirmed",
            affected_assets=[
                "POST https://api.example.test/cart/total",
                "POST https://api.example.test/checkout",
            ],
            description="The checkout flow accepted a client-supplied unit price.",
            impact="A user could reduce the total charged for an order.",
            proof_of_concept="Send unitPrice=1 in the cart payload and complete checkout.",
            remediation="Recalculate all prices server-side from trusted product IDs.",
            cvss={"score": "7.5", "vector": "AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N"},
            references=[
                "https://cwe.mitre.org/data/definitions/345.html",
                {"label": "OWASP API4", "url": "https://owasp.org/API-Security/"},
            ],
            evidence=[
                {
                    "kind": "request",
                    "title": "Modified cart request",
                    "body": "POST /cart/total with unitPrice=1",
                    "artifact_path": "/loot/cart-total.txt",
                }
            ],
            created_by="tester",
        )

        assert finding["engagement_id"] == engagement["engagement_id"]
        assert finding["severity"] == "High"
        assert finding["status"] == "confirmed"
        assert finding["affected"] == (
            "POST https://api.example.test/cart/total\n" "POST https://api.example.test/checkout"
        )
        assert finding["cvss_score"] == "7.5"
        assert len(finding["references"]) == 2
        assert finding["references"][1]["label"] == "OWASP API4"
        assert len(finding["evidence"]) == 1
        assert finding["evidence"][0]["artifact_path"] == "/loot/cart-total.txt"

        listed = list_findings(engagement_id=engagement["engagement_id"])
        assert [item["finding_id"] for item in listed] == [finding["finding_id"]]

    def test_update_finding_scalar_fields_without_replacing_evidence(self):
        finding = create_finding(title="Draft issue", severity="Info")
        add_finding_reference(finding["finding_id"], "https://example.test/ref")
        add_finding_evidence(
            finding["finding_id"],
            title="Raw response",
            body="HTTP/1.1 200 OK",
        )

        updated = update_finding(
            finding["finding_id"],
            severity="Medium",
            status="needs_review",
            impact="This needs manual review.",
            updated_by="reviewer",
        )

        assert updated["severity"] == "Medium"
        assert updated["status"] == "needs_review"
        assert updated["updated_by"] == "reviewer"
        assert len(updated["references"]) == 1
        assert len(updated["evidence"]) == 1

    def test_validation_rejects_unknown_severity(self):
        with pytest.raises(ValueError, match="severity must be one of"):
            create_finding(title="Bad severity", severity="Important")

    def test_finding_to_report_dict_matches_renderer_contract(self):
        finding = create_finding(
            title="Stored XSS in search",
            severity="Medium",
            category="Web",
            affected="https://example.test/search?q=",
            description="The search page reflects q into HTML without encoding.",
            impact="A crafted link can run JavaScript in a user's browser.",
            proof_of_concept="GET /search?q=<script>alert(1)</script>",
            remediation="HTML-encode q before rendering it.",
            cvss_score="6.1",
            cvss_vector="AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
            references=[
                {"label": "CWE-79", "url": "https://cwe.mitre.org/data/definitions/79.html"}
            ],
        )

        stored = get_finding(finding["finding_id"])
        report_dict = finding_to_report_dict(stored)

        assert report_dict == {
            "id": finding["finding_id"],
            "title": "Stored XSS in search",
            "severity": "Medium",
            "category": "Web",
            "cvss": {
                "score": "6.1",
                "vector": "AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
            },
            "affected": "https://example.test/search?q=",
            "description": "The search page reflects q into HTML without encoding.",
            "impact": "A crafted link can run JavaScript in a user's browser.",
            "proof_of_concept": "GET /search?q=<script>alert(1)</script>",
            "remediation": "HTML-encode q before rendering it.",
            "references": [
                "CWE-79 - https://cwe.mitre.org/data/definitions/79.html",
            ],
        }


class TestReportMarkdownNormalization:
    def test_literal_bullet_glyphs_become_list_markers(self):
        text = "Static source trace:\n\n\u2022 first item\n\u2022 second item"
        assert normalize_report_markdown(text) == (
            "Static source trace:\n\n- first item\n- second item"
        )

    def test_bullet_with_no_following_space(self):
        text = "trace:\n\u2022bhi-eapp/foo.xml:12 does a thing"
        assert normalize_report_markdown(text) == "trace:\n- bhi-eapp/foo.xml:12 does a thing"

    def test_indented_and_mixed_glyphs_preserved_as_lists(self):
        text = "head:\n\u2022 top\n  \u2043 nested-ish\n\u2219 third"
        assert normalize_report_markdown(text) == "head:\n- top\n  - nested-ish\n- third"

    def test_escaped_ordered_marker_is_unescaped(self):
        text = "steps:\n1\\. do this\n2\\. then that"
        assert normalize_report_markdown(text) == "steps:\n1. do this\n2. then that"

    def test_single_line_text_is_left_untouched(self):
        # The renderer treats a single-line field as a plain paragraph, so rewriting
        # a lone "• x" to "- x" would only yield a literal dash. Guard on newlines.
        assert normalize_report_markdown("\u2022 lone bullet") == "\u2022 lone bullet"

    def test_midline_glyph_and_real_lists_are_untouched(self):
        text = "a \u2022 b dot in prose\n- already a list\n1. already ordered"
        assert normalize_report_markdown(text) == text

    def test_is_idempotent(self):
        text = "t:\n\u2022 one\n\u2022 two"
        once = normalize_report_markdown(text)
        assert normalize_report_markdown(once) == once

    def test_empty_text_is_safe(self):
        assert normalize_report_markdown("") == ""

    def test_finding_to_report_dict_normalizes_body_fields(self):
        finding = create_finding(
            title="Path traversal in file handler",
            severity="High",
            category="Web",
            proof_of_concept="Static source trace:\n\n\u2022 reads path\n\u2022 writes path",
        )
        report_dict = finding_to_report_dict(get_finding(finding["finding_id"]))
        assert report_dict["proof_of_concept"] == (
            "Static source trace:\n\n- reads path\n- writes path"
        )
        # Stored text is untouched; only the render shape is normalized.
        assert get_finding(finding["finding_id"])["proof_of_concept"] == (
            "Static source trace:\n\n\u2022 reads path\n\u2022 writes path"
        )
