import subprocess
import json
import os
from skills.base import BaseSkill

class NetworkScanner(BaseSkill):
    """
    Intelligent Network Scanner Skill.
    Handles ping sweeps and service discovery.
    """
    def run(self, action="ping_sweep", target=None):
        target = target or self.target
        if not target:
            return {"error": "No target specified"}

        if action == "ping_sweep":
            return self._ping_sweep(target)
        elif action == "service_scan":
            return self._service_scan(target)
        else:
            return {"error": f"Unknown action: {action}"}

    def _ping_sweep(self, network):
        # fping is fast for sweeps
        cmd = f"fping -g {network} -a 2>/dev/null"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            hosts = result.stdout.splitlines()
            self.save_artifact(f"alive_hosts_{network.replace('/', '_')}.txt", result.stdout)
            return {"alive_count": len(hosts), "hosts": hosts}
        except Exception as e:
            return {"error": str(e)}

    def _service_scan(self, host):
        # Wrapper for common nmap service scan
        loot_file = f"nmap_{host.replace('.', '_')}.json"
        # We use the existing operator's ability to parse XML if we save it as XML
        # But for the 'Skill', we can also just return the results directly
        cmd = f"nmap -sV -T4 {host} -oX /loot/tmp_scan.xml"
        subprocess.run(cmd, shell=True, capture_output=True)
        
        # We can leverage the operator's parser or implement one here.
        # For now, let's just indicate success and the artifact location.
        return {
            "status": "completed",
            "host": host,
            "artifact": f"/loot/tmp_scan.xml",
            "note": "Operator will auto-parse the XML if returned"
        }
