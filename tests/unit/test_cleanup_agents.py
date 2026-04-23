import json
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.cleanup_agents import handle_cleanup_agents


def _completed(stdout="", returncode=0):
    return Mock(returncode=returncode, stdout=stdout, stderr="")


def test_cleanup_agents_finds_custom_agent_id():
    container_listing = json.dumps({"Names": "penny-recon", "State": "running"}) + "\n"
    inspect_payload = json.dumps([
        {
            "Config": {
                "Image": "kali-smart-operator",
                "Env": ["EXECUTOR_ID=penny-recon", "TARGET_SCOPE=example.com"],
                "Labels": {},
            }
        }
    ])

    with patch("tools.cleanup_agents.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed(container_listing),
            _completed(inspect_payload),
            _completed(),
            _completed(),
        ]

        result = handle_cleanup_agents({"agent_id": "penny-recon"})

    assert result["status"] == "success"
    assert result["cleaned"] == ["penny-recon"]


def test_cleanup_agents_finds_labeled_custom_agent_by_target():
    container_listing = json.dumps({"Names": "penny-recon", "State": "running"}) + "\n"
    inspect_payload = json.dumps([
        {
            "Config": {
                "Image": "kali-smart-operator",
                "Env": ["EXECUTOR_ID=penny-recon", "TARGET_SCOPE=corp.example"],
                "Labels": {"taskmaster.managed": "true"},
            }
        }
    ])

    with patch("tools.cleanup_agents.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed(container_listing),
            _completed(inspect_payload),
            _completed(),
            _completed(),
        ]

        result = handle_cleanup_agents({"target": "corp.example"})

    assert result["status"] == "success"
    assert result["cleaned"] == ["penny-recon"]


def test_cleanup_agents_matches_hostname_target_against_url_scope():
    container_listing = json.dumps({"Names": "penny-recon", "State": "running"}) + "\n"
    inspect_payload = json.dumps([
        {
            "Config": {
                "Image": "kali-smart-operator",
                "Env": [
                    "EXECUTOR_ID=penny-recon",
                    "TARGET_SCOPE=https://www.priceline.com/penny",
                ],
                "Labels": {"taskmaster.managed": "true"},
            }
        }
    ])

    with patch("tools.cleanup_agents.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _completed(container_listing),
            _completed(inspect_payload),
            _completed(),
            _completed(),
        ]

        result = handle_cleanup_agents({"target": "www.priceline.com"})

    assert result["status"] == "success"
    assert result["cleaned"] == ["penny-recon"]
