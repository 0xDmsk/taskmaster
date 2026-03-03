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
make build        # Build Kali agent container (executors/Dockerfile)

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
               state/state.py   # Execution lifecycle (QUEUED→CLAIMED→RUNNING→COMPLETED/FAILED)
               state/storage.py # JSON file persistence with fcntl locking
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

**Execution flow:** `request_security_action` → `spawn_agent` → `claim_execution` → skill runs → `complete_execution` → session report generated.

## Key Concepts

**State Machine:** Executions move through QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED. Only one RUNNING execution per target (target locking via `state/storage.py`).

**Security Phases:** Policy enforces ordering: `reconnaissance → enumeration → exploitation → post_exploitation → reporting`. See `policies/state_policy.py`.

**Skills:** Each skill extends `skills/base.py:BaseSkill`. Skills save JSON/XML artifacts to `/loot` (auto-parsed into execution results). See `skills/TEMPLATE.md` for creating new skills.

**Audit:** Every state transition is logged to `audit/audit_log.jsonl`. Final report at `audit/session_report.md`.

**MCP Tools (in `tools/`):** `request_security_action`, `spawn_agent`, `query_execution_status`, `fetch_execution_result`, `wait_for_completion`, `mark_execution_complete`, `claim_execution`, `start_execution`, `complete_execution`, `fail_execution`, `list_queued_executions`, `cleanup_agents`, `recover_execution`.

## Environment

Copy `.env.example` to `.env`. Key vars: `TASKMASTER_HOST`, `TASKMASTER_PORT`, `HTTP_PROXY`, `SECLISTS_PATH`. Networking defaults are pre-configured for macOS Docker (`192.168.64.1`). See `.env.example` for the full list.

## Agent Operational Guide

See `GEMINI.md` for the full worker-queue model and mission briefing template at `policies/agent_mission_template.md`.
