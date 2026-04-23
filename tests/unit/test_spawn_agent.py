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

