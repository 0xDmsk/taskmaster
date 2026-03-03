import subprocess
import json
import os
import sys

def handle_cleanup_agents(arguments):
    """
    Stops and removes kali-agent containers based on filters.
    Filters:
      - target: Only cleanup agents assigned to this target (via TARGET_SCOPE env)
      - agent_id: Cleanup a specific agent
      - all: Cleanup all kali-agent containers (default: False)
      - state: Filter by 'running' or 'stopped' (default: all states)
    """
    target = arguments.get("target")
    agent_id = arguments.get("agent_id")
    cleanup_all = arguments.get("all", False)
    state_filter = arguments.get("state")

    # 1. List containers to find matches
    try:
        # Get all containers with name starting with kali-agent
        cmd_ls = ["container", "ls", "-a"]
        result = subprocess.run(cmd_ls, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        if not lines:
            return {"status": "success", "message": "No containers found", "cleaned": []}

        # Header: ID, IMAGE, OS, ARCH, STATE, ADDR, CPUS, MEMORY
        # Find column indices (approximation based on headers)
        header = lines[0]
        id_idx = 0
        state_idx = header.find("STATE")

        to_cleanup = []
        
        # Skip header
        for line in lines[1:]:
            parts = line.split()
            if not parts: continue
            
            c_id = parts[0]
            if not c_id.startswith("kali-agent"):
                continue

            # Basic match
            match = False
            if cleanup_all:
                match = True
            elif agent_id and c_id == agent_id:
                match = True
            elif target:
                # We need to inspect to see the TARGET_SCOPE env var
                inspect_cmd = ["container", "inspect", c_id]
                inspect_res = subprocess.run(inspect_cmd, capture_output=True, text=True)
                if target in inspect_res.stdout: # Rough check for target in env/config
                    match = True
            
            # Apply state filter if matched
            if match and state_filter:
                # Extract state from fixed position or split logic
                c_state = "unknown"
                if "running" in line.lower(): c_state = "running"
                elif "stopped" in line.lower(): c_state = "stopped"
                
                if c_state != state_filter.lower():
                    match = False

            if match:
                to_cleanup.append(c_id)

        if not to_cleanup:
            return {"status": "success", "message": "No matching agents found for cleanup", "cleaned": []}

        # 2. Stop and Remove
        cleaned = []
        for cid in to_cleanup:
            # Stop if running
            subprocess.run(["container", "stop", cid], capture_output=True)
            # Remove
            subprocess.run(["container", "rm", cid], capture_output=True)
            cleaned.append(cid)

        return {
            "status": "success",
            "message": f"Cleaned up {len(cleaned)} agents",
            "cleaned": cleaned
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        args = json.loads(sys.argv[1])
        print(json.dumps(handle_cleanup_agents(args)))
    else:
        print(json.dumps({"error": "No arguments provided"}))
