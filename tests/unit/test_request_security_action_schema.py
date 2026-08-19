import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.request_security_action import REQUEST_SECURITY_ACTION_SCHEMA


def test_request_security_action_json_matches_supported_action_types():
    schema_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../tools/request_security_action.json")
    )

    with open(schema_path, "r", encoding="utf-8") as f:
        published_schema = json.load(f)["inputSchema"]

    assert (
        published_schema["properties"]["action_type"]["enum"]
        == REQUEST_SECURITY_ACTION_SCHEMA["properties"]["action_type"]["enum"]
    )
    assert "script" in published_schema["properties"]


def test_mobile_skill_is_a_supported_action_type():
    # Regression: the operator/docs advertise mobile_skill, so the queue schema
    # (both the runtime validator and the published MCP schema) must accept it.
    assert "mobile_skill" in REQUEST_SECURITY_ACTION_SCHEMA["properties"]["action_type"]["enum"]

    schema_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../tools/request_security_action.json")
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        published_schema = json.load(f)["inputSchema"]
    assert "mobile_skill" in published_schema["properties"]["action_type"]["enum"]


def test_spawn_agent_schema_supports_mobile_agent_type():
    # Regression: spawn_agent must advertise the 'mobile' executor type or the
    # MCP client rejects agent_type="mobile" before the container is launched.
    from server import TOOLS

    enum = TOOLS["spawn_agent"]["inputSchema"]["properties"]["agent_type"]["enum"]
    assert "mobile" in enum
