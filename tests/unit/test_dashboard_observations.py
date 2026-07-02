import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dashboard import render
from dashboard.api import get_findings, get_observations
from state.state import create_execution, transition_execution


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "executions.db")
    monkeypatch.setenv("STATE_DB", db_path)


def _create_completed_execution():
    create_execution(
        execution_id="exec-observation-1",
        target="https://example.test",
        security_phase="reconnaissance",
        request_payload={"justification": "Collect landing page indicators."},
    )
    transition_execution("exec-observation-1", "CLAIMED", "agent-1")
    transition_execution("exec-observation-1", "RUNNING", "agent-1")
    transition_execution(
        "exec-observation-1",
        "COMPLETED",
        "agent-1",
        result=json.dumps(
            {
                "skill": "browser.RenderedPageObserve",
                "tool": "playwright",
                "findings": {"title": "Example", "status_code": 200},
                "artifacts": ["/loot/example.json"],
                "errors": [],
            }
        ),
        interpretation="The page rendered and returned HTTP 200.",
    )


def test_dashboard_exposes_execution_output_as_observations():
    _create_completed_execution()

    observations = get_observations()

    assert len(observations) == 1
    assert observations[0]["observations"] == {"title": "Example", "status_code": 200}
    assert observations[0]["findings"] == observations[0]["observations"]
    assert get_findings() == observations


def test_observations_template_avoids_finding_label_for_execution_output():
    _create_completed_execution()
    observations = get_observations()

    html = render(
        "observations.html",
        page="observations",
        stats={},
        observations=observations,
    )

    assert "Execution Observations" in html
    assert "Observation Data" in html
    assert "1 observation" in html
    assert "Findings &amp; Results" not in html
    assert "<h4>Findings</h4>" not in html
