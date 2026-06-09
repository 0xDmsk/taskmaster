import subprocess
import json
import sys

from targeting import targets_match

KNOWN_AGENT_IMAGES = {"kali-smart-operator", "playwright-operator", "report-operator"}


def _inspect_container(container_name):
    result = subprocess.run(
        ["docker", "inspect", container_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    return payload[0] if payload else None


def _extract_env(inspect_data):
    env_pairs = {}
    env_list = inspect_data.get("Config", {}).get("Env", []) if inspect_data else []
    for entry in env_list:
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        env_pairs[key] = value
    return env_pairs


def _image_name(inspect_data):
    image = inspect_data.get("Config", {}).get("Image", "") if inspect_data else ""
    return image.split(":", 1)[0]


def _is_taskmaster_agent(container_name, inspect_data):
    if (
        container_name.startswith("kali-agent")
        or container_name.startswith("playwright-agent")
        or container_name.startswith("reporting-agent")
    ):
        return True

    labels = inspect_data.get("Config", {}).get("Labels", {}) if inspect_data else {}
    if labels.get("taskmaster.managed") == "true":
        return True

    env_pairs = _extract_env(inspect_data)
    if env_pairs.get("EXECUTOR_ID") == container_name and _image_name(inspect_data) in KNOWN_AGENT_IMAGES:
        return True

    return False


def handle_cleanup_agents(arguments):
    """
    Stops and removes agent containers (kali-agent-*, playwright-agent-*, and reporting-agent-*).
    Filters:
      - target: Only cleanup agents assigned to this target (via TARGET_SCOPE env)
      - agent_id: Cleanup a specific agent
      - all: Cleanup all agent containers (default: False)
      - state: Filter by 'running' or 'stopped' (default: all states)
    """
    target = arguments.get("target")
    agent_id = arguments.get("agent_id")
    cleanup_all = arguments.get("all", False)
    state_filter = arguments.get("state")

    try:
        # List all containers (running + stopped) as JSON for reliable parsing
        cmd_ls = [
            "docker", "ps", "-a",
            "--format", "{{json .}}",
        ]
        result = subprocess.run(cmd_ls, capture_output=True, text=True, check=True)

        containers = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        to_cleanup = []

        for c in containers:
            name = c.get("Names", "")
            c_id = name.lstrip("/")  # docker ps Names may include leading /
            inspect_data = _inspect_container(c_id)

            # Only manage agent containers spawned by Taskmaster
            if not _is_taskmaster_agent(c_id, inspect_data):
                continue

            # Apply state filter before anything else
            c_state = c.get("State", "").lower()
            if state_filter and c_state != state_filter.lower():
                continue

            match = False
            if cleanup_all:
                match = True
            elif agent_id and c_id == agent_id:
                match = True
            elif target:
                env_pairs = _extract_env(inspect_data)
                if targets_match(env_pairs.get("TARGET_SCOPE"), target):
                    match = True

            if match:
                to_cleanup.append(c_id)

        if not to_cleanup:
            return {"status": "success", "message": "No matching agents found for cleanup", "cleaned": []}

        cleaned = []
        for cid in to_cleanup:
            subprocess.run(["docker", "stop", cid], capture_output=True)
            subprocess.run(["docker", "rm", cid], capture_output=True)
            cleaned.append(cid)

        return {
            "status": "success",
            "message": f"Cleaned up {len(cleaned)} agents",
            "cleaned": cleaned,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        args = json.loads(sys.argv[1])
        print(json.dumps(handle_cleanup_agents(args)))
    else:
        print(json.dumps({"error": "No arguments provided"}))
