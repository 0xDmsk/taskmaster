#!/usr/bin/env python3
import json
import subprocess
import sys
import socket
import time
import traceback
import os
import urllib.request
import urllib.error

# Configuration from environment or defaults
TASKMASTER_HOST = os.environ.get("TASKMASTER_HOST", "localhost")
TASKMASTER_PORT = int(os.environ.get("TASKMASTER_PORT", 5000))
EXECUTOR_ID = os.environ.get("EXECUTOR_ID", f"kali-{socket.gethostname()}")
TARGET_SCOPE = os.environ.get("TARGET_SCOPE") # Optional: limit this agent to a specific target
AGENT_MISSION = os.environ.get("AGENT_MISSION") # Optional: mission description/prompt

def configure_proxychains():
    """
    Configures /etc/proxychains4.conf to use the host proxy.
    """
    proxy_host = os.environ.get("TASKMASTER_HOST", "192.168.64.1")
    proxy_port = "8888" # Based on user's host proxy configuration
    
    conf_path = "/etc/proxychains4.conf"
    if not os.path.exists(conf_path):
        return

    try:
        # Simple configuration: remove existing proxy lines and add the host proxy
        with open(conf_path, "r") as f:
            lines = f.readlines()
        
        new_lines = []
        in_proxy_list = False
        for line in lines:
            if line.strip().startswith("[ProxyList]"):
                new_lines.append(line)
                in_proxy_list = True
                # Add our host proxy right after the header
                new_lines.append(f"http {proxy_host} {proxy_port}\n")
                continue
            
            if in_proxy_list:
                # Skip existing proxy entries
                if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("["):
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

def parse_nmap_xml(xml_path):
    """
    Parses Nmap XML output into a structured JSON dictionary.
    """
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        hosts = []
        for host in root.findall('host'):
            ip = ""
            addr_elem = host.find('address')
            if addr_elem is not None:
                ip = addr_elem.get('addr')
            
            status_elem = host.find('status')
            status = status_elem.get('state') if status_elem is not None else "unknown"
            if status != 'up':
                continue
                
            ports = []
            ports_elem = host.find('ports')
            if ports_elem is not None:
                for port in ports_elem.findall('port'):
                    p = {
                        "id": int(port.get('portid')),
                        "protocol": port.get('protocol'),
                        "state": port.find('state').get('state'),
                        "service": "unknown"
                    }
                    service = port.find('service')
                    if service is not None:
                        p["service"] = service.get('name', 'unknown')
                        p["version"] = service.get('version', '')
                        p["product"] = service.get('product', '')
                    
                    ports.append(p)
            
            hosts.append({
                "ip": ip,
                "ports": ports
            })
            
        return hosts
    except Exception as e:
        return {"error": f"Failed to parse Nmap XML: {str(e)}"}

def execute_action(execution):
    """
    The core 'Smart Operator' logic.
    Handles standard shell commands and Python execution (Coderunner style).
    """
    payload = execution.get("request", {})
    action_type = payload.get("action_type")
    command = payload.get("command")
    
    print(f"[*] Executing {action_type}: {command[:50]}...")

    # Coderunner logic: If action_type is 'analysis' or 'python', we run it as python
    if action_type in ["analysis", "python"]:
        try:
            # Capture stdout/stderr for the python execution
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            f_stdout = io.StringIO()
            f_stderr = io.StringIO()
            
            with redirect_stdout(f_stdout), redirect_stderr(f_stderr):
                # We use a shared global/local dict for the exec
                exec_globals = {"__builtins__": __builtins__}
                exec(command, exec_globals)
            
            output = f_stdout.getvalue()
            errors = f_stderr.getvalue()
            
            return {
                "status": "COMPLETED",
                "result": f"STDOUT:\n{output}\nSTDERR:\n{errors}"
            }
        except Exception:
            return {
                "status": "FAILED",
                "result": f"Python Execution Failed:\n{traceback.format_exc()}"
            }
    
    # Skill Execution Logic
    elif action_type == "skill":
        skill_name = payload.get("skill")
        skill_args = payload.get("arguments", {})
        
        print(f"[*] Invoking Skill: {skill_name} with {skill_args}")
        
        try:
            # Dynamically import the skill
            # Format: 'network.NetworkScanner'
            module_path, class_name = skill_name.rsplit(".", 1)
            import importlib
            module = importlib.import_module(f"skills.{module_path}")
            skill_class = getattr(module, class_name)
            
            # Initialize and run
            skill_instance = skill_class(target=payload.get("target"))
            result_data = skill_instance.run(**skill_args)
            
            return {
                "status": "COMPLETED",
                "result": json.dumps(result_data, indent=2)
            }
        except Exception:
            return {
                "status": "FAILED",
                "result": f"Skill Execution Failed:\n{traceback.format_exc()}"
            }

    # Standard Shell Logic
    else:
        # Track files in /loot before execution
        loot_path = "/loot"
        before_files = set(os.listdir(loot_path)) if os.path.exists(loot_path) else set()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600 # 10 minute timeout
            )
            
            status = "COMPLETED" if result.returncode == 0 else "FAILED"
            output = f"Exit Code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            
            # Detect new files in /loot
            after_files = set(os.listdir(loot_path)) if os.path.exists(loot_path) else set()
            new_files = after_files - before_files
            
            structured_results = {}
            artifacts = []

            for filename in new_files:
                full_path = os.path.join(loot_path, filename)
                artifacts.append(full_path)
                
                # Auto-parse JSON
                if filename.endswith(".json"):
                    try:
                        with open(full_path, "r") as f:
                            structured_results[filename] = json.load(f)
                    except:
                        pass
                
                # Auto-parse Nmap XML
                elif filename.endswith(".xml") and "nmap" in command:
                    parsed_nmap = parse_nmap_xml(full_path)
                    structured_results[filename] = parsed_nmap

            if structured_results:
                output += f"\n\n[STRUCTURED_DATA]:\n{json.dumps(structured_results, indent=2)}"
            
            if artifacts:
                output += f"\n\n[ARTIFACTS]:\n" + "\n".join(artifacts)
            
            return {
                "status": status,
                "result": output
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "FAILED",
                "result": "Execution timed out after 600 seconds"
            }
        except Exception:
            return {
                "status": "FAILED",
                "result": f"Shell Execution Failed:\n{traceback.format_exc()}"
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

            # Filter by TARGET_SCOPE if set
            if TARGET_SCOPE and target != TARGET_SCOPE:
                continue
            
            # 2. Claim
            claim = call_taskmaster("claim_execution", {
                "execution_id": eid,
                "executor_id": EXECUTOR_ID
            })
            
            if "error" in claim:
                # Likely already claimed by someone else
                continue
                
            print(f"[+] Claimed task {eid}")
            
            # 3. Start
            call_taskmaster("start_execution", {
                "execution_id": eid,
                "executor_id": EXECUTOR_ID
            })
            
            # 4. Execute
            result_data = execute_action(task)
            
            # 5. Finish
            if result_data["status"] == "COMPLETED":
                call_taskmaster("complete_execution", {
                    "execution_id": eid,
                    "executor_id": EXECUTOR_ID,
                    "result": result_data["result"]
                })
                print(f"[✓] Task {eid} completed")
            else:
                call_taskmaster("fail_execution", {
                    "execution_id": eid,
                    "executor_id": EXECUTOR_ID,
                    "error_info": result_data["result"]
                })
                print(f"[✗] Task {eid} failed")
        
        time.sleep(1)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[*] Shutting down.")