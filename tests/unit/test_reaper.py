import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools import reaper

CFG = {
    "enabled": True,
    "interval": 60,
    "idle_timeout": 900,
    "stale_timeout": 7200,
    "max_age": 14400,
    "orphan_timeout": 300,
}


def _completed(stdout="", returncode=0):
    return Mock(returncode=returncode, stdout=stdout, stderr="")


def _started_ago(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _ps_listing(name):
    return json.dumps({"Names": name, "State": "running"}) + "\n"


def _inspect(name, started_ago_s, executor_id=None):
    return [
        {
            "Config": {
                "Image": "kali-smart-operator",
                "Env": [f"EXECUTOR_ID={executor_id or name}"],
                "Labels": {"taskmaster.managed": "true"},
            },
            "State": {"StartedAt": _started_ago(started_ago_s)},
        }
    ]


def test_idle_container_past_grace_is_reaped():
    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=[]),
        patch("tools.reaper._inspect_container", return_value=_inspect("kali-agent-aaa", 1200)[0]),
        patch("tools.reaper.log_event"),
    ):
        run.side_effect = [
            _completed(_ps_listing("kali-agent-aaa")),
            _completed(),  # docker stop
            _completed(),  # docker rm
        ]
        result = reaper.reap_once(CFG)

    assert len(result["reaped"]) == 1
    assert result["reaped"][0]["container"] == "kali-agent-aaa"
    assert result["reaped"][0]["reason"].startswith("idle:")


def test_idle_container_inside_grace_is_kept():
    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=[]),
        patch("tools.reaper._inspect_container", return_value=_inspect("kali-agent-young", 60)[0]),
    ):
        run.side_effect = [_completed(_ps_listing("kali-agent-young"))]
        result = reaper.reap_once(CFG)

    assert result["reaped"] == []


def test_stale_execution_reaps_and_fails_execution():
    name = "kali-agent-stale"
    stale_updated = (datetime.utcnow() - timedelta(seconds=8000)).isoformat()
    executions = [
        {
            "execution_id": "e1",
            "executor_id": name,
            "status": "RUNNING",
            "updated_at": stale_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper._inspect_container", return_value=_inspect(name, 9000)[0]),
        patch("tools.reaper.update_execution") as upd,
        patch("tools.reaper.log_event") as log,
    ):
        run.side_effect = [
            _completed(_ps_listing(name)),
            _completed(),
            _completed(),
        ]
        result = reaper.reap_once(CFG)

    assert result["reaped"][0]["reason"].startswith("stale_heartbeat:")
    upd.assert_called_once()
    args, _ = upd.call_args
    assert args[0] == "e1"
    assert args[1]["status"] == "FAILED"
    assert args[1]["updated_by"] == "reaper"
    # Both execution_recovered and agent_reaped events.
    event_types = [c.args[0] for c in log.call_args_list]
    assert "execution_recovered" in event_types
    assert "agent_reaped" in event_types


def test_stale_execution_with_timezone_aware_updated_at():
    # Regression: production writes timezone-AWARE updated_at
    # (datetime.now(timezone.utc)), but the reaper compared it against a naive
    # cutoff — raising "can't compare offset-naive and offset-aware datetimes"
    # on every pass while a long execution stayed RUNNING. The reaper must
    # classify aware timestamps without crashing.
    name = "kali-agent-aware"
    stale_updated = (datetime.now(timezone.utc) - timedelta(seconds=8000)).isoformat()
    executions = [
        {
            "execution_id": "e-aware",
            "executor_id": name,
            "status": "RUNNING",
            "updated_at": stale_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper._inspect_container", return_value=_inspect(name, 9000)[0]),
        patch("tools.reaper.update_execution"),
        patch("tools.reaper.log_event"),
    ):
        run.side_effect = [_completed(_ps_listing(name)), _completed(), _completed()]
        result = reaper.reap_once(CFG)

    assert result["reaped"][0]["reason"].startswith("stale_heartbeat:")


def test_active_execution_with_fresh_updated_at_is_kept():
    name = "kali-agent-busy"
    fresh_updated = datetime.utcnow().isoformat()
    executions = [
        {
            "execution_id": "e2",
            "executor_id": name,
            "status": "RUNNING",
            "updated_at": fresh_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper._inspect_container", return_value=_inspect(name, 1800)[0]),
    ):
        run.side_effect = [_completed(_ps_listing(name))]
        result = reaper.reap_once(CFG)

    assert result["reaped"] == []


def test_hard_age_cap_overrides_active_work():
    name = "kali-agent-old"
    fresh_updated = datetime.utcnow().isoformat()
    executions = [
        {
            "execution_id": "e3",
            "executor_id": name,
            "status": "RUNNING",
            "updated_at": fresh_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper._inspect_container", return_value=_inspect(name, 20000)[0]),
        patch("tools.reaper.update_execution") as upd,
        patch("tools.reaper.log_event"),
    ):
        run.side_effect = [
            _completed(_ps_listing(name)),
            _completed(),
            _completed(),
        ]
        result = reaper.reap_once(CFG)

    assert result["reaped"][0]["reason"].startswith("hard_age_cap:")
    upd.assert_called_once()
    assert upd.call_args.args[0] == "e3"


def test_disabled_reaper_skips():
    cfg = dict(CFG, enabled=False)
    with patch("tools.reaper.subprocess.run") as run:
        result = reaper.reap_once(cfg)
    assert result == {"reaped": [], "skipped": "disabled"}
    run.assert_not_called()


def test_non_taskmaster_container_is_ignored():
    inspect = {
        "Config": {
            "Image": "redis",
            "Env": [],
            "Labels": {},
        },
        "State": {"StartedAt": _started_ago(20000)},
    }
    listing = json.dumps({"Names": "some-redis", "State": "running"}) + "\n"

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=[]),
        patch("tools.reaper._inspect_container", return_value=inspect),
    ):
        run.side_effect = [_completed(listing)]
        result = reaper.reap_once(CFG)

    assert result["reaped"] == []


def test_orphan_execution_with_no_live_container_is_recovered():
    """A RUNNING row whose container has vanished should be force-failed."""
    old_updated = (datetime.utcnow() - timedelta(seconds=600)).isoformat()
    executions = [
        {
            "execution_id": "orphan-1",
            "executor_id": "kali-agent-gone",
            "status": "RUNNING",
            "updated_at": old_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper.update_execution") as upd,
        patch("tools.reaper.log_event") as log,
    ):
        # docker ps reports no running containers.
        run.side_effect = [_completed("")]
        result = reaper.reap_once(CFG)

    assert result["reaped"] == []
    assert len(result["orphans_recovered"]) == 1
    assert result["orphans_recovered"][0]["execution_id"] == "orphan-1"
    upd.assert_called_once()
    assert upd.call_args.args[0] == "orphan-1"
    assert upd.call_args.args[1]["status"] == "FAILED"
    event_types = [c.args[0] for c in log.call_args_list]
    assert "execution_recovered" in event_types


def test_orphan_within_grace_window_is_kept():
    """A recently-updated row without a container is inside the grace window."""
    fresh_updated = (datetime.utcnow() - timedelta(seconds=30)).isoformat()
    executions = [
        {
            "execution_id": "orphan-young",
            "executor_id": "kali-agent-gone",
            "status": "RUNNING",
            "updated_at": fresh_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper.update_execution") as upd,
        patch("tools.reaper.log_event"),
    ):
        run.side_effect = [_completed("")]
        result = reaper.reap_once(CFG)

    assert result["orphans_recovered"] == []
    upd.assert_not_called()


def test_execution_with_live_container_is_not_treated_as_orphan():
    """A stale row is left to the container-based rules while its container lives."""
    name = "kali-agent-live"
    old_updated = (datetime.utcnow() - timedelta(seconds=600)).isoformat()
    executions = [
        {
            "execution_id": "e-live",
            "executor_id": name,
            "status": "RUNNING",
            "updated_at": old_updated,
        }
    ]

    with (
        patch("tools.reaper.subprocess.run") as run,
        patch("tools.reaper.load_executions", return_value=executions),
        patch("tools.reaper._inspect_container", return_value=_inspect(name, 120)[0]),
        patch("tools.reaper.update_execution") as upd,
        patch("tools.reaper.log_event"),
    ):
        # Container is present and young; neither stale nor orphan rules fire.
        run.side_effect = [_completed(_ps_listing(name))]
        result = reaper.reap_once(CFG)

    assert result["reaped"] == []
    assert result["orphans_recovered"] == []
    upd.assert_not_called()


def test_parse_docker_time_handles_nanoseconds_and_z():
    parsed = reaper._parse_docker_time("2026-05-07T10:32:14.123456789Z")
    assert parsed is not None
    assert parsed.tzinfo is timezone.utc
    assert parsed.microsecond == 123456


def test_parse_docker_time_returns_none_for_zero_value():
    assert reaper._parse_docker_time("0001-01-01T00:00:00Z") is None
    assert reaper._parse_docker_time("") is None
    assert reaper._parse_docker_time(None) is None
