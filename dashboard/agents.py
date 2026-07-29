"""Container introspection for active kali-agent containers."""

import logging
import subprocess

from state.storage import load_executions

logger = logging.getLogger(__name__)


def get_agents():
    """List active kali-agent containers with state info."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=kali-agent",
             "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.CreatedAt}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            logger.warning("docker ps failed: %s", result.stderr)
            return []

        agents = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            state = "running" if "Up" in parts[2] else "stopped"
            agents.append({
                "id": parts[0][:12],
                "name": parts[1],
                "status": parts[2],
                "state": state,
                "image": parts[3],
                "created": parts[4],
            })
        return agents
    except FileNotFoundError:
        logger.info("docker not found, trying podman")
        return _try_podman()
    except Exception as e:
        logger.warning("Agent listing failed: %s", e)
        return []


def get_agent_history(engagement_id=None):
    """Group executions by executor_id, merged with active container data.

    When ``engagement_id`` is set, only executions tagged with that engagement are
    counted, and idle containers with no matching executions are omitted — under an
    engagement scope an unrelated live container isn't relevant. Unscoped ("All
    engagements"), idle containers are still surfaced so the fleet stays visible.
    """
    execs = load_executions()
    if engagement_id:
        execs = [e for e in execs if e.get("engagement_id") == engagement_id]
    containers = get_agents()
    container_map = {c["name"]: c for c in containers}

    agents_by_id = {}
    for e in execs:
        eid = e.get("executor_id")
        if not eid:
            continue
        if eid not in agents_by_id:
            agents_by_id[eid] = {
                "executor_id": eid,
                "container": container_map.get(eid),
                "executions": [],
                "stats": {"total": 0, "completed": 0, "failed": 0, "running": 0, "queued": 0},
            }
        entry = agents_by_id[eid]
        entry["executions"].append(e)
        entry["stats"]["total"] += 1
        s = e.get("status", "QUEUED")
        if s == "COMPLETED":
            entry["stats"]["completed"] += 1
        elif s == "FAILED":
            entry["stats"]["failed"] += 1
        elif s == "RUNNING":
            entry["stats"]["running"] += 1
        elif s in ("QUEUED", "CLAIMED"):
            entry["stats"]["queued"] += 1

    # Add live containers with no executions — only when unscoped, since an idle
    # container has no engagement association to match against.
    for name, c in container_map.items():
        if engagement_id:
            break
        if name not in agents_by_id:
            agents_by_id[name] = {
                "executor_id": name,
                "container": c,
                "executions": [],
                "stats": {"total": 0, "completed": 0, "failed": 0, "running": 0, "queued": 0},
            }

    return list(agents_by_id.values())


def _try_podman():
    """Fallback to podman if docker is not available."""
    try:
        result = subprocess.run(
            ["podman", "ps", "-a", "--filter", "name=kali-agent",
             "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.CreatedAt}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []

        agents = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            state = "running" if "Up" in parts[2] else "stopped"
            agents.append({
                "id": parts[0][:12],
                "name": parts[1],
                "status": parts[2],
                "state": state,
                "image": parts[3],
                "created": parts[4],
            })
        return agents
    except Exception:
        return []
