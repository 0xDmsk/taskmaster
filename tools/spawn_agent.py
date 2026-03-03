import subprocess
import os
import uuid

import config


def handle_spawn_agent(arguments):
    # Load .env file manually if it exists
    env_path = os.path.join(config.PROJECT_DIR, ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()

    target = arguments.get("target")
    mission = arguments.get("mission")
    agent_id = arguments.get("agent_id", f"kali-agent-{uuid.uuid4().hex[:6]}")

    # Configuration - check .env first, then process env, then default
    taskmaster_host = (
        arguments.get("taskmaster_host")
        or env_vars.get("TASKMASTER_HOST")
        or os.environ.get("TASKMASTER_HOST")
        or "192.168.64.1"
    )
    taskmaster_port = (
        arguments.get("taskmaster_port")
        or env_vars.get("TASKMASTER_PORT")
        or os.environ.get("TASKMASTER_PORT")
        or "5000"
    )
    proxy_url = (
        arguments.get("proxy_url")
        or env_vars.get("HTTP_PROXY")
        or os.environ.get("HTTP_PROXY")
        or "http://192.168.64.1:8888"
    )
    image_name = "kali-smart-operator"

    # Paths derived from config
    loot_dir = os.path.abspath(os.path.join(config.WORK_DIR, "audit", "loot"))
    skills_dir = os.path.abspath(os.path.join(config.PROJECT_DIR, "skills"))
    seclists_path = env_vars.get("SECLISTS_PATH") or os.environ.get("SECLISTS_PATH")

    cmd = [
        "container",
        "run",
        "-d",
        "--name",
        agent_id,
        "-v",
        f"{loot_dir}:/loot",  # Mount host audit/loot to container /loot
        "-v",
        f"{skills_dir}:/work/skills",  # Mount host skills to /work/skills
    ]

    if seclists_path:
        cmd.extend(["-v", f"{os.path.abspath(seclists_path)}:/usr/share/seclists"])

    cmd.extend(
        [
            "-e",
            f"TASKMASTER_HOST={taskmaster_host}",
            "-e",
            f"TASKMASTER_PORT={taskmaster_port}",
            "-e",
            f"EXECUTOR_ID={agent_id}",
            "-e",
            f"http_proxy={proxy_url}",
            "-e",
            f"https_proxy={proxy_url}",
            "-e",
            f"HTTP_PROXY={proxy_url}",
            "-e",
            f"HTTPS_PROXY={proxy_url}",
            "-e",
            f"no_proxy={taskmaster_host},localhost,127.0.0.1",
            "-e",
            f"NO_PROXY={taskmaster_host},localhost,127.0.0.1",
        ]
    )

    if seclists_path:
        cmd.extend(["-e", "SECLISTS_PATH=/usr/share/seclists"])

    if target:
        cmd.extend(["-e", f"TARGET_SCOPE={target}"])

    if mission:
        cmd.extend(["-e", f"AGENT_MISSION={mission}"])

    cmd.extend([image_name, "kali-operator"])

    try:
        # Run container command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()

        return {
            "status": "success",
            "agent_id": agent_id,
            "container_id": container_id,
            "target": target,
        }
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": f"Failed to spawn agent: {e.stderr}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Example usage
    import sys
    import json

    if len(sys.argv) > 1:
        args = json.loads(sys.argv[1])
        print(json.dumps(handle_spawn_agent(args)))
