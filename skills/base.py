import json
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseSkill(ABC):
    """
    Base class for all Agent Skills.

    Subclasses must define:
        tool: str               — CLI tool name (e.g. "nmap", "ffuf")
        tool_version_command: str — command to detect version (e.g. "nmap --version")

    Subclasses must implement:
        build_command(**kwargs) -> str   — construct the CLI command
        parse_output(stdout, stderr, exit_code) -> dict — parse raw output into findings

    Optional:
        schema: dict | None — JSON Schema for the findings field
    """

    tool: str = ""
    tool_version_command: str = ""
    schema: dict | None = None
    auto_install_with_pdtm: bool = False
    pdtm_project: str | None = None

    def __init__(self, target=None):
        self.target = target
        self.loot_path = "/loot"
        self._artifacts: list[str] = []
        self._errors: list[str] = []

    @abstractmethod
    def build_command(self, **kwargs) -> str:
        """Construct the CLI command string to execute."""

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        """Parse raw command output into structured findings dict."""

    def run(self, **kwargs) -> dict:
        """
        Orchestrator: builds command, executes it, parses output,
        and returns a structured JSON envelope.
        """
        target = kwargs.pop("target", None) or self.target
        self.target = target
        self._artifacts = []
        self._errors = []

        started_at = datetime.now(timezone.utc).isoformat()
        skill_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        # Strip leading "skills." prefix if present for cleaner naming
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

        # Detect tool version
        tool_version = self._detect_tool_version()

        # Build the command
        try:
            command = self.build_command(**kwargs)
        except Exception as e:
            completed_at = datetime.now(timezone.utc).isoformat()
            return {
                "skill": skill_name,
                "target": target,
                "status": "error",
                "started_at": started_at,
                "completed_at": completed_at,
                "tool": self.tool,
                "tool_version": tool_version,
                "command": "",
                "findings": {},
                "artifacts": self._artifacts,
                "errors": [f"build_command failed: {e}"],
            }

        # Execute
        shell_result = self.execute_shell(command)

        if "error" in shell_result:
            completed_at = datetime.now(timezone.utc).isoformat()
            return {
                "skill": skill_name,
                "target": target,
                "status": "error",
                "started_at": started_at,
                "completed_at": completed_at,
                "tool": self.tool,
                "tool_version": tool_version,
                "command": command,
                "findings": {},
                "artifacts": self._artifacts,
                "errors": [shell_result["error"]],
            }

        stdout = shell_result.get("stdout", "")
        stderr = shell_result.get("stderr", "")
        exit_code = shell_result.get("exit_code", -1)

        # Parse output
        try:
            findings = self.parse_output(stdout, stderr, exit_code)
            status = "error" if exit_code != 0 and not findings else "success"
        except Exception as e:
            findings = {}
            status = "partial"
            self._errors.append(f"parse_output failed: {e}")

        if stderr.strip():
            self._errors.append(stderr.strip())

        completed_at = datetime.now(timezone.utc).isoformat()

        return {
            "skill": skill_name,
            "target": target,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "tool": self.tool,
            "tool_version": tool_version,
            "command": command,
            "findings": findings,
            "artifacts": list(self._artifacts),
            "errors": list(self._errors),
        }

    def _detect_tool_version(self) -> str:
        """Detect the tool version using tool_version_command."""
        if not self.tool_version_command:
            return ""
        try:
            result = subprocess.run(
                self.tool_version_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Return first non-empty line
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    return line
            return ""
        except Exception:
            return ""

    def _ensure_tool_available(self) -> str | None:
        """Ensure the declared tool exists, optionally installing it via PDTM."""
        if not self.tool:
            return None

        if shutil.which(self.tool):
            return None

        install_error = self._attempt_pdtm_install()
        if install_error:
            return install_error

        if shutil.which(self.tool):
            return None

        return f"Required tool '{self.tool}' is not installed in this executor image."

    def _attempt_pdtm_install(self) -> str | None:
        """Attempt to install the tool via PDTM when the skill opts into it."""
        if not self.auto_install_with_pdtm:
            return None

        if not shutil.which("pdtm"):
            return (
                f"Required tool '{self.tool}' is not installed in this executor image, "
                "and PDTM is unavailable for auto-install."
            )

        project = self.pdtm_project or self.tool
        try:
            result = subprocess.run(
                ["pdtm", "-duc", "-nc", "-i", project],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return f"PDTM timed out while installing '{project}'."
        except Exception as e:
            return f"PDTM failed while installing '{project}': {e}"

        if result.returncode == 0:
            return None

        details = "\n".join(
            part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
        )
        if details:
            return f"PDTM failed to install '{project}': {details}"
        return f"PDTM failed to install '{project}'."

    def execute_shell(self, command, timeout=300):
        """Helper to run shell commands safely."""
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

    def save_artifact(self, filename, content):
        """Saves raw text content to /loot and tracks it."""
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        self._artifacts.append(path)
        return path

    def save_json(self, filename, data):
        """Saves a dictionary as JSON to /loot and tracks it."""
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.loot_path, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._artifacts.append(path)
        return path
