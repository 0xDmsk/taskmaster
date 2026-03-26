# Skill Creation Template

Use this template when creating new skills in the `skills/` directory.

## Design Rules

1. **One tool per skill class** — each skill wraps exactly one CLI tool
2. **Two abstract methods** — `build_command()` constructs the CLI command, `parse_output()` parses results into structured findings
3. **JSON envelope** — `run()` is concrete and assembles a standard envelope automatically

## File Naming
- Filename: `[category].py` (e.g., `web.py`, `cloud.py`, `network.py`)
- Class Name: `[Tool][Action]` (e.g., `NmapScan`, `FfufFuzz`, `GobusterDns`)

## Code Template

```python
from skills.base import BaseSkill


class YourToolAction(BaseSkill):
    """
    Description: what this skill does and which tool it wraps.
    """

    tool = "toolname"                          # CLI tool name
    tool_version_command = "toolname --version" # version detection command

    def build_command(self, **kwargs) -> str:
        """Construct the exact CLI command to run."""
        host = kwargs.get("host") or self.target
        if not host:
            raise ValueError("host or target is required")
        return f"toolname --option {host}"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        """Parse raw command output into a structured findings dict."""
        # Use self.save_artifact() / self.save_json() to persist files
        # Use self._errors.append() to record non-fatal errors
        # Use self._artifacts.append() for files created by the tool itself
        return {
            "key": "parsed data here"
        }
```

## JSON Envelope (returned by `run()`)

```json
{
  "skill": "category.YourToolAction",
  "target": "10.0.0.1",
  "status": "success | error | partial",
  "started_at": "2024-01-01T00:00:00+00:00",
  "completed_at": "2024-01-01T00:00:05+00:00",
  "tool": "toolname",
  "tool_version": "1.0.0",
  "command": "toolname --option 10.0.0.1",
  "findings": { ... },
  "artifacts": ["/loot/output.json"],
  "errors": []
}
```

## How to use dynamically
1. **Write File**: Create or edit the `.py` file in the `skills/` directory.
2. **Invoke**: Use `action_type: "skill"` with `skill: "category.ClassName"` (e.g., `"network.NmapScan"`).
3. **Arguments**: Pass kwargs via the `arguments` field (e.g., `{"host": "10.0.0.1", "ports": "80,443"}`).
4. **Persistence**: Since `skills/` is a mounted volume, the spawned agent sees the new code immediately.
