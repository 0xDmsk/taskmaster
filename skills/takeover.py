import json
import os

from skills.base import BaseSkill


class NucleiTakeover(BaseSkill):
    """Subdomain takeover detection using nuclei with takeover templates."""

    tool = "nuclei"
    tool_version_command = "nuclei -version 2>&1"

    def build_command(self, **kwargs) -> str:
        targets = kwargs.get("targets") or kwargs.get("subdomains")
        target = kwargs.get("host") or self.target

        # Write target list to a temp file for nuclei -l
        if targets:
            if isinstance(targets, str):
                targets = targets.splitlines()
            self._targets_file = os.path.join(self.loot_path, "nuclei_targets.txt")
            os.makedirs(os.path.dirname(self._targets_file), exist_ok=True)
            with open(self._targets_file, "w") as f:
                f.write("\n".join(targets))
            self._artifacts.append(self._targets_file)
            input_flag = f"-l {self._targets_file}"
        elif target:
            input_flag = f"-u {target}"
        else:
            raise ValueError("targets list or target is required")

        self._output_file = os.path.join(self.loot_path, "nuclei_takeover.json")
        return f"nuclei {input_flag} -t http/takeovers/ " f"-jsonl -o {self._output_file} -silent"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        self._artifacts.append(self._output_file)
        vulnerable = []
        if os.path.exists(self._output_file):
            try:
                with open(self._output_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                vulnerable.append(
                                    {
                                        "host": entry.get("host", ""),
                                        "template_id": entry.get("template-id", ""),
                                        "name": entry.get("info", {}).get("name", ""),
                                        "severity": entry.get("info", {}).get("severity", ""),
                                        "matched_at": entry.get("matched-at", ""),
                                    }
                                )
                            except json.JSONDecodeError:
                                pass
            except OSError:
                self._errors.append(f"Failed to read {self._output_file}")

        return {
            "vulnerable_count": len(vulnerable),
            "vulnerable": vulnerable,
        }
