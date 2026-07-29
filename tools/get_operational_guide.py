"""Serve the canonical operational guide to the orchestrating LLM.

OPERATIONAL_GUIDE.md is the single source of truth. Two channels deliver it
regardless of the LLM's working directory:

- ``core_instructions()`` returns the guide's marked "Core loop" section for the
  MCP ``initialize`` response (``instructions`` field), which clients inject into
  the model's context every session — so it must stay concise.
- ``handle_get_operational_guide`` returns the whole file on demand via the
  ``get_operational_guide`` MCP tool.
"""

import os

import config

GUIDE_PATH = os.path.join(config.PROJECT_DIR, "OPERATIONAL_GUIDE.md")

_CORE_START = "<!-- MCP-INSTRUCTIONS-START -->"
_CORE_END = "<!-- MCP-INSTRUCTIONS-END -->"

_FALLBACK = (
    "Taskmaster orchestration: queue work with request_security_action or "
    "request_playbook, provision with spawn_agent, monitor with wait_for_completion, "
    "then finalize with mark_execution_complete including an 'interpretation'. Call "
    "get_operational_guide for the full workflow."
)


def load_guide():
    """Return the full operational guide text, or a short fallback if missing."""
    try:
        with open(GUIDE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return _FALLBACK


def core_instructions():
    """Return the guide's marked core section for MCP initialize.instructions.

    Falls back to the full guide (if unmarked) or a short static string so the
    handshake always carries *something* usable.
    """
    text = load_guide()
    start = text.find(_CORE_START)
    end = text.find(_CORE_END)
    if start != -1 and end != -1 and end > start:
        return text[start + len(_CORE_START) : end].strip()
    return text if text != _FALLBACK else _FALLBACK


def handle_get_operational_guide(args):
    """MCP tool: return the full canonical operational guide."""
    return {"guide": load_guide()}
