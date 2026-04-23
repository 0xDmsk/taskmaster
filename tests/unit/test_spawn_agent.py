import json
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.spawn_agent import handle_spawn_agent


def test_spawn_agent_rewrites_loopback_taskmaster_host():
    completed = Mock(returncode=0, stdout="container-id\n", stderr="")

    with patch("tools.spawn_agent.subprocess.run", return_value=completed) as mock_run:
        result = handle_spawn_agent(
            {
                "agent_id": "test-agent",
                "taskmaster_host": "127.0.0.1",
                "taskmaster_port": "5000",
            }
        )

    assert result["status"] == "success"
    cmd = mock_run.call_args.args[0]
    assert "TASKMASTER_HOST=host.docker.internal" in cmd


def test_playwright_agent_exposes_interactive_browser_url():
    completed = Mock(returncode=0, stdout="container-id\n", stderr="")

    with (
        patch("tools.spawn_agent.subprocess.run", return_value=completed) as mock_run,
        patch("tools.spawn_agent._allocate_host_port", return_value=6081),
    ):
        result = handle_spawn_agent(
            {
                "agent_type": "playwright",
                "agent_id": "pw-agent",
                "target": "https://example.com",
            }
        )

    assert result["status"] == "success"
    assert result["interactive_browser"] is True
    assert result["novnc_url"] == "http://127.0.0.1:6081/vnc.html"

    cmd = mock_run.call_args.args[0]
    assert "127.0.0.1:6081:6080" in cmd
    assert "PLAYWRIGHT_HEADLESS=false" in cmd
    assert "PLAYWRIGHT_DEVTOOLS=true" in cmd
    assert "PLAYWRIGHT_SESSION_URL=http://127.0.0.1:6081/vnc.html" in cmd
    assert cmd[-1] == "playwright-operator"


def test_playwright_agent_can_disable_interactive_browser():
    completed = Mock(returncode=0, stdout="container-id\n", stderr="")

    with patch("tools.spawn_agent.subprocess.run", return_value=completed) as mock_run:
        result = handle_spawn_agent(
            {
                "agent_type": "playwright",
                "agent_id": "pw-agent",
                "interactive_browser": False,
            }
        )

    assert result["status"] == "success"
    assert result["interactive_browser"] is False
    assert result["novnc_url"] is None

    cmd = mock_run.call_args.args[0]
    assert "PLAYWRIGHT_HEADLESS=true" in cmd
    assert "PLAYWRIGHT_DEVTOOLS=false" in cmd
    assert "127.0.0.1:6080:6080" not in cmd


def test_playwright_agent_uses_image_default_command():
    completed = Mock(returncode=0, stdout="container-id\n", stderr="")

    with (
        patch("tools.spawn_agent.subprocess.run", return_value=completed) as mock_run,
        patch("tools.spawn_agent._allocate_host_port", return_value=6081),
    ):
        handle_spawn_agent(
            {
                "agent_type": "playwright",
                "agent_id": "pw-agent",
            }
        )

    cmd = mock_run.call_args.args[0]
    assert cmd[-1] == "playwright-operator"
    assert cmd[-2] != "playwright-operator"
