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
import shutil
import subprocess
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone


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
        except FileNotFoundError as e:
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
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}

    def resolve_apk(self, apk: str | None) -> str:
        """Resolve and validate the APK path the caller passed.

        Callers pass a container path — an APK dropped in the read-only
        `/session` mount or written under `/loot`. We do not accept host paths.
        """
        candidate = apk or self.target
        if not candidate:
            raise ValueError("An 'apk' path (a container path, e.g. /session/app.apk) is required.")
        if not os.path.isfile(candidate):
            raise FileNotFoundError(
                f"APK not found at {candidate!r}. Drop it in the agent's /session mount "
                "(spawn with session_dir) or under /loot, and pass the container path."
            )
        return candidate

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
