"""
Unit tests for the refactored BaseSkill envelope assembly.
"""

import json
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skills.base import BaseSkill

# --- Concrete test skill ---


class EchoSkill(BaseSkill):
    tool = "echo"
    tool_version_command = "echo v1.0.0"

    def build_command(self, **kwargs) -> str:
        msg = kwargs.get("msg", "hello")
        return f"echo {msg}"

    def parse_output(self, stdout, stderr, exit_code) -> dict:
        return {"message": stdout.strip()}


class FailBuildSkill(BaseSkill):
    tool = "false"
    tool_version_command = ""

    def build_command(self, **kwargs) -> str:
        raise ValueError("bad args")

    def parse_output(self, stdout, stderr, exit_code) -> dict:
        return {}


class FailParseSkill(BaseSkill):
    tool = "echo"
    tool_version_command = ""

    def build_command(self, **kwargs) -> str:
        return "echo ok"

    def parse_output(self, stdout, stderr, exit_code) -> dict:
        raise RuntimeError("parse boom")


class PdtmSkill(BaseSkill):
    tool = "httpx"
    auto_install_with_pdtm = True

    def build_command(self, **kwargs) -> str:
        return "httpx -version"

    def parse_output(self, stdout, stderr, exit_code) -> dict:
        return {"message": stdout.strip()}


# --- Tests ---


class TestEnvelopeAssembly:
    def test_success_envelope(self):
        skill = EchoSkill(target="localhost")
        result = skill.run()

        assert result["skill"].endswith("test_base_skill.EchoSkill")
        assert result["target"] == "localhost"
        assert result["status"] == "success"
        assert result["tool"] == "echo"
        assert result["tool_version"] == "v1.0.0"
        assert result["command"] == "echo hello"
        assert result["findings"] == {"message": "hello"}
        assert isinstance(result["artifacts"], list)
        assert isinstance(result["errors"], list)
        assert "started_at" in result
        assert "completed_at" in result

    def test_target_override_via_kwargs(self):
        skill = EchoSkill(target="original")
        result = skill.run(target="override")
        assert result["target"] == "override"

    def test_custom_msg_kwarg(self):
        skill = EchoSkill(target="localhost")
        result = skill.run(msg="world")
        assert result["findings"]["message"] == "world"
        assert result["command"] == "echo world"


class TestErrorHandling:
    def test_build_command_failure(self):
        skill = FailBuildSkill(target="localhost")
        result = skill.run()

        assert result["status"] == "error"
        assert result["command"] == ""
        assert any("build_command failed" in e for e in result["errors"])

    def test_parse_output_failure(self):
        skill = FailParseSkill(target="localhost")
        result = skill.run()

        assert result["status"] == "partial"
        assert result["findings"] == {}
        assert any("parse_output failed" in e for e in result["errors"])


class TestVersionDetection:
    def test_detects_version(self):
        skill = EchoSkill(target="localhost")
        version = skill._detect_tool_version()
        assert version == "v1.0.0"

    def test_empty_version_command(self):
        skill = FailBuildSkill(target="localhost")
        version = skill._detect_tool_version()
        assert version == ""


class TestArtifactTracking:
    def test_save_artifact_tracked(self, tmp_path):
        skill = EchoSkill(target="localhost")
        skill.loot_path = str(tmp_path)

        path = skill.save_artifact("test.txt", "content")
        assert path in skill._artifacts
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "content"

    def test_save_json_tracked(self, tmp_path):
        skill = EchoSkill(target="localhost")
        skill.loot_path = str(tmp_path)

        path = skill.save_json("data", {"key": "value"})
        assert path.endswith(".json")
        assert path in skill._artifacts
        with open(path) as f:
            assert json.load(f) == {"key": "value"}


class TestPdtmBootstrap:
    def test_auto_installs_supported_tool_via_pdtm(self):
        skill = PdtmSkill(target="localhost")

        with patch("skills.base.shutil.which") as mock_which, patch(
            "skills.base.subprocess.run"
        ) as mock_run:
            mock_which.side_effect = [None, "/usr/local/bin/pdtm", "/root/.pdtm/go/bin/httpx"]
            mock_run.side_effect = [
                Mock(returncode=0, stdout="", stderr=""),
                Mock(returncode=0, stdout="httpx v1.0.0\n", stderr=""),
                Mock(returncode=0, stdout="httpx v1.0.0\n", stderr=""),
            ]

            result = skill.run()

        assert result["status"] == "success"
        assert mock_run.call_args_list[0].args[0] == ["pdtm", "-duc", "-nc", "-i", "httpx"]

    def test_returns_clear_error_when_pdtm_install_fails(self):
        skill = PdtmSkill(target="localhost")

        with patch("skills.base.shutil.which") as mock_which, patch(
            "skills.base.subprocess.run"
        ) as mock_run:
            mock_which.side_effect = [None, "/usr/local/bin/pdtm"]
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="boom")

            result = skill.run()

        assert result["status"] == "error"
        assert "PDTM failed to install" in result["errors"][0]
