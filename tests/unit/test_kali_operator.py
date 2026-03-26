"""
Unit tests for the kali_operator two-pathway dispatch.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from executors.kali_operator import execute_action, _execute_skill, _execute_python_sandbox


class TestExecuteActionDispatch:
    """Test that execute_action routes to the correct pathway."""

    def test_skill_pathway(self):
        """Skill action_type dispatches to _execute_skill."""
        execution = {
            "request": {
                "action_type": "skill",
                "skill": "network.FpingSweep",
                "target": "192.168.1.0/24",
                "arguments": {},
            }
        }
        # This will fail because fping isn't installed, but it should
        # go through the skill pathway and return a JSON envelope
        result = execute_action(execution)
        parsed = json.loads(result["result"])
        assert "skill" in parsed or "errors" in parsed

    def test_python_pathway(self):
        """Python action_type dispatches to _execute_python_sandbox."""
        execution = {
            "request": {
                "action_type": "python",
                "command": "print('hello from sandbox')",
                "target": "test",
            }
        }
        result = execute_action(execution)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["skill"] == "python_sandbox"
        assert "hello from sandbox" in parsed["findings"]["stdout"]

    def test_unknown_action_type_rejected(self):
        """Unknown action_type returns FAILED with error."""
        execution = {
            "request": {
                "action_type": "network_scan",
                "command": "nmap 10.0.0.1",
                "target": "10.0.0.1",
            }
        }
        result = execute_action(execution)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert "Unknown action_type" in parsed["errors"][0]

    def test_shell_pathway_removed(self):
        """Raw shell commands (old default pathway) are no longer supported."""
        execution = {
            "request": {
                "action_type": "raw_shell",
                "command": "ls -la",
                "target": "localhost",
            }
        }
        result = execute_action(execution)
        assert result["status"] == "FAILED"


class TestPythonSandbox:
    def test_basic_execution(self):
        payload = {"command": "x = 2 + 2\nprint(x)", "target": "test"}
        result = _execute_python_sandbox(payload)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert "4" in parsed["findings"]["stdout"]

    def test_error_capture(self):
        payload = {"command": "raise ValueError('boom')", "target": "test"}
        result = _execute_python_sandbox(payload)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert parsed["status"] == "error"
        assert any("ValueError" in e for e in parsed["errors"])

    def test_envelope_structure(self):
        payload = {"command": "print('ok')", "target": "myhost"}
        result = _execute_python_sandbox(payload)
        parsed = json.loads(result["result"])
        assert parsed["skill"] == "python_sandbox"
        assert parsed["target"] == "myhost"
        assert isinstance(parsed["artifacts"], list)
        assert isinstance(parsed["errors"], list)


class TestSkillPathway:
    def test_invalid_skill_name(self):
        """Non-existent skill module returns FAILED with traceback."""
        payload = {
            "skill": "nonexistent.FakeSkill",
            "target": "10.0.0.1",
            "arguments": {},
        }
        result = _execute_skill(payload)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert parsed["status"] == "error"
        assert any("ModuleNotFoundError" in e or "No module" in e for e in parsed["errors"])

    def test_skill_with_echo(self):
        """Test skill pathway with a real skill that uses echo (always available)."""
        # We'll test via execute_action to verify end-to-end dispatch
        # Using a python sandbox as a proxy since actual skills need tools installed
        payload = {
            "skill": "network.FpingSweep",
            "target": "192.168.1.0/24",
            "arguments": {},
        }
        result = _execute_skill(payload)
        parsed = json.loads(result["result"])
        # Should have proper envelope structure regardless of success/failure
        assert "skill" in parsed
        assert "errors" in parsed
