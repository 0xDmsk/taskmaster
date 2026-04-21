"""
Unit tests for the playwright_operator two-pathway dispatch.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from executors.playwright_operator import (
    SUPPORTED_ACTION_TYPES,
    execute_action,
    _execute_playwright_script,
    _execute_browser_skill,
)


class TestSupportedActionTypes:
    def test_playwright_supported(self):
        assert "playwright" in SUPPORTED_ACTION_TYPES

    def test_playwright_skill_supported(self):
        assert "playwright_skill" in SUPPORTED_ACTION_TYPES

    def test_kali_types_not_supported(self):
        assert "skill" not in SUPPORTED_ACTION_TYPES
        assert "python" not in SUPPORTED_ACTION_TYPES


class TestExecuteActionDispatch:
    def test_playwright_script_pathway(self):
        """playwright action_type dispatches to _execute_playwright_script."""
        envelope = {
            "skill": "playwright_script",
            "target": "https://example.com",
            "status": "success",
            "findings": {"title": "Example"},
            "artifacts": [],
            "errors": [],
        }
        execution = {
            "request": {
                "action_type": "playwright",
                "script": f"import json; print(json.dumps({json.dumps(envelope)}))",
                "target": "https://example.com",
                "arguments": {},
            }
        }
        result = execute_action(execution)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["findings"]["title"] == "Example"

    def test_playwright_skill_pathway_unknown_skill(self):
        """playwright_skill with non-existent class returns FAILED."""
        execution = {
            "request": {
                "action_type": "playwright_skill",
                "skill": "browser.NonExistentSkill",
                "target": "https://example.com",
                "arguments": {},
            }
        }
        result = execute_action(execution)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert parsed["status"] == "error"

    def test_unknown_action_type_rejected(self):
        """Unknown action_type returns FAILED."""
        execution = {
            "request": {
                "action_type": "nmap_scan",
                "target": "10.0.0.1",
            }
        }
        result = execute_action(execution)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert "Unknown action_type" in parsed["errors"][0]

    def test_kali_action_types_rejected(self):
        """Kali-specific action types are not handled by the playwright operator."""
        for action_type in ("skill", "python"):
            execution = {"request": {"action_type": action_type, "target": "10.0.0.1"}}
            result = execute_action(execution)
            assert result["status"] == "FAILED"


class TestPlaywrightScriptExecution:
    def test_json_envelope_output(self):
        """Script that prints a valid JSON envelope is parsed correctly."""
        envelope = {
            "skill": "playwright_script",
            "target": "https://example.com",
            "status": "success",
            "findings": {"pages_visited": 3},
            "artifacts": [],
            "errors": [],
        }
        payload = {
            "script": f"import json; print(json.dumps({json.dumps(envelope)}))",
            "target": "https://example.com",
            "arguments": {},
        }
        result = _execute_playwright_script(payload)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["findings"]["pages_visited"] == 3

    def test_non_json_output_wrapped(self):
        """Script that prints plain text is wrapped in a standard envelope."""
        payload = {
            "script": "print('scan complete')",
            "target": "https://example.com",
            "arguments": {},
        }
        result = _execute_playwright_script(payload)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["skill"] == "playwright_script"
        assert "scan complete" in parsed["findings"]["stdout"]

    def test_script_exception_returns_failed(self):
        """Script that raises an exception returns FAILED."""
        payload = {
            "script": "raise RuntimeError('browser crashed')",
            "target": "https://example.com",
            "arguments": {},
        }
        result = _execute_playwright_script(payload)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert parsed["status"] == "error"

    def test_target_passed_as_env_var(self):
        """TARGET env var is available to the script."""
        payload = {
            "script": "import os, json; print(json.dumps({'skill':'s','target':os.environ['TARGET'],'status':'success','findings':{},'artifacts':[],'errors':[]}))",
            "target": "https://target.example.com",
            "arguments": {},
        }
        result = _execute_playwright_script(payload)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["target"] == "https://target.example.com"

    def test_arguments_passed_as_env_var(self):
        """PLAYWRIGHT_ARGS env var contains JSON-encoded arguments."""
        payload = {
            "script": (
                "import os, json; "
                "args = json.loads(os.environ['PLAYWRIGHT_ARGS']); "
                "print(json.dumps({'skill':'s','target':'t','status':'success',"
                "'findings':{'depth': args.get('depth')},'artifacts':[],'errors':[]}))"
            ),
            "target": "https://example.com",
            "arguments": {"depth": 3},
        }
        result = _execute_playwright_script(payload)
        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["findings"]["depth"] == 3

    def test_error_status_in_envelope_maps_to_failed(self):
        """Envelope with status=error results in FAILED task status."""
        envelope = {
            "skill": "playwright_script",
            "target": "t",
            "status": "error",
            "findings": {},
            "artifacts": [],
            "errors": ["login failed"],
        }
        payload = {
            "script": f"import json; print(json.dumps({json.dumps(envelope)}))",
            "target": "t",
            "arguments": {},
        }
        result = _execute_playwright_script(payload)
        assert result["status"] == "FAILED"

    def test_script_timeout(self):
        """Script that exceeds timeout returns FAILED."""
        payload = {
            "script": "import time; time.sleep(9999)",
            "target": "t",
            "arguments": {},
        }
        with patch("executors.playwright_operator.subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=300)
            result = _execute_playwright_script(payload)

        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert "timed out" in parsed["errors"][0]


class TestBrowserSkillDispatch:
    def test_missing_module_returns_failed(self):
        """Non-existent module returns FAILED with error envelope."""
        payload = {
            "skill": "browser.DoesNotExist",
            "target": "https://example.com",
            "arguments": {},
        }
        result = _execute_browser_skill(payload)
        assert result["status"] == "FAILED"
        parsed = json.loads(result["result"])
        assert parsed["status"] == "error"
        assert len(parsed["errors"]) > 0

    def test_envelope_structure_on_error(self):
        """Error envelope contains all required keys."""
        payload = {
            "skill": "browser.NoSuchSkill",
            "target": "https://example.com",
            "arguments": {},
        }
        result = _execute_browser_skill(payload)
        parsed = json.loads(result["result"])
        for key in ("skill", "target", "status", "findings", "artifacts", "errors"):
            assert key in parsed

    def test_valid_skill_class_is_called(self, tmp_path):
        """A valid BaseBrowserSkill subclass is imported and run() is called."""
        mock_result = {
            "skill": "browser.MockSPASkill",
            "target": "https://example.com",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:00:01+00:00",
            "tool": "playwright",
            "tool_version": "1.48.0",
            "command": "",
            "findings": {"title": "Mock SPA"},
            "artifacts": [],
            "errors": [],
        }

        mock_skill_instance = MagicMock()
        mock_skill_instance.run.return_value = mock_result
        mock_skill_class = MagicMock(return_value=mock_skill_instance)

        mock_module = MagicMock()
        mock_module.MockSPASkill = mock_skill_class

        with patch("importlib.import_module", return_value=mock_module):
            payload = {
                "skill": "browser.MockSPASkill",
                "target": "https://example.com",
                "arguments": {"depth": 2},
            }
            result = _execute_browser_skill(payload)

        assert result["status"] == "COMPLETED"
        parsed = json.loads(result["result"])
        assert parsed["findings"]["title"] == "Mock SPA"
        mock_skill_class.assert_called_once_with(target="https://example.com")
        mock_skill_instance.run.assert_called_once_with(depth=2)
