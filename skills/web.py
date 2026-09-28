import hashlib
import json
import os
import random
import re
import string
import subprocess
import time
from urllib.parse import quote

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
    `severity`, `concurrency`, `template_timeout`, `rate_limit` (requests/sec —
    the only backpressure lever against a slow/rate-limiting target; nuclei
    has no backoff of its own), `timeout` (wall-clock, default 600s),
    `extra_args`.
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
        if kwargs.get("rate_limit"):
            # Backpressure against a slow/rate-limiting target — nuclei has no
            # backoff of its own, so an unthrottled scan against a throttling
            # target just burns the wall-clock timeout instead of finishing.
            parts += ["-rate-limit", str(int(kwargs["rate_limit"]))]
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
                "timed_out": True,
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


# Header/body patterns redacted before evidence is written to /loot or handed
# to add_reporting_finding_evidence — a marker/control run against a live
# target routinely echoes session cookies, auth headers, or API keys back in
# the response.
_REDACT_HEADER_KEYS = {"authorization", "cookie", "set-cookie", "x-api-key", "x-auth-token"}
_REDACT_BODY_PATTERNS = [
    (
        re.compile(
            r'"(authorization|cookie|set-cookie|x-api-key|api[_-]?key)"\s*:\s*"[^"]*"', re.I
        ),
        r'"\1": "[REDACTED]"',
    ),
    (re.compile(r"(?im)^(Authorization|Cookie|Set-Cookie|X-Api-Key)\s*:\s*.+$"), r"\1: [REDACTED]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        "[REDACTED_JWT]",
    ),
]

_WAF_BLOCK_SIGNATURES = [
    re.compile(p, re.I)
    for p in (
        r"access denied",
        r"request blocked",
        r"attention required",
        r"mod_?security",
        r"security policy",
        r"blocked by the",
        r"request rejected",
        r"406 not acceptable",
        r"\bwaf\b",
    )
]

# WAF-evasion transforms tried against a blocked marker before giving up. The
# same technique is reapplied to the control so marker vs. control stays a
# fair, same-encoding comparison instead of "blocked payload vs. clean control".
_BYPASS_TECHNIQUES = {
    "double_url_encode": lambda v: quote(quote(v, safe=""), safe=""),
    "case_variation": lambda v: "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(v)),
    "html_entity": lambda v: "".join(f"&#{ord(c)};" if c in "'\"<>" else c for c in v),
    "null_byte": lambda v: v + "%00",
}


class StrikeVerify(BaseSkill):
    """Confirm-before-report: live baseline + marker + negative-control HTTP
    verification, so a scan hit becomes a verdict instead of a hypothesis
    that goes straight into `create_reporting_finding`.

    Sends three requests — an unmodified baseline, one with a unique marker
    injected, one with a benign lookalike "control" injected in the same
    position — and derives a verdict from reflection:

      marker reflected, control NOT reflected  -> confirmed        (real signal)
      marker reflected, control ALSO reflected -> false_positive   (benign echo)
      marker NOT reflected                     -> unconfirmed      (can't prove it)
      request failed / WAF-blocked, no bypass   -> blocked

    If the marker request is WAF-blocked (403/406/429 or a block-page
    signature), a small set of evasion variants (double-URL-encode, case
    variation, HTML-entity, null-byte) are tried before giving up; the same
    variant is then applied to the control for a fair comparison. Reflection
    is a substring check on the response body, so this proves *reflected*
    behavior only — it does not confirm blind/time-based/OOB findings, which
    need a different oracle (e.g. an interactsh callback) not implemented here.

    Runs as pure Python (curl_cffi, falling back to requests) rather than
    shelling out to one CLI tool — inspired by the baseline/marker/negative-
    control "verdict" pattern in github.com/shinthink/blitzstrike's STRIKE tier.

    kwargs: `url` (required; may contain a `{{MARKER}}` placeholder — in its
    absence the marker/control are appended as a `param` query arg, default
    "q"), `method` ("GET"/"POST", default "GET"), `data` (POST body template,
    same placeholder rule), `headers` (dict), `marker` / `control` (override
    the random tokens — each defaults to a fresh `TM<timestamp><random>` /
    `CT<timestamp><random>`), `timeout` (per-request seconds, default 15),
    `retries_on_block` (bool, default True).

    Evidence (redacted request/response summaries, hashed bodies) is written
    to `/loot` as an artifact — pass that `artifact_path` plus this
    execution's id straight into `add_reporting_finding_evidence` to attach
    the verdict to a report finding.
    """

    tool = ""
    tool_version_command = ""

    def build_command(self, **kwargs) -> str:
        url = kwargs.get("url") or self.target
        if not url:
            raise ValueError("url or target is required")
        self._verify_kwargs = dict(kwargs)
        self._verify_kwargs["url"] = url
        method = str(kwargs.get("method", "GET")).upper()
        # Not actually shelled out to — this string only feeds the envelope's
        # `command` field for the audit trail, matching BaseSkill's contract.
        return f"strike_verify {method} {url}"

    def execute_shell(self, command, timeout=300):
        try:
            result = self._run_verification(self._verify_kwargs)
        except Exception as e:  # noqa: BLE001
            return {"error": f"strike_verify failed: {e}"}
        return {"stdout": json.dumps(result), "stderr": "", "exit_code": 0}

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        if not stdout:
            return {}
        result = json.loads(stdout)
        evidence = result.pop("evidence")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", self._verify_kwargs["url"])[:60] or "target"
        artifact_path = self.save_json(f"strike_verify_{safe_name}_{int(time.time())}", evidence)
        result["evidence_artifact"] = artifact_path
        return result

    # -- verification -----------------------------------------------------

    def _run_verification(self, kwargs) -> dict:
        url = kwargs["url"]
        method = str(kwargs.get("method", "GET")).upper()
        data_template = kwargs.get("data")
        headers = dict(kwargs.get("headers") or {})
        param = kwargs.get("param", "q")
        marker = kwargs.get("marker") or self._random_token("TM")
        control = kwargs.get("control") or self._random_token("CT")
        timeout = float(kwargs.get("timeout", 15))
        allow_bypass = kwargs.get("retries_on_block", True)

        base_url, base_data = self._inject(url, data_template, "", param, blank=True)
        baseline = self._request(base_url, method, base_data, headers, timeout)

        marker_url, marker_data = self._inject(url, data_template, marker, param)
        marker_resp = self._request(marker_url, method, marker_data, headers, timeout)

        bypass_used = None
        if allow_bypass and self._is_waf_block(marker_resp):
            for technique, variant in self._bypass_variants(marker):
                cand_url, cand_data = self._inject(url, data_template, variant, param)
                resp = self._request(cand_url, method, cand_data, headers, timeout)
                if not self._is_waf_block(resp):
                    marker, marker_resp, bypass_used = variant, resp, technique
                    break

        control_value = self._apply_bypass(bypass_used, control)
        control_url, control_data = self._inject(url, data_template, control_value, param)
        control_resp = self._request(control_url, method, control_data, headers, timeout)

        marker_reflected = marker in marker_resp["body"]
        control_reflected = control_value in control_resp["body"]

        if marker_resp["status"] == 0:
            status = "blocked"
            reason = "Marker request failed (network error or timeout)."
        elif bypass_used is None and self._is_waf_block(marker_resp):
            status = "blocked"
            reason = "Marker request blocked by a WAF; no bypass variant got through."
        elif marker_reflected and not control_reflected:
            status = "confirmed"
            reason = "Marker reflected; benign control was not — real behavior, not an echo."
        elif marker_reflected and control_reflected:
            status = "false_positive"
            reason = "Marker and its benign control both reflected — indistinguishable from a normal echo."
        else:
            status = "unconfirmed"
            reason = "Marker was not reflected in the response; cannot confirm the hypothesis."

        return {
            "status": status,
            "reason": reason,
            "marker": marker,
            "control": control_value,
            "marker_reflected": marker_reflected,
            "control_reflected": control_reflected,
            "bypass_used": bypass_used,
            "baseline_status": baseline["status"],
            "marker_status": marker_resp["status"],
            "control_status": control_resp["status"],
            "evidence": {
                "url": url,
                "method": method,
                "marker": marker,
                "control": control_value,
                "bypass_used": bypass_used,
                "baseline": self._summarize(baseline),
                "marker_response": self._summarize(marker_resp),
                "control_response": self._summarize(control_resp),
            },
        }

    def _inject(self, url, data_template, value, param, blank=False):
        """Substitute `{{MARKER}}` in url/data, or append `param=value` to the
        URL's query string when neither contains the placeholder. `blank=True`
        (baseline) strips a placeholder to "" instead of leaving it literal."""
        has_placeholder = "{{MARKER}}" in url or (data_template and "{{MARKER}}" in data_template)
        new_url = url.replace("{{MARKER}}", value) if "{{MARKER}}" in url else url
        new_data = (
            data_template.replace("{{MARKER}}", value)
            if data_template and "{{MARKER}}" in data_template
            else data_template
        )
        if not has_placeholder and not blank:
            sep = "&" if "?" in url else "?"
            new_url = f"{url}{sep}{param}={quote(value, safe='')}"
        return new_url, new_data

    def _request(self, url, method, data, headers, timeout) -> dict:
        # Imported lazily: only the Kali executor image ships curl_cffi/requests
        # (see executors/Dockerfile), and this class must still import cleanly
        # wherever skills/web.py is loaded outside that container (server, tests).
        hdrs = {"User-Agent": "Mozilla/5.0 (compatible; TaskmasterStrikeVerify/1.0)"}
        hdrs.update(headers or {})
        try:
            try:
                from curl_cffi import requests as http_client

                extra = {"impersonate": "chrome124"}
            except ImportError:
                import requests as http_client

                extra = {}
            resp = http_client.request(
                method, url, data=data, headers=hdrs, timeout=timeout, allow_redirects=True, **extra
            )
            body = resp.text
            if len(body) > 300000:
                body = body[:300000]
            return {"status": resp.status_code, "body": body, "headers": dict(resp.headers)}
        except Exception as e:  # noqa: BLE001
            return {"status": 0, "body": str(e), "headers": {}}

    def _is_waf_block(self, resp) -> bool:
        if resp["status"] in (403, 406, 429):
            return True
        head = resp["body"][:4000]
        return any(p.search(head) for p in _WAF_BLOCK_SIGNATURES)

    def _bypass_variants(self, marker):
        return [
            (name, fn(marker)) for name, fn in _BYPASS_TECHNIQUES.items() if fn(marker) != marker
        ]

    def _apply_bypass(self, technique, value):
        fn = _BYPASS_TECHNIQUES.get(technique) if technique else None
        return fn(value) if fn else value

    def _summarize(self, resp) -> dict:
        body = self._redact_body(resp["body"])
        return {
            "status": resp["status"],
            "body_sha256": hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest(),
            "body_preview": body[:500],
            "headers": self._redact_headers(resp.get("headers", {})),
        }

    def _redact_body(self, text: str) -> str:
        for pattern, repl in _REDACT_BODY_PATTERNS:
            text = pattern.sub(repl, text)
        return text

    def _redact_headers(self, headers: dict) -> dict:
        return {
            k: ("[REDACTED]" if k.lower() in _REDACT_HEADER_KEYS else v) for k, v in headers.items()
        }

    def _random_token(self, prefix: str) -> str:
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        return f"{prefix}{int(time.time())}{suffix}"
