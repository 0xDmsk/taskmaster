import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from state.reporting import create_engagement, create_finding
from state.state import create_execution, transition_execution
from state.surface import (
    ingest_execution_endpoints,
    link_surface,
    list_surface,
    normalize_endpoint,
    resolve_surface_refs,
    upsert_surface_items,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_DB", str(tmp_path / "executions.db"))


@pytest.fixture
def eid():
    return create_engagement("ExampleCo Web Assessment")["engagement_id"]


def _by_key(items):
    return {i["key"]: i for i in items}


@pytest.mark.parametrize(
    "method,raw,default_host,key",
    [
        ("get", "https://API.example.com/users/42?x=1#f", "", "GET api.example.com/users/{id}"),
        (
            None,
            "POST /api/v1/users/search/",
            "app.example.com",
            "POST app.example.com/api/v1/users/search",
        ),
        (None, "http://h.example.com:8080/a", "", "ANY h.example.com:8080/a"),
        (None, "https://h.example.com:443/a", "", "ANY h.example.com/a"),
        (None, "http://h.example.com:443/a", "", "ANY h.example.com:443/a"),
        ("DELETE", "/orders/3f2a1c9e-1b2c-4d5e-8f90-a1b2c3d4e5f6", "", "DELETE /orders/{id}"),
        (None, "/files/deadbeefdeadbeefdead", "", "ANY /files/{id}"),
        (None, "api.example.com/health", "", "ANY api.example.com/health"),
        (None, "myapp://checkout/confirm", "", "ANY myapp://checkout/confirm"),
        (None, "https://example.com", "", "ANY example.com/"),
    ],
)
def test_normalize_endpoint(method, raw, default_host, key):
    assert normalize_endpoint(method, raw, default_host)["key"] == key


def test_normalize_rejects_empty():
    with pytest.raises(ValueError):
        normalize_endpoint("GET", "  ")


def test_upsert_is_idempotent_and_assigns_refs(eid):
    first = upsert_surface_items(
        eid,
        [
            {"kind": "functionality", "name": "Account export", "attack_surface_ref": "AS-2"},
            {
                "method": "GET",
                "url": "https://app.example.com/api/export?id=1",
                "parent": "Account export",
            },
            "POST https://app.example.com/api/export",
        ],
    )
    assert [i["ref"] for i in first] == ["FN-1", "EP-1", "EP-2"]
    assert first[1]["parent_id"] == first[0]["item_id"]

    # Same endpoint, different id/query: merges; blank description gets filled.
    again = upsert_surface_items(
        eid, [{"url": "GET https://app.example.com/api/export?id=2", "description": "CSV export"}]
    )
    assert again[0]["item_id"] == first[1]["item_id"]
    items = _by_key(list_surface(eid))
    assert len(items) == 3
    assert items["GET app.example.com/api/export"]["description"] == "CSV export"


def test_parent_ref_must_exist(eid):
    with pytest.raises(ValueError, match="Unknown functionality ref"):
        upsert_surface_items(eid, [{"url": "/x", "parent": "FN-9"}])


def test_unknown_engagement_rejected():
    with pytest.raises(ValueError, match="Unknown engagement_id"):
        upsert_surface_items("eng_missing", ["/x"])


def test_resolve_refs_creates_strings_but_not_unknown_refs(eid):
    (ep,) = upsert_surface_items(eid, ["GET https://app.example.com/a"])
    resolved = resolve_surface_refs(eid, ["ep-1", "POST /b"], default_host="app.example.com")
    assert resolved[0]["item_id"] == ep["item_id"]
    assert resolved[1]["key"] == "POST app.example.com/b"
    assert resolved[1]["ref"] == "EP-2"
    with pytest.raises(ValueError, match="Unknown surface ref"):
        resolve_surface_refs(eid, ["EP-7"])


def test_derived_status_progression(eid):
    (ep,) = upsert_surface_items(eid, ["GET https://app.example.com/a"])
    assert list_surface(eid)[0]["status"] == "discovered"

    create_execution("exec-1", "app.example.com", "enumeration", {}, engagement_id=eid)
    link_surface([ep["item_id"]], "tested", execution_id="exec-1")
    link_surface([ep["item_id"]], "tested", execution_id="exec-1")  # deduped
    item = list_surface(eid)[0]
    assert item["status"] == "in_progress"
    assert len(item["links"]) == 1
    assert item["phase_counts"] == {"enumeration": 1}

    transition_execution("exec-1", "CLAIMED", executor_id="w")
    transition_execution("exec-1", "RUNNING", executor_id="w")
    transition_execution("exec-1", "COMPLETED", executor_id="w", result="{}")
    assert list_surface(eid)[0]["status"] == "tested"

    fp = create_finding(engagement_id=eid, title="Noise", status="false_positive")
    link_surface([ep["item_id"]], "affects", finding_id=fp["finding_id"])
    assert list_surface(eid)[0]["status"] == "tested"

    real = create_finding(engagement_id=eid, title="IDOR", severity="High")
    link_surface([ep["item_id"]], "affects", finding_id=real["finding_id"])
    assert list_surface(eid)[0]["status"] == "vulnerable"


def test_ingest_execution_endpoints(eid):
    envelope = {
        "skill": "python_sandbox",
        "findings": {
            "stdout": "...",
            "endpoints": [
                "GET /api/users/1",
                {"method": "POST", "path": "/api/login"},
                {"url": "https://cdn.example.com/app.js"},
                42,  # malformed: skipped
                {"method": "GET"},  # no location: skipped
            ],
        },
    }
    create_execution("exec-r", "https://app.example.com", "reconnaissance", {}, engagement_id=eid)
    transition_execution("exec-r", "CLAIMED", executor_id="w")
    transition_execution("exec-r", "RUNNING", executor_id="w")
    transition_execution("exec-r", "COMPLETED", executor_id="w", result=json.dumps(envelope))

    assert ingest_execution_endpoints("exec-r") == 3
    assert ingest_execution_endpoints("exec-r") == 3  # re-ingest: no duplicates
    items = _by_key(list_surface(eid))
    assert set(items) == {
        "GET app.example.com/api/users/{id}",
        "POST app.example.com/api/login",
        "ANY cdn.example.com/app.js",
    }
    login = items["POST app.example.com/api/login"]
    assert login["source"] == "sandbox"
    assert [(l["rel"], l["execution_id"]) for l in login["links"]] == [("discovered", "exec-r")]


def test_ingest_skips_untagged_executions():
    create_execution("exec-u", "app.example.com", "reconnaissance", {})
    assert ingest_execution_endpoints("exec-u") == 0
