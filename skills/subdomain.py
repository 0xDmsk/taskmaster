import requests
import json
import os
from skills.base import BaseSkill

class SubdomainSkill(BaseSkill):
    """
    Subdomain Enumeration Skill.
    Combines passive sources (crt.sh) and active brute-force (gobuster).
    """
    def run(self, mode="passive", wordlist=None, **kwargs):
        target = self.target or kwargs.get("target")
        if not target:
            return {"error": "Target is required"}

        results = {
            "target": target,
            "mode": mode,
            "subdomains": []
        }

        # 1. Passive Recon (Always run as it's cheap)
        passive_subs = self._query_crtsh(target)
        results["subdomains"].extend(passive_subs)
        results["passive_count"] = len(passive_subs)

        # 2. Active Recon (Optional)
        if mode == "active":
            active_subs = self._run_gobuster(target, wordlist)
            # Merge unique
            new_subs = [s for s in active_subs if s not in results["subdomains"]]
            results["subdomains"].extend(new_subs)
            results["active_found"] = len(new_subs)

        # Save generic list
        self.save_artifact(f"subdomains_{target}.txt", "".join(results["subdomains"]))
        
        return results

    def _query_crtsh(self, domain):
        print(f"[*] Querying crt.sh for {domain}...")
        try:
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            # We rely on the proxy injected in the container if needed, 
            # but requests usually respects env vars automatically.
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                # Extract name_value and clean wildcards
                subs = set()
                for entry in data:
                    name = entry.get("name_value", "")
                    for sub in name.split():
                        if "*" not in sub:
                            subs.add(sub)
                return list(subs)
        except Exception as e:
            print(f"[!] crt.sh failed: {e}")
            return []
        return []

    def _run_gobuster(self, domain, wordlist=None):
        print(f"[*] Running gobuster DNS for {domain}...")
        # Default wordlist from SecLists if not provided
        if not wordlist:
            wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt"
        
        if not os.path.exists(wordlist):
            return []

        # 1. Check for wildcard DNS
        import uuid
        random_sub = f"check-{uuid.uuid4().hex[:8]}.{domain}"
        check = self.execute_shell(f"host {random_sub}")
        wildcard_ips = [line.split()[-1] for line in check.get("stdout", "").splitlines() if "has address" in line]
        
        # 2. Build gobuster command
        # --domain: target domain
        # -q: quiet, --no-error: hide errors
        cmd = f"gobuster dns --domain {domain} -w {wordlist} -q --no-error"
        if wildcard_ips:
            print(f"[!] Wildcard DNS detected ({', '.join(wildcard_ips)}). Enabling --wildcard mode.")
            cmd += " --wildcard"

        res = self.execute_shell(cmd)
        
        found_subs = []
        if res.get("stdout"):
            for line in res["stdout"].splitlines():
                if "Found:" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        found_subs.append(parts[1])

        # 3. Filter results if wildcard was detected
        if wildcard_ips and found_subs:
            print(f"[*] Filtering {len(found_subs)} results against wildcard IPs using parallel resolution...")
            refined = []
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def check_sub(sub):
                s_check = self.execute_shell(f"host {sub}")
                stdout = s_check.get("stdout", "")
                ips = [l.split()[-1] for l in stdout.splitlines() if "has address" in l]
                # Keep if it has an IP that is NOT one of the wildcard IPs
                if any(ip not in wildcard_ips for ip in ips):
                    return sub
                return None

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(check_sub, sub): sub for sub in found_subs}
                for future in as_completed(futures):
                    res = future.result()
                    if res:
                        refined.append(res)
            return refined

        return found_subs
