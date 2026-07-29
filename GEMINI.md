# GEMINI.md

Taskmaster no longer keeps a Gemini-specific operational guide. The content that used to live here (a hand-maintained skills catalog and a copy of the operator workflow) drifted from the code and duplicated the other guides, so it was collapsed into a single source of truth.

- **Operating Taskmaster** (driving the server during an assessment): **`OPERATIONAL_GUIDE.md`**. It is also served to any MCP client automatically — over the `initialize` handshake and the `get_operational_guide` tool — so you receive it without reading this file.
- **Developing the Taskmaster codebase**: **`CLAUDE.md`** (full guide) and **`AGENTS.md`** (short dev entry point).

If you drive Taskmaster with the Gemini CLI, point it at `OPERATIONAL_GUIDE.md`.
