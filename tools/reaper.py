"""Background reaper that stops idle, stale, or over-aged agent containers.

A container is reaped when ANY of these is true:

1. Hard age cap     — older than max_age seconds, regardless of state. Backstop
                      for anything else that slips through.
2. Stale heartbeat  — has a CLAIMED/RUNNING execution whose ``updated_at`` is
                      older than stale_timeout. Container is stopped AND the
                      execution is force-failed so the target lock releases.
3. Idle past grace  — has no CLAIMED/RUNNING execution and was started more
                      than idle_timeout seconds ago. Catches "spawned, never
                      assigned work, forgotten".

Configured via env vars (all optional):
  TASKMASTER_REAPER_ENABLED         default true
  TASKMASTER_REAPER_INTERVAL        default 60   (seconds between passes)
  TASKMASTER_REAPER_IDLE_TIMEOUT    default 900  (15 min)
  TASKMASTER_REAPER_STALE_TIMEOUT   default 7200 (2 h)
  TASKMASTER_REAPER_MAX_AGE         default 14400 (4 h)
"""

import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone

from audit.audit_manager import log_event
from state.storage import load_executions, update_execution
from tools.cleanup_agents import _extract_env, _inspect_container, _is_taskmaster_agent

DEFAULT_INTERVAL = 60
DEFAULT_IDLE_TIMEOUT = 900
DEFAULT_STALE_TIMEOUT = 7200
DEFAULT_MAX_AGE = 14400

logger = logging.getLogger(__name__)


def _config():
    enabled = os.environ.get("TASKMASTER_REAPER_ENABLED", "true").lower() in (
        "true", "1", "yes", "on",
    )
    return {
        "enabled": enabled,
        "interval": int(os.environ.get("TASKMASTER_REAPER_INTERVAL", DEFAULT_INTERVAL)),
        "idle_timeout": int(os.environ.get("TASKMASTER_REAPER_IDLE_TIMEOUT", DEFAULT_IDLE_TIMEOUT)),
        "stale_timeout": int(os.environ.get("TASKMASTER_REAPER_STALE_TIMEOUT", DEFAULT_STALE_TIMEOUT)),
        "max_age": int(os.environ.get("TASKMASTER_REAPER_MAX_AGE", DEFAULT_MAX_AGE)),
    }


def _parse_docker_time(ts):
    """Parse docker's RFC3339 timestamp; tolerate nanosecond precision and Z."""
    if not ts or ts.startswith("0001-01-01"):
        return None
    cleaned = ts.rstrip("Z")
    if "." in cleaned:
        head, frac = cleaned.split(".", 1)
        frac = re.sub(r"\D", "", frac)[:6]
        cleaned = f"{head}.{frac}" if frac else head
    try:
        return datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _list_running_taskmaster_containers():
    """Return [(name, inspect_data)] for running, Taskmaster-managed containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Reaper: docker ps failed: %s", exc)
        return []

    containers = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = entry.get("Names", "").lstrip("/")
        if not name:
            continue
        inspect = _inspect_container(name)
        if not _is_taskmaster_agent(name, inspect):
            continue
        containers.append((name, inspect))
    return containers


def _container_started_at(inspect):
    if not inspect:
        return None
    return _parse_docker_time(inspect.get("State", {}).get("StartedAt"))


def _stop_container(name):
    subprocess.run(["docker", "stop", name], capture_output=True)
    subprocess.run(["docker", "rm", name], capture_output=True)


def _fail_execution_for_reap(execution_id, reason):
    update_execution(execution_id, {
        "status": "FAILED",
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": "reaper",
        "result": reason,
    })
    log_event("execution_recovered", {
        "execution_id": execution_id,
        "reason": reason,
        "source": "reaper",
    })


def _classify(active, age_seconds, cfg):
    """Return (reason, affected_executions) or (None, [])."""
    if age_seconds >= cfg["max_age"]:
        return f"hard_age_cap:{int(age_seconds)}s", active

    if active:
        cutoff = datetime.utcnow() - timedelta(seconds=cfg["stale_timeout"])
        stale = []
        for e in active:
            updated = e.get("updated_at")
            if not updated:
                continue
            try:
                if datetime.fromisoformat(updated) < cutoff:
                    stale.append(e)
            except ValueError:
                continue
        if stale:
            return f"stale_heartbeat:{cfg['stale_timeout']}s", stale
        return None, []

    if age_seconds >= cfg["idle_timeout"]:
        return f"idle:{int(age_seconds)}s_no_active_work", []

    return None, []


def reap_once(cfg=None):
    """Run a single reaper pass. Returns {'reaped': [...]} (or skip marker)."""
    if cfg is None:
        cfg = _config()
    if not cfg["enabled"]:
        return {"reaped": [], "skipped": "disabled"}

    now = datetime.now(timezone.utc)
    reaped = []

    active_by_executor = {}
    for e in load_executions():
        if e.get("status") in ("CLAIMED", "RUNNING") and e.get("executor_id"):
            active_by_executor.setdefault(e["executor_id"], []).append(e)

    for name, inspect in _list_running_taskmaster_containers():
        env = _extract_env(inspect)
        executor_id = env.get("EXECUTOR_ID") or name
        started_at = _container_started_at(inspect)
        age_seconds = (now - started_at).total_seconds() if started_at else 0
        active = active_by_executor.get(executor_id, [])

        reason, affected = _classify(active, age_seconds, cfg)
        if not reason:
            continue

        for execution in affected:
            _fail_execution_for_reap(
                execution["execution_id"],
                f"Reaper terminated {name} ({reason})",
            )

        _stop_container(name)
        log_event("agent_reaped", {
            "container": name,
            "executor_id": executor_id,
            "reason": reason,
            "age_seconds": int(age_seconds),
            "affected_executions": [e["execution_id"] for e in affected],
        })
        logger.info("Reaper stopped %s (%s)", name, reason)
        reaped.append({"container": name, "reason": reason})

    return {"reaped": reaped}


def start_reaper_thread():
    """Start a daemon thread that calls reap_once() forever. Returns it, or None if disabled."""
    cfg = _config()
    if not cfg["enabled"]:
        logger.info("Reaper disabled (TASKMASTER_REAPER_ENABLED=false)")
        return None

    def loop():
        while True:
            try:
                reap_once()
            except Exception:
                logger.exception("Reaper pass failed")
            time.sleep(cfg["interval"])

    thread = threading.Thread(target=loop, name="taskmaster-reaper", daemon=True)
    thread.start()
    logger.info(
        "Reaper started (interval=%ss, idle=%ss, stale=%ss, max_age=%ss)",
        cfg["interval"], cfg["idle_timeout"], cfg["stale_timeout"], cfg["max_age"],
    )
    return thread
