# Skill Creation Template

Use this template when creating new skills in the `skills/` directory.

## File Naming
- Filename: `[category].py` (e.g., `web.py`, `cloud.py`, `exploit.py`)
- Class Name: `[Action]Skill` (e.g., `FuzzingSkill`, `AuditSkill`)

## Code Template

```python
from skills.base import BaseSkill

class YourActionSkill(BaseSkill):
    """
    Description of what this skill does.
    """
    def run(self, **kwargs):
        # 1. Extract arguments
        # example: param = kwargs.get("param", "default")
        
        # 2. Logic (Shell commands or Python)
        # res = self.execute_shell("ls -la")
        
        # 3. Save artifacts if needed
        # self.save_artifact("output.txt", res["stdout"])
        
        # 4. Return structured dictionary
        return {
            "status": "success",
            "data": "..."
        }
```

## How to use dynamically:
1.  **Write File**: I (Gemini) write the `.py` file to the host's `skills/` directory.
2.  **Invoke**: Use `action_type: "skill"` with `skill: "[filename].[ClassName]"`.
3.  **Persistence**: Since `skills/` is a mounted volume, the spawned agent sees the new code immediately.
