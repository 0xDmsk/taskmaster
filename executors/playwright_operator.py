#!/usr/bin/env python3
"""
Playwright Operator — browser-capable executor for Taskmaster.

Handles two action types:
  playwright_skill — imports a BaseBrowserSkill subclass, calls run()
  playwright       — runs a raw Python/Playwright script in a subprocess

All other action types are ignored (left for other executors to claim).
"""
import importlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from targeting import targets_match

TASKMASTER_HOST = os.environ.get("TASKMASTER_HOST", "host.docker.internal")
TASKMASTER_PORT = int(os.environ.get("TASKMASTER_PORT", 5000))
EXECUTOR_ID = os.environ.get("EXECUTOR_ID", f"playwright-{socket.gethostname()}")
TARGET_SCOPE = os.environ.get("TARGET_SCOPE")
AGENT_MISSION = os.environ.get("AGENT_MISSION")
BROWSER_ENGINE = os.environ.get("BROWSER_ENGINE", "patchright")

SUPPORTED_ACTION_TYPES = {"playwright", "playwright_skill"}


def call_taskmaster(tool_name, arguments):
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
    payload = execution.get("request", {})
    action_type = payload.get("action_type")

    if action_type == "playwright_skill":
        return _execute_browser_skill(payload)
    elif action_type == "playwright":
        return _execute_playwright_script(payload)
    else:
        return {
            "status": "FAILED",
            "result": json.dumps(
                {
                    "status": "error",
                    "errors": [
                        f"Unknown action_type: {action_type}. "
                        f"Supported types: playwright, playwright_skill"
                    ],
                }
            ),
        }


def _execute_browser_skill(payload):
    """Import and run a BaseBrowserSkill subclass."""
    skill_name = payload.get("skill")
    skill_args = payload.get("arguments", {})
    target = payload.get("target")

    print(f"[*] Invoking Browser Skill: {skill_name} with {skill_args}")

    try:
        # Format: 'browser.SPACrawl'
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


def _execute_playwright_script(payload):
    """
    Run a raw Python/Playwright script in a subprocess.

    The script receives:
      - TARGET env var
      - LOOT_DIR env var
      - PLAYWRIGHT_ARGS env var (JSON string of extra arguments)

    The script is expected to print a single JSON envelope to stdout.
    Any non-JSON stdout is wrapped in a standard envelope under findings.stdout.
    """
    script = payload.get("script", "")
    target = payload.get("target")
    arguments = payload.get("arguments", {})

    print(f"[*] Executing Playwright script for target: {target}")

    env = os.environ.copy()
    env["TARGET"] = target or ""
    env["LOOT_DIR"] = "/loot"
    env["PLAYWRIGHT_ARGS"] = json.dumps(arguments)
    env["BROWSER_ENGINE"] = BROWSER_ENGINE

    script_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix="pw_task_", delete=False
        ) as f:
            f.write(script)
            script_file = f.name

        proc = subprocess.run(
            [sys.executable, script_file],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        # Try to parse stdout directly as the JSON envelope
        try:
            envelope = json.loads(stdout)
            if stderr:
                envelope.setdefault("errors", []).append(stderr)
            status = "COMPLETED" if envelope.get("status") != "error" else "FAILED"
            return {"status": status, "result": json.dumps(envelope, indent=2)}
        except json.JSONDecodeError:
            # Script didn't output a JSON envelope — wrap raw output
            envelope = {
                "skill": "playwright_script",
                "target": target,
                "status": "error" if proc.returncode != 0 else "success",
                "findings": {"stdout": stdout},
                "artifacts": [],
                "errors": [stderr] if stderr else [],
            }
            status = "FAILED" if proc.returncode != 0 else "COMPLETED"
            return {"status": status, "result": json.dumps(envelope, indent=2)}

    except subprocess.TimeoutExpired:
        envelope = {
            "skill": "playwright_script",
            "target": target,
            "status": "error",
            "findings": {},
            "artifacts": [],
            "errors": ["Script timed out after 300s"],
        }
        return {"status": "FAILED", "result": json.dumps(envelope, indent=2)}
    except Exception:
        envelope = {
            "skill": "playwright_script",
            "target": target,
            "status": "error",
            "findings": {},
            "artifacts": [],
            "errors": [traceback.format_exc()],
        }
        return {"status": "FAILED", "result": json.dumps(envelope, indent=2)}
    finally:
        if script_file and os.path.exists(script_file):
            os.unlink(script_file)


def main_loop():
    print(f"[*] Playwright Operator started (ID: {EXECUTOR_ID})")
    print(f"[*] Browser engine: {BROWSER_ENGINE}")
    if TARGET_SCOPE:
        print(f"[*] Target Scope restricted to: {TARGET_SCOPE}")
    if AGENT_MISSION:
        print(f"[*] Mission: {AGENT_MISSION}")
    print(f"[*] Connecting to Taskmaster at {TASKMASTER_HOST}:{TASKMASTER_PORT}")
    print(f"[*] Handling action types: {', '.join(sorted(SUPPORTED_ACTION_TYPES))}")

    while True:
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

            # Only handle playwright tasks — leave everything else for other executors
            if action_type not in SUPPORTED_ACTION_TYPES:
                continue

            if TARGET_SCOPE and not targets_match(TARGET_SCOPE, target):
                continue

            # Claim
            claim = call_taskmaster(
                "claim_execution",
                {"execution_id": eid, "executor_id": EXECUTOR_ID},
            )
            if "error" in claim:
                continue

            print(f"[+] Claimed task {eid} ({action_type})")

            # Start — bail out if the server rejects the transition
            # (e.g. another RUNNING execution is holding the target lock).
            # Without this check we'd silently run the action and then
            # fail every downstream state write, leaving the row stuck
            # at CLAIMED until the reaper sweeps it.
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

            # Execute
            result_data = execute_action(task)

            # Finish — surface any rejection so the wedge is visible in logs
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
