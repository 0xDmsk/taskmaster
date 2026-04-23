import subprocess
import json
import os
import sys

def handle_cleanup_agents(arguments):
    """
    Stops and removes agent containers (kali-agent-* and playwright-agent-*).
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

            # Only manage agent containers spawned by Taskmaster
            if not (c_id.startswith("kali-agent") or c_id.startswith("playwright-agent")):
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
                # Inspect to check TARGET_SCOPE env var
                inspect_cmd = ["docker", "inspect", c_id,
                               "--format", "{{range .Config.Env}}{{.}}\n{{end}}"]
                inspect_res = subprocess.run(inspect_cmd, capture_output=True, text=True)
                if f"TARGET_SCOPE={target}" in inspect_res.stdout:
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
