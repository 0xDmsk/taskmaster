import json
import sys
import os
from tools.request_security_action import handle_request
from tools.query_execution_status import handle_query_execution_status
from tools.claim_execution import handle_claim_execution
from tools.start_execution import handle_start_execution
from tools.complete_execution import handle_complete_execution
from tools.fail_execution import handle_fail_execution

def run_test():
    print("Running granular workflow test...")
    
    # Clean state
    if os.path.exists("state/executions.json"):
        os.remove("state/executions.json")

    # 1. Request Recon
    print("\n1. Requesting Recon...")
    payload = {
        "agent_role": "recon",
        "phase": "reconnaissance",
        "target": "10.0.0.1",
        "action_type": "network_scan",
        "tool": "nmap",
        "command": "nmap -sV 10.0.0.1",
        "justification": "Initial recon to identify open ports and services for security assessment...................",
        "expected_output": "XML output"
    }
    result = handle_request(payload)
    print("Result:", result)
    execution_id = result["execution_id"]

    # 2. Claim
    print("\n2. Claiming Execution...")
    res = handle_claim_execution({
        "execution_id": execution_id,
        "executor_id": "agent-1"
    })
    print("Claim Result:", res)
    assert res.get("status") == "CLAIMED"

    # 3. Start
    print("\n3. Starting Execution...")
    res = handle_start_execution({
        "execution_id": execution_id,
        "executor_id": "agent-1"
    })
    print("Start Result:", res)
    assert res.get("status") == "RUNNING"

    # 4. Fail (Testing failure path)
    print("\n4. Failing Execution (Testing FAILED state)...")
    res = handle_fail_execution({
        "execution_id": execution_id,
        "executor_id": "agent-1",
        "error_info": "Network timeout"
    })
    print("Fail Result:", res)
    assert res.get("status") == "FAILED"

    # 5. New Request for same target
    print("\n5. Requesting Recon again (Should be allowed)...")
    result2 = handle_request(payload)
    print("Result 2:", result2)
    execution_id2 = result2["execution_id"]

    # 6. Complete Path
    handle_claim_execution({"execution_id": execution_id2, "executor_id": "agent-1"})
    handle_start_execution({"execution_id": execution_id2, "executor_id": "agent-1"})
    print("\n6. Completing Execution...")
    res = handle_complete_execution({
        "execution_id": execution_id2,
        "executor_id": "agent-1",
        "result": "Scan successful this time"
    })
    print("Complete Result:", res)
    assert res.get("status") == "COMPLETED"

    print("\nAll granular lifecycle tests passed.")

if __name__ == "__main__":
    run_test()