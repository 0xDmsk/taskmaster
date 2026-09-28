import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skills.web import StrikeVerify


def _resp(status=200, body="", headers=None):
    return {"status": status, "body": body, "headers": headers or {}}


def test_build_command_requires_a_url(tmp_path):
    skill = StrikeVerify(target=None)
    skill.loot_path = str(tmp_path)
    try:
        skill.build_command()
    except ValueError as e:
        assert "url" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_inject_uses_placeholder_when_present():
    skill = StrikeVerify(target="http://example.com")
    url, data = skill._inject("http://example.com/x?id={{MARKER}}", None, "PAYLOAD", "q")
    assert url == "http://example.com/x?id=PAYLOAD"
    assert data is None


def test_inject_falls_back_to_query_param():
    skill = StrikeVerify(target="http://example.com")
    url, data = skill._inject("http://example.com/x", None, "PAYLOAD", "q")
    assert url == "http://example.com/x?q=PAYLOAD"


def test_inject_blank_strips_placeholder_for_baseline():
    skill = StrikeVerify(target="http://example.com")
    url, _ = skill._inject("http://example.com/x?id={{MARKER}}", None, "", "q", blank=True)
    assert url == "http://example.com/x?id="


def test_inject_blank_leaves_url_untouched_without_placeholder():
    skill = StrikeVerify(target="http://example.com")
    url, _ = skill._inject("http://example.com/x", None, "", "q", blank=True)
    assert url == "http://example.com/x"


def test_confirmed_when_marker_reflected_and_control_is_not(monkeypatch):
    skill = StrikeVerify(target="http://example.com")
    skill.loot_path = "/tmp"

    def fake_request(self, url, method, data, headers, timeout):
        if "TM" in url:
            return _resp(200, "echo: TM-marker")
        if "CT" in url:
            return _resp(200, "no reflection here")
        return _resp(200, "baseline")

    monkeypatch.setattr(StrikeVerify, "_request", fake_request)
    result = skill._run_verification(
        {"url": "http://example.com/x", "marker": "TM-marker", "control": "CT-control"}
    )
    assert result["status"] == "confirmed"
    assert result["marker_reflected"] is True
    assert result["control_reflected"] is False


def test_false_positive_when_both_reflected(monkeypatch):
    skill = StrikeVerify(target="http://example.com")

    def fake_request(self, url, method, data, headers, timeout):
        if "TM" in url:
            return _resp(200, "echo: TM-marker")
        if "CT" in url:
            return _resp(200, "echo: CT-control")
        return _resp(200, "baseline")

    monkeypatch.setattr(StrikeVerify, "_request", fake_request)
    result = skill._run_verification(
        {"url": "http://example.com/x", "marker": "TM-marker", "control": "CT-control"}
    )
    assert result["status"] == "false_positive"


def test_unconfirmed_when_marker_not_reflected(monkeypatch):
    skill = StrikeVerify(target="http://example.com")

    monkeypatch.setattr(
        StrikeVerify,
        "_request",
        lambda self, url, method, data, headers, timeout: _resp(200, "nothing"),
    )
    result = skill._run_verification(
        {"url": "http://example.com/x", "marker": "TM-marker", "control": "CT-control"}
    )
    assert result["status"] == "unconfirmed"


def test_blocked_when_marker_request_errors(monkeypatch):
    skill = StrikeVerify(target="http://example.com")

    monkeypatch.setattr(
        StrikeVerify,
        "_request",
        lambda self, url, method, data, headers, timeout: _resp(0, "conn refused"),
    )
    result = skill._run_verification(
        {"url": "http://example.com/x", "marker": "TM-marker", "control": "CT-control"}
    )
    assert result["status"] == "blocked"


def test_waf_bypass_reapplies_technique_to_control(monkeypatch):
    skill = StrikeVerify(target="http://example.com")
    variants = skill._bypass_variants("TM-marker")
    assert variants, "expected at least one bypass variant for this marker"
    first_technique, first_variant = variants[0]

    call_log = []

    def fake_request(self, url, method, data, headers, timeout):
        call_log.append(url)
        call_index = len(call_log)
        if call_index == 1:
            return _resp(200, "baseline")
        if call_index == 2:
            return _resp(403, "request blocked by mod_security")
        if call_index == 3:
            # first bypass variant gets through and reflects
            return _resp(200, f"echo: {first_variant}")
        return _resp(200, f"echo: {data or url}")  # control request

    monkeypatch.setattr(StrikeVerify, "_request", fake_request)
    result = skill._run_verification(
        {"url": "http://example.com/x", "marker": "TM-marker", "control": "CT-control"}
    )
    assert result["bypass_used"] == first_technique
    assert result["marker_reflected"] is True
    # control was transformed with the same technique, not left as the raw literal
    assert result["control"] == skill._apply_bypass(first_technique, "CT-control")
    assert result["control"] != "CT-control"


def test_parse_output_writes_evidence_artifact_and_strips_it(tmp_path):
    skill = StrikeVerify(target="http://example.com")
    skill.loot_path = str(tmp_path)
    skill._verify_kwargs = {"url": "http://example.com/x"}
    stdout = (
        '{"status": "confirmed", "reason": "r", "marker": "TM1", "control": "CT1", '
        '"marker_reflected": true, "control_reflected": false, "bypass_used": null, '
        '"baseline_status": 200, "marker_status": 200, "control_status": 200, '
        '"evidence": {"url": "http://example.com/x"}}'
    )
    result = skill.parse_output(stdout, "", 0)
    assert result["status"] == "confirmed"
    assert "evidence" not in result
    assert os.path.exists(result["evidence_artifact"])
