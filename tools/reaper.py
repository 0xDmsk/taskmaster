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

Separately, each pass also sweeps **orphaned executions**: rows still in
CLAIMED/RUNNING whose executor has no live container at all (the container
crashed or was removed out-of-band) and whose ``updated_at`` is older than
orphan_timeout. These are force-failed so the per-target lock releases without
waiting for a manual ``recover_execution`` call. The container-based rules above
can only act on containers Docker still reports; the orphan sweep covers the
gap where the container is already gone.

Configured via env vars (all optional):
  TASKMASTER_REAPER_ENABLED         default true
  TASKMASTER_REAPER_INTERVAL        default 60   (seconds between passes)
  TASKMASTER_REAPER_IDLE_TIMEOUT    default 900  (15 min)
  TASKMASTER_REAPER_STALE_TIMEOUT   default 7200 (2 h)
  TASKMASTER_REAPER_MAX_AGE         default 14400 (4 h)
  TASKMASTER_REAPER_ORPHAN_TIMEOUT  default 300  (5 min)
"""

import glob
import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone

import config
from audit.audit_manager import log_event
from state.storage import load_executions, update_execution
from tools.cleanup_agents import _extract_env, _inspect_container, _is_taskmaster_agent

DEFAULT_INTERVAL = 60
DEFAULT_IDLE_TIMEOUT = 900
DEFAULT_STALE_TIMEOUT = 7200
DEFAULT_MAX_AGE = 14400
DEFAULT_ORPHAN_TIMEOUT = 300

logger = logging.getLogger(__name__)


def _config():
    enabled = os.environ.get("TASKMASTER_REAPER_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    return {
        "enabled": enabled,
        "interval": int(os.environ.get("TASKMASTER_REAPER_INTERVAL", DEFAULT_INTERVAL)),
        "idle_timeout": int(os.environ.get("TASKMASTER_REAPER_IDLE_TIMEOUT", DEFAULT_IDLE_TIMEOUT)),
        "stale_timeout": int(
            os.environ.get("TASKMASTER_REAPER_STALE_TIMEOUT", DEFAULT_STALE_TIMEOUT)
        ),
        "max_age": int(os.environ.get("TASKMASTER_REAPER_MAX_AGE", DEFAULT_MAX_AGE)),
        "orphan_timeout": int(
            os.environ.get("TASKMASTER_REAPER_ORPHAN_TIMEOUT", DEFAULT_ORPHAN_TIMEOUT)
        ),
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
            capture_output=True,
            text=True,
            check=True,
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


def _find_partial_artifacts(execution):
    """Best-effort glob of /loot for output a nuclei skill may have streamed to
    disk before this execution was reaped.

    Both nuclei skills (`web.NucleiScan`, `mobile.MobileNucleiScan`) write
    matches to a `-jsonl`/`-o` file incrementally, so a killed process still
    leaves real partial results on disk — but LOOT_DIR is one directory shared
    by every agent, so there's no execution-scoped subfolder to look in. This
    is a heuristic (skill name + target substring + mtime not older than the
    execution) good enough to point a human at the right file, not a
    guaranteed exact match.
    """
    request = execution.get("request") or {}
    if isinstance(request, str):
        try:
            request = json.loads(request)
        except json.JSONDecodeError:
            request = {}
    skill = request.get("skill", "")
    if not skill.endswith("NucleiScan"):
        return []

    loot_dir = config.LOOT_DIR
    if not os.path.isdir(loot_dir):
        return []

    created = _parse_ts(execution.get("created_at"))
    target = execution.get("target") or ""
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", target)[:60]

    hits = []
    for path in glob.glob(os.path.join(loot_dir, "*nuclei*.jsonl")):
        if stem and stem not in os.path.basename(path):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
        except OSError:
            continue
        if created and mtime < created:
            continue
        hits.append(path)
    return hits


def _fail_execution_for_reap(execution_id, reason, execution=None):
    from state.state import cancel_blocked_dependents

    if execution is not None:
        artifacts = _find_partial_artifacts(execution)
        if artifacts:
            reason = f"{reason} | possible partial output on disk: {', '.join(artifacts)}"

    update_execution(
        execution_id,
        {
            "status": "FAILED",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "reaper",
            "result": reason,
        },
    )
    log_event(
        "execution_recovered",
        {
            "execution_id": execution_id,
            "reason": reason,
            "source": "reaper",
        },
    )
    # A failed execution can never satisfy its dependents — cancel the chain.
    cancel_blocked_dependents(execution_id, f"Cancelled: dependency {execution_id} failed (reaper)")


def _parse_ts(value):
    """Parse an ISO timestamp into an aware UTC datetime, or None.

    Timestamps in the store are mixed: state transitions write timezone-aware
    values (``datetime.now(timezone.utc)``) while some paths historically wrote
    naive ones (``datetime.utcnow()``). Normalize everything to aware-UTC so
    comparisons never mix naive and aware datetimes (which raises TypeError).
    """
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _classify(active, age_seconds, cfg):
    """Return (reason, affected_executions) or (None, [])."""
    if age_seconds >= cfg["max_age"]:
        return f"hard_age_cap:{int(age_seconds)}s", active

    if active:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cfg["stale_timeout"])
        stale = []
        for e in active:
            ts = _parse_ts(e.get("updated_at"))
            if ts is None:
                continue
            if ts < cutoff:
                stale.append(e)
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

    executions = load_executions()
    active_by_executor = {}
    for e in executions:
        if e.get("status") in ("CLAIMED", "RUNNING") and e.get("executor_id"):
            active_by_executor.setdefault(e["executor_id"], []).append(e)

    live_executors = set()
    for name, inspect in _list_running_taskmaster_containers():
        env = _extract_env(inspect)
        executor_id = env.get("EXECUTOR_ID") or name
        live_executors.add(executor_id)
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
                execution=execution,
            )

        _stop_container(name)
        log_event(
            "agent_reaped",
            {
                "container": name,
                "executor_id": executor_id,
                "reason": reason,
                "age_seconds": int(age_seconds),
                "affected_executions": [e["execution_id"] for e in affected],
            },
        )
        logger.info("Reaper stopped %s (%s)", name, reason)
        reaped.append({"container": name, "reason": reason})

    orphans = _sweep_orphans(executions, live_executors, cfg)
    return {"reaped": reaped, "orphans_recovered": orphans}


def _sweep_orphans(executions, live_executors, cfg):
    """Force-fail CLAIMED/RUNNING executions whose container no longer exists.

    An execution is orphaned when its executor is not among the currently
    running Taskmaster containers *and* it has been untouched for longer than
    ``orphan_timeout`` (a grace window so a briefly-restarting or just-spawned
    container isn't mistaken for a dead one). Force-failing releases the
    per-target lock that a vanished container would otherwise hold forever.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=cfg["orphan_timeout"])
    recovered = []
    for e in executions:
        if e.get("status") not in ("CLAIMED", "RUNNING"):
            continue
        executor_id = e.get("executor_id")
        if not executor_id or executor_id in live_executors:
            continue
        ts = _parse_ts(e.get("updated_at"))
        if ts is None:
            continue
        if ts >= cutoff:
            continue

        eid = e["execution_id"]
        reason = (
            f"Reaper recovered orphan {eid}: executor {executor_id} has no live "
            f"container (idle > {cfg['orphan_timeout']}s)"
        )
        _fail_execution_for_reap(eid, reason, execution=e)
        logger.info("Reaper recovered orphan %s (executor %s gone)", eid, executor_id)
        recovered.append({"execution_id": eid, "executor_id": executor_id})
    return recovered


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
        cfg["interval"],
        cfg["idle_timeout"],
        cfg["stale_timeout"],
        cfg["max_age"],
    )
    return thread
