import json
import os
import re
import subprocess

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
    tool_version_command = "httpx -version | tail -n 1 2>&1"
    auto_install_with_pdtm = True

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


class NucleiScan(BaseSkill):
    """nuclei scan of a web target (URL/host), bounded with partial-on-timeout.

    Standard HTTP nuclei — distinct from `mobile.MobileNucleiScan` (file protocol
    over decompiled smali). A full template run is the classic scan that never
    fits one window; shard it with `request_batch` by passing a `tags` /
    `templates` subset per shard (parallel across different targets, or
    `sequential` against one host). nuclei streams matches to the `-o` JSONL as it
    runs, so a `timeout` wall-clock returns the partial results found so far with
    `timed_out: true` instead of failing.

    kwargs: `target` (or `targets` list), `templates`, `tags`, `exclude_tags`,
    `severity`, `concurrency`, `template_timeout`, `timeout` (wall-clock, default
    600s), `extra_args`.
    """

    tool = "nuclei"
    tool_version_command = "nuclei -version 2>&1"
    auto_install_with_pdtm = True

    DEFAULT_TIMEOUT = 600

    def build_command(self, **kwargs) -> str:
        target = kwargs.get("target") or self.target
        targets = kwargs.get("targets")
        if not target and not targets:
            raise ValueError("target (URL/host) or targets list is required")

        self._timed_out = False
        self._wall_timeout = int(kwargs.get("timeout", self.DEFAULT_TIMEOUT))
        os.makedirs(self.loot_path, exist_ok=True)

        if targets:
            if isinstance(targets, str):
                targets = targets.splitlines()
            self._targets_file = os.path.join(self.loot_path, "nuclei_web_targets.txt")
            with open(self._targets_file, "w") as f:
                f.write("\n".join(t for t in targets if t))
            self._artifacts.append(self._targets_file)
            input_flag = f"-l {self._targets_file}"
            stem = "list"
        else:
            input_flag = f"-u {target}"
            stem = re.sub(r"[^A-Za-z0-9._-]", "_", target)[:60] or "target"

        self._output_file = os.path.join(self.loot_path, f"nuclei_web_{stem}.jsonl")
        parts = ["nuclei", input_flag, "-jsonl", "-o", self._output_file, "-silent"]

        # Sharding / scoping knobs (a subset per shard is how a full scan is split).
        for flag, key in (
            ("-t", "templates"),
            ("-tags", "tags"),
            ("-exclude-tags", "exclude_tags"),
            ("-severity", "severity"),
        ):
            val = kwargs.get(key)
            if val:
                parts += [flag, str(val)]
        if kwargs.get("concurrency"):
            parts += ["-c", str(int(kwargs["concurrency"]))]
        if kwargs.get("template_timeout"):
            parts += ["-timeout", str(int(kwargs["template_timeout"]))]
        if kwargs.get("extra_args"):
            parts.append(str(kwargs["extra_args"]))
        return " ".join(parts)

    def execute_shell(self, command, timeout=300):
        # Bounded wall-clock; on timeout keep the partial -o output rather than
        # erroring, so BaseSkill.run() still calls parse_output on what nuclei
        # streamed to disk before the deadline.
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._wall_timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired as e:
            self._timed_out = True
            return {
                "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
                "stderr": (e.stderr or "") if isinstance(e.stderr, str) else "",
                "exit_code": -1,
            }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        self._artifacts.append(self._output_file)
        results = []
        if os.path.exists(self._output_file):
            with open(self._output_file, errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    info = obj.get("info", {})
                    results.append(
                        {
                            "host": obj.get("host", ""),
                            "template_id": obj.get("template-id") or obj.get("templateID"),
                            "name": info.get("name"),
                            "severity": info.get("severity"),
                            "matched": obj.get("matched-at") or obj.get("matched"),
                        }
                    )
        if self._timed_out:
            self._errors.append(
                f"nuclei hit the {self._wall_timeout}s wall-clock; returning partial "
                "results. Shard by -tags/-t with request_batch, or raise 'timeout'."
            )
        return {
            "result_count": len(results),
            "results": results,
            "timed_out": self._timed_out,
        }
