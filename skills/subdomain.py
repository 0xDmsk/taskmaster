import json
import os

from skills.base import BaseSkill


class GobusterDns(BaseSkill):
    """Active subdomain brute-force using gobuster DNS mode."""

    tool = "gobuster"
    tool_version_command = "gobuster version 2>&1"

    def build_command(self, **kwargs) -> str:
        domain = kwargs.get("domain") or self.target
        if not domain:
            raise ValueError("domain or target is required")
        wordlist = kwargs.get(
            "wordlist", "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt"
        )
        self._domain = domain
        return f"gobuster dns --domain {domain} -w {wordlist} -q --no-error"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        found = []
        for line in stdout.splitlines():
            if "Found:" in line:
                parts = line.split()
                if len(parts) >= 2:
                    found.append(parts[1])

        if found:
            self.save_artifact(f"gobuster_dns_{self._domain}.txt", "\n".join(found))
        return {
            "domain": self._domain,
            "subdomains_found": len(found),
            "subdomains": found,
        }


class SubfinderEnum(BaseSkill):
    """Passive subdomain enumeration using subfinder."""

    tool = "subfinder"
    tool_version_command = "subfinder -version 2>&1"
    auto_install_with_pdtm = True

    def build_command(self, **kwargs) -> str:
        domain = kwargs.get("domain") or self.target
        if not domain:
            raise ValueError("domain or target is required")
        self._domain = domain
        safe_name = domain.replace(".", "_")
        self._output_file = f"/loot/subfinder_{safe_name}.json"
        return f"subfinder -d {domain} -o {self._output_file} -oJ -silent"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        self._artifacts.append(self._output_file)
        subdomains = []
        if os.path.exists(self._output_file):
            try:
                with open(self._output_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                host = entry.get("host", "")
                                if host:
                                    subdomains.append(host)
                            except json.JSONDecodeError:
                                # Plain text output fallback
                                subdomains.append(line)
            except OSError:
                self._errors.append(f"Failed to read {self._output_file}")
        else:
            # Subfinder may output to stdout instead
            subdomains = [s.strip() for s in stdout.splitlines() if s.strip()]

        return {
            "domain": self._domain,
            "subdomains_found": len(subdomains),
            "subdomains": subdomains,
        }
