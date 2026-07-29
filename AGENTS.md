# AGENTS.md

Repository-local guidance for agentic coding assistants (Codex and others) **developing** the Taskmaster codebase.

Taskmaster is a stateful MCP server that orchestrates security assessments across Kali / Playwright / Reporting containers. This file is a short dev entry point; the two authoritative documents are:

- **`CLAUDE.md`** — the full development guide: architecture, key concepts, execution pathways, the runtime layout, and the complete MCP tool map. Read it before making non-trivial changes.
- **`OPERATIONAL_GUIDE.md`** — how to *drive* Taskmaster during an assessment (the queue → provision → monitor → finalize loop, playbooks and dependencies, session material, reporting database, threat modeling). This is the single source of truth for operator workflow, and it is served to any MCP client over the `initialize` handshake and the `get_operational_guide` tool — so it applies even when this repo isn't checked out. When operator workflow changes, edit **that** file, not this one.

## Commands

```bash
make dev          # Set up the development environment
make install      # uv sync
make start        # Start the MCP server (+ dashboard on 127.0.0.1:5001)
make test         # pytest with coverage
make lint         # ruff
make format       # black
uv run pytest tests/path/to/test_file.py::test_name   # Run a single test
```

Code style: Black with a 100-char line length, Ruff linting, Python 3.12+.

## Where things live

- `server.py` — MCP JSON-RPC server + dual HTTP listeners (agent-facing MCP endpoint; loopback dashboard).
- `tools/` — one module per MCP tool handler.
- `state/` — execution lifecycle (`state.py`), SQLite persistence (`storage.py`).
- `policies/` — phase-transition policy, playbooks, mission/note-taking templates.
- `dashboard/` — web UI (`webapp.py` router, `api.py`, `agents.py`, Jinja2 `templates/`, `static/`).
- `skills/` — `base.py` (CLI skills), `browser.py` (Playwright), `reporting.py` (docx).
- `executors/` — Dockerfiles + operator scripts for the Kali / Playwright / Reporting agents.

Keep tests green (`make test`) and lint clean (`make lint`) before finishing. When you add or change a tool, update its schema in `server.py` and the tool map in `CLAUDE.md`.
