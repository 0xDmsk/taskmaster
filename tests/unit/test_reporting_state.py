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
