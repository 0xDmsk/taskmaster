"""
Mobile skill base — static analysis of Android application packages.

Phase 1 of the mobile worker: everything here runs headless in a plain
container with no device, no emulator, and no frida-server. The inputs are
files (an APK dropped in `/session` or `/loot`); the outputs are the standard
Taskmaster JSON envelope plus artifacts written to `/loot`.

`BaseMobileSkill` mirrors `BaseSkill` / `BaseReportSkill` so the executor
dispatcher and the dashboard treat mobile tasks like any other execution.
Unlike `BaseSkill`, a static-analysis skill is rarely a single shell command —
it typically decompiles, then parses files — so subclasses implement
`analyze(**kwargs) -> dict` (returning the `findings` payload) and drive their
own tool invocations through the `run_tool` helper.

Dynamic instrumentation (frida/objection, a device reached over the network) is
Phase 2 and will add a `BaseMobileDynamicSkill` alongside this one.
"""

import os
import re
import shutil
import subprocess
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone


def _safe_stem(path: str) -> str:
    """Filesystem-safe stem of a path's basename (for naming loot artifacts)."""
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    return re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "app"


class BaseMobileSkill(ABC):
    """Base class for headless mobile static-analysis skills.

    Subclasses set:
        tool: str                  — primary CLI tool (e.g. "apktool"); "" if pure-Python
        tool_version_command: str  — command to detect the tool version

    Subclasses implement:
        analyze(**kwargs) -> dict  — do the work, return the findings payload
    """

    tool: str = ""
    tool_version_command: str = ""

    def __init__(self, target: str | None = None):
        self.target = target
        self.loot_path = "/loot"
        self._artifacts: list[str] = []
        self._errors: list[str] = []

    @abstractmethod
    def analyze(self, **kwargs) -> dict:
        """Perform the analysis and return the findings dict.

        Implementations write artifacts to `/loot` via `save_artifact` /
        `save_json` / `track_artifact`, run tools via `run_tool`, and append
        soft failures to `self._errors`. Raise for hard failures — `run`
        turns the exception into an error envelope.
        """

    def run(self, **kwargs) -> dict:
        target = kwargs.pop("target", None) or self.target
        self.target = target
        self._artifacts = []
        self._errors = []

        started_at = datetime.now(timezone.utc).isoformat()
        skill_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        if skill_name.startswith("skills."):
            skill_name = skill_name[len("skills.") :]

        tool_error = self._ensure_tool_available()
        if tool_error:
            completed_at = datetime.now(timezone.utc).isoformat()
            return {
                "skill": skill_name,
                "target": target,
                "status": "error",
                "started_at": started_at,
                "completed_at": completed_at,
                "tool": self.tool,
                "tool_version": "",
                "command": "",
                "findings": {},
                "artifacts": [],
                "errors": [tool_error],
            }

        tool_version = self._detect_tool_version()

        findings: dict = {}
        status = "success"
        try:
            findings = self.analyze(**kwargs) or {}
        except (FileNotFoundError, ValueError) as e:
            # Bad/missing arguments and missing inputs are user errors — surface
            # a clean one-line message, not a stack trace.
            self._errors.append(str(e))
            status = "error"
        except Exception:
            self._errors.append(traceback.format_exc())
            status = "error"

        completed_at = datetime.now(timezone.utc).isoformat()
        return {
            "skill": skill_name,
            "target": target,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "tool": self.tool,
            "tool_version": tool_version,
            "command": "",
            "findings": findings,
            "artifacts": list(self._artifacts),
            "errors": list(self._errors),
        }

    # ------------------------------------------------------------------ #
    # Tool + input helpers                                                 #
    # ------------------------------------------------------------------ #

    def _ensure_tool_available(self) -> str | None:
        if not self.tool:
            return None
        if shutil.which(self.tool):
            return None
        return f"Required tool '{self.tool}' is not installed in this executor image."

    def _detect_tool_version(self) -> str:
        if not self.tool_version_command:
            return ""
        try:
            result = subprocess.run(
                self.tool_version_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in (result.stdout + result.stderr).splitlines():
                line = line.strip()
                if line:
                    return line
            return ""
        except Exception:
            return ""

    def run_tool(self, command: str, timeout: int = 600) -> dict:
        """Run a shell command and return stdout/stderr/exit_code (or an error)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired as e:
            # Flag timeouts distinctly so callers can salvage partial output a
            # tool streamed to disk before the deadline killed it.
            return {
                "error": f"Command timed out after {timeout}s",
                "timed_out": True,
                "timeout": timeout,
                "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
                "stderr": (e.stderr or "") if isinstance(e.stderr, str) else "",
            }
        except Exception as e:
            return {"error": str(e)}

    def resolve_apk(self, apk: str | None) -> str:
        """Resolve the APK to analyze.

        Order: (1) an explicit `apk` container path; (2) the target, if it is
        itself a file path; (3) auto-discovery of a single `.apk` under /session
        then /loot. Auto-discovery is what lets playbook steps run with empty
        arguments — drop one APK in the session mount and every step finds it.
        """
        return self._resolve_app_file(apk, "apk", "APK", "*.apk")

    def resolve_ipa(self, ipa: str | None) -> str:
        """Resolve the IPA to analyze. Mirrors `resolve_apk` for iOS input."""
        return self._resolve_app_file(ipa, "ipa", "IPA", "*.ipa")

    def _resolve_app_file(
        self, explicit: str | None, kwarg_name: str, label: str, glob_pattern: str
    ) -> str:
        if explicit:
            if os.path.isfile(explicit):
                return explicit
            raise FileNotFoundError(
                f"{label} not found at {explicit!r}. Drop it in the agent's /session mount "
                "(spawn with session_dir) or under /loot, and pass the container path."
            )
        if self.target and os.path.isfile(self.target):
            return self.target

        discovered = self._discover_file(glob_pattern, label, kwarg_name)
        if discovered:
            return discovered
        raise ValueError(
            f"No {kwarg_name!r} given and no {glob_pattern[1:]} found in /session or /loot. "
            f"Drop exactly one {label} in the agent's session mount (spawn with session_dir), "
            f"or pass arguments.{kwarg_name} with the container path."
        )

    def _discover_file(self, glob_pattern: str, label: str, kwarg_name: str) -> str | None:
        """Find a single file matching `glob_pattern` under /session then /loot.

        Returns the path when exactly one is present in the first location that
        has any; raises if a location is ambiguous (more than one) so the caller
        picks explicitly rather than us guessing.
        """
        import glob  # noqa: PLC0415

        session_dir = os.environ.get("SESSION_DIR", "/session")
        for base in (session_dir, self.loot_path):
            if not base or not os.path.isdir(base):
                continue
            hits = sorted(glob.glob(os.path.join(base, glob_pattern)))
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                raise ValueError(
                    f"Multiple {label}s in {base} "
                    f"({', '.join(os.path.basename(h) for h in hits)}); "
                    f"pass arguments.{kwarg_name} to choose one."
                )
        return None

    def resolve_source_dir(self, kwargs: dict, suffix: str) -> str:
        """Resolve a decompiled source tree for skills that scan one.

        Uniform contract across the tree-consuming skills: pass `source_dir` to
        reuse an existing decompiled tree (e.g. the `output_dir` from
        `ApkDecompile`), or pass `apk` to have this skill decode it first with
        apktool into `/loot/<apk>-<suffix>`. `source_dir` wins when both given.
        """
        source_dir = kwargs.get("source_dir")
        if source_dir:
            if not os.path.isdir(source_dir):
                raise FileNotFoundError(f"source_dir not found: {source_dir!r}")
            return source_dir

        apk = self.resolve_apk(kwargs.get("apk"))
        source_dir = os.path.join(self.loot_path, f"{_safe_stem(apk)}-{suffix}")
        if not shutil.which("apktool"):
            raise RuntimeError(
                "No source_dir given and apktool is unavailable to decompile the APK."
            )
        result = self.run_tool(f"apktool d -f -o {source_dir!r} {apk!r}")
        if not os.path.isdir(source_dir):
            raise RuntimeError(
                f"apktool decode failed: {result.get('stderr') or result.get('error')}"
            )
        self.track_artifact(source_dir)
        return source_dir

    # ------------------------------------------------------------------ #
    # Artifact helpers                                                     #
    # ------------------------------------------------------------------ #

    def track_artifact(self, path: str) -> str:
        """Record an already-written file/dir as an artifact."""
        self._artifacts.append(path)
        return path

    def save_artifact(self, filename: str, content: str) -> str:
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        self._artifacts.append(path)
        return path

    def save_json(self, filename: str, data: dict) -> str:
        import json  # noqa: PLC0415

        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._artifacts.append(path)
        return path
