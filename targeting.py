from urllib.parse import urlparse


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "0.0.0.0", "localhost"}


def normalize_taskmaster_host(host: str | None) -> str:
    """Map loopback values to a host-reachable address for containerized agents."""
    candidate = (host or "").strip()
    if not candidate:
        return "host.docker.internal"
    if candidate.lower() in _LOOPBACK_HOSTS:
        return "host.docker.internal"
    return candidate


def _normalize_path(path: str) -> str:
    if not path or path == "/":
        return ""
    return path.rstrip("/")


def _target_parts(value: str | None) -> dict:
    raw = (value or "").strip()
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    return {
        "raw": raw.rstrip("/") if raw != "/" else raw,
        "host": (parsed.hostname or "").lower(),
        "path": _normalize_path(parsed.path or ""),
    }


def targets_match(scope: str | None, target: str | None) -> bool:
    """
    Match a target scope against a queued execution target.

    Supports:
    - exact target equality
    - hostname scope matching a full URL target on the same host
    - exact URL path matching when both sides include a path
    """
    scoped = _target_parts(scope)
    candidate = _target_parts(target)

    if not scoped["raw"] or not candidate["raw"]:
        return False

    if scoped["raw"] == candidate["raw"]:
        return True

    if not scoped["host"] or not candidate["host"]:
        return False

    if scoped["host"] != candidate["host"]:
        return False

    if scoped["path"] and candidate["path"]:
        return scoped["path"] == candidate["path"]

    return True
