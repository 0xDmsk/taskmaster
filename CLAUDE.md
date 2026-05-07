# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Taskmaster is a stateful MCP (Model Context Protocol) server that orchestrates autonomous security assessments using specialized Kali Linux containers. AI agents (e.g., Gemini) call MCP tools via JSON-RPC to queue tasks, spawn containers, and execute security skills.

## Commands

```bash
# Setup & Install
make dev          # Setup development environment
make install      # Install dependencies with UV (uv sync)

# Run
make start        # Start MCP server
make spawn        # Spawn interactive agent

# Build
make build              # Build both agent containers (Kali + Playwright)
make build-kali         # Build only the Kali agent container (executors/Dockerfile)
make build-playwright   # Build only the Playwright agent container (executors/Dockerfile.playwright)

# Test & Lint
make test         # Run pytest with coverage
make lint         # Run ruff linter
make format       # Format with black
make clean        # Clean runtime state (state/ and audit/ dirs)

# Direct UV commands
uv run pytest tests/path/to/test_file.py::test_name   # Run single test
uv run ruff check .
uv run black .
```

Code style: Black with 100-char line length, Ruff linting, Python 3.12+.

## Architecture

```
AI Agent (Gemini)
    │  JSON-RPC (MCP protocol, STDIO)
    ▼
server.py  ──► tools/           # MCP tool handlers
               dashboard/       # Web UI (api.py, agents.py, templates/, static/)
               state/state.py   # Execution lifecycle (QUEUED→CLAIMED→RUNNING→COMPLETED/FAILED)
               state/storage.py # SQLite persistence with WAL mode
               policies/state_policy.py  # Phase transition enforcement
               audit/audit_manager.py    # JSONL audit log + Markdown report
    │
    │  Docker/Podman
    ▼
Kali Linux container (executors/Dockerfile)
    executors/kali_operator.py  # Agent polls Taskmaster, executes skills
    skills/*.py                 # Security skills mounted at /work/skills
    /loot → audit/loot/         # Shared volume for artifacts
```

**Execution flow:** `request_security_action` queues work only. The default next step is `spawn_agent`, unless you have already verified a compatible live worker for the same target and executor type. After provisioning, use `wait_for_completion` as the normal monitor path. Use `query_execution_status` mainly for debugging or recovery.

## Key Concepts

**State Machine:** Executions move through QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED. Only one RUNNING execution per target (target locking via `state/storage.py`).

**Security Phases:** Policy enforces ordering: `reconnaissance → enumeration → exploitation → post_exploitation → reporting`. See `policies/state_policy.py`.

**Skills:** Each skill extends `skills/base.py:BaseSkill` with one tool per class. Subclasses implement `build_command(**kwargs) -> str` and `parse_output(stdout, stderr, exit_code) -> dict`. The concrete `run()` orchestrator produces a JSON envelope with `skill`, `target`, `status`, `findings`, `artifacts`, `errors`. See `skills/TEMPLATE.md` for creating new skills.

**Execution Pathways:** The Kali operator (`executors/kali_operator.py`) supports exactly two `action_type` values: `"skill"` (imports and runs a skill class) and `"python"` (sandboxed `exec()`). The Playwright operator (`executors/playwright_operator.py`) supports `"playwright_skill"` (imports a `BaseBrowserSkill` subclass) and `"playwright"` (raw script run via the container's Python interpreter using `playwright.sync_api`/`async_api` — **Python only, not JavaScript**). All four pathways produce JSON envelope output.

**Audit:** Every state transition is logged to `audit/audit_log.jsonl`. Final report at `audit/session_report.md`.

**MCP Tools (in `tools/`):** `request_security_action`, `spawn_agent`, `query_execution_status`, `fetch_execution_result`, `wait_for_completion`, `mark_execution_complete`, `claim_execution`, `start_execution`, `complete_execution`, `fail_execution`, `list_queued_executions`, `cleanup_agents`, `recover_execution`.

## Environment

Copy `.env.example` to `.env`. Key vars: `TASKMASTER_HOST`, `TASKMASTER_PORT`, `HTTP_PROXY`, `SECLISTS_PATH`. Default `TASKMASTER_HOST` is `host.docker.internal` (Docker Desktop on macOS/Windows); Linux users should set it to the `docker0` bridge IP. See `.env.example` for the full list.

## Agent Operational Guide

This section applies whenever Claude is the orchestrating LLM driving Taskmaster (not just when editing source code in this repo). Sister files `AGENTS.md` (Codex) and `GEMINI.md` carry the same workflow — keep them in sync when changing it.

Standard workflow:
1. **Queue** — call `request_security_action`.
2. **Provision** — call `spawn_agent` unless you have already verified that a compatible live worker is running for the same target and executor type.
3. **Monitor** — call `wait_for_completion` to block until the execution reaches `COMPLETED` or `FAILED`.
4. **Finalize with analysis** — when the executor returns, call `mark_execution_complete` (or `complete_execution` / `fail_execution`) with an `interpretation` argument. This is a **markdown summary of what the raw output means** — notable findings, suspected misconfigurations, and the next investigative step. The dashboard renders it as the primary "Analysis" panel; the raw agent stdout sits behind a "See agent output" toggle. Match the level of detail you would surface to a human reviewer in the CLI.
5. **Cleanup** — once a target assessment or phase is finalized, use `cleanup_agents` to decommission the worker fleet.

Do not assume that a `QUEUED` execution provisions a worker by itself. Use `query_execution_status` mainly for debugging, recovery, or explicit spot-checks — not as the default next step after queuing work.

### Interpretation field — required for good UX

Every finalization call should include `interpretation`. Without it the dashboard's findings panel only shows the raw executor stdout, which is often dense JSON or wall-of-text output. Markdown is supported (headers, `**bold**`, bullet lists, fenced code blocks, inline `code`, links). Aim for a few sentences to a few short paragraphs.

See `AGENTS.md` for the canonical model-agnostic guide, `GEMINI.md` for the fuller worker-queue context, and `policies/agent_mission_template.md` for mission briefing structure plus the interpretation wrap-up.
