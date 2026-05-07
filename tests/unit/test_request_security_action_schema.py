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
