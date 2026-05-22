import subprocess
import os
import socket
import uuid

import config
from targeting import normalize_taskmaster_host


def _bool_arg(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _allocate_host_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


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
    agent_type = arguments.get("agent_type", "kali")  # "kali" | "playwright" | "reporting"
    agent_id = arguments.get("agent_id", f"{agent_type}-agent-{uuid.uuid4().hex[:6]}")
    interactive_browser = _bool_arg(
        arguments.get("interactive_browser"), default=(agent_type == "playwright")
    )

    # Configuration - check .env first, then process env, then default
    taskmaster_host = normalize_taskmaster_host(
        arguments.get("taskmaster_host")
        or env_vars.get("TASKMASTER_HOST")
        or os.environ.get("TASKMASTER_HOST")
        or "host.docker.internal"
    )
    taskmaster_port = (
        arguments.get("taskmaster_port")
        or env_vars.get("TASKMASTER_PORT")
        or os.environ.get("TASKMASTER_PORT")
        or "5000"
    )
    # Proxy is opt-in per-call only. We deliberately do NOT fall back to the
    # MCP server's HTTP_PROXY or .env — Docker containers route to external
    # networks directly, so the only reason to set a proxy here is when the
    # caller explicitly wants traffic to flow through Burp (or similar).
    proxy_url = arguments.get("proxy_url") or ""
    interactive_hold_ms = (
        arguments.get("interactive_hold_ms")
        or env_vars.get("PLAYWRIGHT_INTERACTIVE_HOLD_MS")
        or os.environ.get("PLAYWRIGHT_INTERACTIVE_HOLD_MS")
        or "120000"
    )
    if agent_type == "playwright":
        image_name = "playwright-operator"
        operator_cmd = None
    elif agent_type == "reporting":
        image_name = "report-operator"
        operator_cmd = None
    else:
        image_name = "kali-smart-operator"
        operator_cmd = "kali-operator"

    # Paths derived from config
    loot_dir = os.path.abspath(os.path.join(config.WORK_DIR, "audit", "loot"))
    skills_dir = os.path.abspath(os.path.join(config.PROJECT_DIR, "skills"))
    seclists_path = env_vars.get("SECLISTS_PATH") or os.environ.get("SECLISTS_PATH")

    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        agent_id,
        "--label",
        "taskmaster.managed=true",
        "--label",
        f"taskmaster.agent_type={agent_type}",
        "--label",
        f"taskmaster.executor_id={agent_id}",
        "-v",
        f"{loot_dir}:/loot",  # Mount host audit/loot to container /loot
        "-v",
        f"{skills_dir}:/work/skills",  # Mount host skills to /work/skills
    ]

    if seclists_path:
        cmd.extend(["-v", f"{os.path.abspath(seclists_path)}:/usr/share/seclists"])

    novnc_url = None

    cmd.extend(
        [
            "-e",
            f"TASKMASTER_HOST={taskmaster_host}",
            "-e",
            f"TASKMASTER_PORT={taskmaster_port}",
            "-e",
            f"EXECUTOR_ID={agent_id}",
        ]
    )

    if proxy_url:
        cmd.extend(
            [
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

    if agent_type == "playwright":
        if interactive_browser:
            novnc_port = int(arguments.get("novnc_port") or _allocate_host_port())
            novnc_url = f"http://127.0.0.1:{novnc_port}/vnc.html"
            cmd.extend(
                [
                    "-p",
                    f"127.0.0.1:{novnc_port}:6080",
                    "-e",
                    "PLAYWRIGHT_HEADLESS=false",
                    "-e",
                    "PLAYWRIGHT_DEVTOOLS=true",
                    "-e",
                    "PLAYWRIGHT_INTERACTIVE=1",
                    "-e",
                    f"PLAYWRIGHT_INTERACTIVE_HOLD_MS={interactive_hold_ms}",
                    "-e",
                    f"PLAYWRIGHT_SESSION_URL={novnc_url}",
                ]
            )
        else:
            cmd.extend(
                [
                    "-e",
                    "PLAYWRIGHT_HEADLESS=true",
                    "-e",
                    "PLAYWRIGHT_DEVTOOLS=false",
                    "-e",
                    "PLAYWRIGHT_INTERACTIVE=0",
                ]
            )

    if target:
        cmd.extend(["-e", f"TARGET_SCOPE={target}"])

    if mission:
        cmd.extend(["-e", f"AGENT_MISSION={mission}"])

    cmd.append(image_name)
    if operator_cmd:
        cmd.append(operator_cmd)

    try:
        # Run container command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()

        return {
            "status": "success",
            "agent_id": agent_id,
            "container_id": container_id,
            "target": target,
            "interactive_browser": interactive_browser,
            "novnc_url": novnc_url,
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
