import json
import os

from skills.base import BaseSkill


class FfufFuzz(BaseSkill):
    """Directory fuzzing using ffuf."""

    tool = "ffuf"
    tool_version_command = "ffuf -V 2>&1"

    def build_command(self, **kwargs) -> str:
        url = kwargs.get("url") or self.target
        if not url:
            raise ValueError("url or target is required")
        if not url.startswith("http"):
            url = f"http://{url}"

        wordlist = kwargs.get("wordlist", "/usr/share/seclists/Discovery/Web-Content/common.txt")
        match_codes = kwargs.get("match_codes", "200,301,302,403")
        threads = kwargs.get("threads", 50)

        safe_name = url.replace(":", "").replace("/", "")
        self._output_file = f"/loot/ffuf_{safe_name}.json"

        return (
            f"ffuf -u {url}/FUZZ -w {wordlist} "
            f"-mc {match_codes} -o {self._output_file} -of json -t {threads} -s"
        )

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        self._artifacts.append(self._output_file)
        found = []
        if os.path.exists(self._output_file):
            try:
                with open(self._output_file) as f:
                    data = json.load(f)
                for res in data.get("results", []):
                    found.append(
                        {
                            "url": res.get("url"),
                            "status": res.get("status"),
                            "length": res.get("length"),
                        }
                    )
            except (json.JSONDecodeError, OSError):
                self._errors.append(f"Failed to parse {self._output_file}")
        return {
            "directories_found": len(found),
            "directories": found,
        }


class HttpxDetect(BaseSkill):
    """Technology detection using httpx."""

    tool = "httpx"
    auto_install_with_pdtm = True
    tool_version_command = "httpx -version 2>&1"

    def build_command(self, **kwargs) -> str:
        url = kwargs.get("url") or self.target
        if not url:
            raise ValueError("url or target is required")
        if not url.startswith("http"):
            url = f"http://{url}"

        safe_name = url.replace(":", "").replace("/", "")
        self._output_file = f"/loot/httpx_{safe_name}.json"

        return (
            f"httpx -u {url} -title -tech-detect -status-code "
            f"-server -follow-redirects -json -o {self._output_file}"
        )

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        self._artifacts.append(self._output_file)
        if os.path.exists(self._output_file):
            try:
                with open(self._output_file) as f:
                    # httpx outputs one JSON object per line
                    results = []
                    for line in f:
                        line = line.strip()
                        if line:
                            results.append(json.loads(line))
                if results:
                    entry = results[0]
                    return {
                        "url": entry.get("url", ""),
                        "status_code": entry.get("status_code"),
                        "title": entry.get("title", ""),
                        "server": entry.get("webserver", ""),
                        "technologies": entry.get("tech", []),
                    }
            except (json.JSONDecodeError, OSError):
                self._errors.append(f"Failed to parse {self._output_file}")
        return {}
