import json
import os
import subprocess
import traceback
from abc import ABC, abstractmethod

class BaseSkill(ABC):
    """
    Base class for all Agent Skills.
    Skills should return a dictionary that can be JSON serialized.
    """
    def __init__(self, target=None):
        self.target = target
        self.loot_path = "/loot"

    @abstractmethod
    def run(self, **kwargs):
        pass

    def execute_shell(self, command, timeout=300):
        """Helper to run shell commands safely."""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}

    def save_artifact(self, filename, content):
        """Saves raw text content to /loot."""
        path = os.path.join(self.loot_path, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def save_json(self, filename, data):
        """Saves a dictionary as JSON to /loot."""
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.loot_path, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path
