#!/usr/bin/env python3
"""
Mobile Operator — headless mobile static-analysis executor for Taskmaster.

Claims tasks with `action_type == "mobile_skill"` and runs them through a
`BaseMobileSkill` subclass (see `skills/mobile.py`). Mirrors the report /
playwright operators' polling loop and action-type filter so kali, playwright,
reporting, and mobile agents coexist on one queue without stealing each other's
work.

Phase 1: static analysis only (apktool / jadx / nuclei over an APK file) — no
device, no emulator, no frida. Dynamic instrumentation (a device reached over
the network) is Phase 2 and will add a second action type here.
"""

import importlib
import json
import os
import socket
import time
import traceback
import urllib.error
import urllib.request

from targeting import targets_match

TASKMASTER_HOST = os.environ.get("TASKMASTER_HOST", "host.docker.internal")
TASKMASTER_PORT = int(os.environ.get("TASKMASTER_PORT", 5000))
EXECUTOR_ID = os.environ.get("EXECUTOR_ID", f"mobile-{socket.gethostname()}")
TARGET_SCOPE = os.environ.get("TARGET_SCOPE")
AGENT_MISSION = os.environ.get("AGENT_MISSION")

SUPPORTED_ACTION_TYPES = {"mobile_skill"}


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

    if action_type == "mobile_skill":
        return _execute_mobile_skill(payload)
    return {
        "status": "FAILED",
        "result": json.dumps(
            {
                "status": "error",
                "errors": [
                    f"Unknown action_type: {action_type}. "
                    f"Supported types: {', '.join(sorted(SUPPORTED_ACTION_TYPES))}"
                ],
            }
        ),
    }


def _execute_mobile_skill(payload):
    """Import and run a BaseMobileSkill subclass."""
    skill_name = payload.get("skill")
    skill_args = payload.get("arguments", {})
    target = payload.get("target")

    print(f"[*] Invoking Mobile Skill: {skill_name} with {skill_args}")

    try:
        # Format: 'mobile.ManifestScan'
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


def main_loop():
    print(f"[*] Mobile Operator started (ID: {EXECUTOR_ID})")
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

            # Only handle mobile tasks — leave everything else for other executors
            if action_type not in SUPPORTED_ACTION_TYPES:
                continue

            if TARGET_SCOPE and not targets_match(TARGET_SCOPE, target):
                continue

            claim = call_taskmaster(
                "claim_execution",
                {"execution_id": eid, "executor_id": EXECUTOR_ID},
            )
            if "error" in claim:
                continue

            print(f"[+] Claimed task {eid} ({action_type})")

            start = call_taskmaster(
                "start_execution",
                {"execution_id": eid, "executor_id": EXECUTOR_ID},
            )
            if "error" in start:
                print(f"[!] start_execution rejected for {eid}: {start['error']}")
                print(f"[!] Skipping {eid} — claim will be cleared by recovery")
                continue

            result_data = execute_action(task)

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
                    print(f"[!] complete_execution rejected for {eid}: {resp['error']}")
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
                    print(f"[!] fail_execution rejected for {eid}: {resp['error']}")
                else:
                    print(f"[-] Task {eid} failed")

        time.sleep(1)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[*] Shutting down.")
