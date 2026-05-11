#!/usr/bin/env python3
import importlib
import io
import json
import os
import socket
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from targeting import targets_match

# Configuration from environment or defaults
TASKMASTER_HOST = os.environ.get("TASKMASTER_HOST", "host.docker.internal")
TASKMASTER_PORT = int(os.environ.get("TASKMASTER_PORT", 5000))
EXECUTOR_ID = os.environ.get("EXECUTOR_ID", f"kali-{socket.gethostname()}")
TARGET_SCOPE = os.environ.get("TARGET_SCOPE")  # Optional: limit to a specific target
AGENT_MISSION = os.environ.get("AGENT_MISSION")  # Optional: mission description


def configure_proxychains():
    """
    Configures /etc/proxychains4.conf to point at $HTTP_PROXY so that tools
    invoked via `proxychains4` flow through the same upstream as the
    HTTP_PROXY-aware clients (curl, requests, etc.). Skips silently if no
    proxy is configured.
    """
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not http_proxy:
        return

    parsed = urllib.parse.urlparse(http_proxy)
    proxy_host = parsed.hostname
    proxy_port = parsed.port or 8080
    if not proxy_host:
        print(f"[!] Could not parse HTTP_PROXY={http_proxy!r}; leaving proxychains4 unconfigured")
        return

    conf_path = "/etc/proxychains4.conf"
    if not os.path.exists(conf_path):
        return

    try:
        with open(conf_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        in_proxy_list = False
        for line in lines:
            if line.strip().startswith("[ProxyList]"):
                new_lines.append(line)
                in_proxy_list = True
                new_lines.append(f"http {proxy_host} {proxy_port}\n")
                continue

            if in_proxy_list:
                if (
                    line.strip()
                    and not line.strip().startswith("#")
                    and not line.strip().startswith("[")
                ):
                    continue

            new_lines.append(line)

        with open(conf_path, "w") as f:
            f.writelines(new_lines)
        print(f"[*] Configured proxychains4 to use {proxy_host}:{proxy_port}")
    except Exception as e:
        print(f"[!] Failed to configure proxychains4: {e}")


def call_taskmaster(tool_name, arguments):
    """
    Calls a Taskmaster tool via HTTP POST.
    """
    url = f"http://{TASKMASTER_HOST}:{TASKMASTER_PORT}/mcp"
    request = {
        "type": "tool_call",
        "tool": tool_name,
        "arguments": arguments,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(request).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response = json.loads(resp.read().decode())
        return response.get("result", {"error": "No result in response"})
    except Exception as e:
        return {"error": f"Connection failed: {str(e)}"}


def execute_action(execution):
    """
    Two-pathway execution dispatcher:
    1. skill   — import skill class, call run(), return JSON envelope
    2. python  — sandboxed exec() with output capture
    """
    payload = execution.get("request", {})
    action_type = payload.get("action_type")

    if action_type == "skill":
        return _execute_skill(payload)
    elif action_type == "python":
        return _execute_python_sandbox(payload)
    else:
        return {
            "status": "FAILED",
            "result": json.dumps(
                {
                    "status": "error",
                    "errors": [
                        f"Unknown action_type: {action_type}. " f"Supported types: skill, python"
                    ],
                }
            ),
        }


def _execute_skill(payload):
    """Import and run a skill class, returning the JSON envelope."""
    skill_name = payload.get("skill")
    skill_args = payload.get("arguments", {})
    target = payload.get("target")

    print(f"[*] Invoking Skill: {skill_name} with {skill_args}")

    try:
        # Format: 'network.NmapScan'
        module_path, class_name = skill_name.rsplit(".", 1)
        module = importlib.import_module(f"skills.{module_path}")
        skill_class = getattr(module, class_name)

        skill_instance = skill_class(target=target)
        result_data = skill_instance.run(**skill_args)

        status = "COMPLETED" if result_data.get("status") != "error" else "FAILED"
        return {
            "status": status,
            "result": json.dumps(result_data, indent=2),
        }
    except Exception:
        error_envelope = {
            "skill": skill_name,
            "target": target,
            "status": "error",
            "findings": {},
            "artifacts": [],
            "errors": [traceback.format_exc()],
        }
        return {
            "status": "FAILED",
            "result": json.dumps(error_envelope, indent=2),
        }


def _execute_python_sandbox(payload):
    """Run Python code in a sandboxed exec() and wrap output in an envelope."""
    command = payload.get("command", "")
    target = payload.get("target")

    print(f"[*] Executing Python sandbox: {command[:50]}...")

    try:
        f_stdout = io.StringIO()
        f_stderr = io.StringIO()

        with redirect_stdout(f_stdout), redirect_stderr(f_stderr):
            exec_globals = {"__builtins__": __builtins__}
            exec(command, exec_globals)

        output = f_stdout.getvalue()
        errors = f_stderr.getvalue()

        envelope = {
            "skill": "python_sandbox",
            "target": target,
            "status": "success",
            "findings": {"stdout": output},
            "artifacts": [],
            "errors": [errors] if errors.strip() else [],
        }
        return {
            "status": "COMPLETED",
            "result": json.dumps(envelope, indent=2),
        }
    except Exception:
        envelope = {
            "skill": "python_sandbox",
            "target": target,
            "status": "error",
            "findings": {},
            "artifacts": [],
            "errors": [traceback.format_exc()],
        }
        return {
            "status": "FAILED",
            "result": json.dumps(envelope, indent=2),
        }


def main_loop():
    configure_proxychains()
    print(f"[*] Kali Operator started (ID: {EXECUTOR_ID})")
    if TARGET_SCOPE:
        print(f"[*] Target Scope restricted to: {TARGET_SCOPE}")
    if AGENT_MISSION:
        print(f"[*] Mission: {AGENT_MISSION}")
    print(f"[*] Connecting to Taskmaster at {TASKMASTER_HOST}:{TASKMASTER_PORT}")

    while True:
        # 1. Poll for work
        args = {}
        if TARGET_SCOPE:
            args["target"] = TARGET_SCOPE

        queued = call_taskmaster("list_queued_executions", args)

        if "error" in queued:
            print(f"[!] Polling error: {queued['error']}")
            time.sleep(5)
            continue

        executions = queued.get("executions", [])
        if not executions:
            time.sleep(2)
            continue

        for task in executions:
            eid = task["execution_id"]
            target = task.get("target")
            action_type = task.get("request", {}).get("action_type")

            # Leave playwright tasks for the playwright operator
            if action_type in ("playwright", "playwright_skill"):
                continue

            # Filter by TARGET_SCOPE if set
            if TARGET_SCOPE and not targets_match(TARGET_SCOPE, target):
                continue

            # 2. Claim
            claim = call_taskmaster(
                "claim_execution",
                {"execution_id": eid, "executor_id": EXECUTOR_ID},
            )

            if "error" in claim:
                continue

            print(f"[+] Claimed task {eid}")

            # 3. Start — bail out if the server rejects the transition
            #    (e.g. another RUNNING execution is holding the target lock).
            #    Without this check we'd silently run the action and then
            #    fail every downstream state write, leaving the row stuck
            #    at CLAIMED until the reaper sweeps it.
            start = call_taskmaster(
                "start_execution",
                {"execution_id": eid, "executor_id": EXECUTOR_ID},
            )
            if "error" in start:
                print(
                    f"[!] start_execution rejected for {eid}: {start['error']}"
                )
                print(
                    f"[!] Skipping {eid} — claim will be cleared by recovery"
                )
                continue

            # 4. Execute
            result_data = execute_action(task)

            # 5. Finish — surface any rejection so the wedge is visible in logs
            if result_data["status"] == "COMPLETED":
                resp = call_taskmaster(
                    "complete_execution",
                    {
                        "execution_id": eid,
                        "executor_id": EXECUTOR_ID,
                        "result": result_data["result"],
                    },
                )
                if "error" in resp:
                    print(
                        f"[!] complete_execution rejected for {eid}: "
                        f"{resp['error']}"
                    )
                else:
                    print(f"[+] Task {eid} completed")
            else:
                resp = call_taskmaster(
                    "fail_execution",
                    {
                        "execution_id": eid,
                        "executor_id": EXECUTOR_ID,
                        "error_info": result_data["result"],
                    },
                )
                if "error" in resp:
                    print(
                        f"[!] fail_execution rejected for {eid}: "
                        f"{resp['error']}"
                    )
                else:
                    print(f"[-] Task {eid} failed")

        time.sleep(1)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[*] Shutting down.")
