import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skills.web import NucleiScan


def test_build_command_includes_sharding_flags(tmp_path):
    skill = NucleiScan(target="http://example.com")
    skill.loot_path = str(tmp_path)
    cmd = skill.build_command(
        target="http://example.com",
        tags="cve,exposure",
        severity="high,critical",
        concurrency=25,
        timeout=600,
    )
    assert "-u http://example.com" in cmd
    assert "-tags cve,exposure" in cmd
    assert "-severity high,critical" in cmd
    assert "-c 25" in cmd
    assert "-jsonl" in cmd
    assert skill._wall_timeout == 600


def test_build_command_requires_a_target(tmp_path):
    skill = NucleiScan(target=None)
    skill.loot_path = str(tmp_path)
    try:
        skill.build_command()
    except ValueError as e:
        assert "target" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_parse_output_reads_jsonl(tmp_path):
    skill = NucleiScan(target="http://example.com")
    skill.loot_path = str(tmp_path)
    skill.build_command(target="http://example.com")
    with open(skill._output_file, "w") as f:
        f.write(
            '{"host":"example.com","template-id":"tech-detect",'
            '"info":{"name":"Tech","severity":"info"},"matched-at":"http://example.com"}\n'
        )
    findings = skill.parse_output("", "", 0)
    assert findings["result_count"] == 1
    assert findings["results"][0]["template_id"] == "tech-detect"
    assert findings["timed_out"] is False


def test_timeout_salvages_partial_results(tmp_path, monkeypatch):
    skill = NucleiScan(target="http://example.com")
    skill.loot_path = str(tmp_path)
    cmd = skill.build_command(target="http://example.com", timeout=5)
    # nuclei streamed one match before the deadline killed it.
    with open(skill._output_file, "w") as f:
        f.write(
            '{"host":"example.com","template-id":"partial",'
            '"info":{"name":"P","severity":"low"},"matched-at":"x"}\n'
        )

    def fake_run(*a, **k):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)

    monkeypatch.setattr(subprocess, "run", fake_run)
    shell = skill.execute_shell(cmd)
    assert shell["exit_code"] == -1
    assert skill._timed_out is True

    findings = skill.parse_output(shell["stdout"], shell["stderr"], shell["exit_code"])
    assert findings["timed_out"] is True
    assert findings["result_count"] == 1  # partial result preserved
    assert any("wall-clock" in e for e in skill._errors)
