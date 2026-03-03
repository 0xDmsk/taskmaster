import os
import requests
import re
from urllib.parse import urljoin
from skills.base import BaseSkill

class WebReconSkill(BaseSkill):
    """
    Web Reconnaissance Skill.
    Handles Tech Detection and Directory Fuzzing.
    """
    def run(self, action="all", target=None, wordlist=None, **kwargs):
        target = target or self.target
        if not target:
            return {"error": "Target required (http/https url)"}
        
        if not target.startswith("http"):
            target = f"http://{target}"

        results = {
            "target": target,
            "tech": {},
            "directories": []
        }

        if action in ["tech", "all"]:
            results["tech"] = self._detect_tech(target)
        
        if action in ["fuzz", "all"]:
            results["directories"] = self._fuzz_dirs(target, wordlist)

        return results

    def _detect_tech(self, url):
        print(f"[*] Detecting tech for {url}...")
        info = {
            "server": "Unknown",
            "powered_by": "Unknown",
            "generator": "Unknown",
            "title": "Unknown"
        }
        try:
            r = requests.get(url, timeout=10, verify=False)
            info["headers"] = dict(r.headers)
            info["server"] = r.headers.get("Server", "Unknown")
            info["powered_by"] = r.headers.get("X-Powered-By", "Unknown")
            
            # Simple body checks
            if "<title>" in r.text:
                m = re.search(r"<title>(.*?)</title>", r.text, re.IGNORECASE)
                if m:
                    info["title"] = m.group(1)
            
            if "content=\"WordPress" in r.text:
                info["generator"] = "WordPress"
            elif "Drupal" in r.text:
                info["generator"] = "Drupal"
            elif "Joomla" in r.text:
                info["generator"] = "Joomla"
                
        except Exception as e:
            info["error"] = str(e)
            
        return info

    def _fuzz_dirs(self, url, wordlist=None):
        print(f"[*] Fuzzing directories for {url}...")
        if not wordlist:
            wordlist = "/usr/share/seclists/Discovery/Web-Content/common.txt"
        
        if not os.path.exists(wordlist):
            return ["Wordlist not found"]

        output_file = f"/loot/ffuf_{url.replace(':', '').replace('/', '')}.json"
        
        # -mc: Match codes
        # -recursion: Depth 1 usually
        cmd = f"ffuf -u {url}/FUZZ -w {wordlist} -mc 200,301,302,403 -o {output_file} -of json -t 50 -s"
        self.execute_shell(cmd)
        
        found = []
        if os.path.exists(output_file):
            try:
                with open(output_file) as f:
                    data = json.load(f)
                    for res in data.get("results", []):
                        found.append({
                            "url": res.get("url"),
                            "status": res.get("status"),
                            "length": res.get("length")
                        })
            except:
                pass
        return found
