# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Taskmaster is a stateful MCP (Model Context Protocol) server that orchestrates autonomous security assessments using specialized Kali Linux containers. AI agents (Claude Code, Codex, and other MCP clients) call MCP tools via JSON-RPC to queue tasks, spawn containers, and execute security skills.

## Commands

```bash
# Setup & Install
make dev          # Setup development environment
make install      # Install dependencies with UV (uv sync)

# Run
make start        # Start MCP server
make spawn        # Spawn interactive agent

# Build
make build              # Build all four agent containers (Kali + Playwright + Reporting + Mobile)
make build-kali         # Build only the Kali agent container (executors/Dockerfile)
make build-playwright   # Build only the Playwright agent container (executors/Dockerfile.playwright)
make build-reporting    # Build only the Reporting agent container (executors/Dockerfile.reporting)
make build-mobile       # Build only the Mobile agent container (executors/Dockerfile.mobile)

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
               dashboard/       # Web UI (api.py, agents.py, webapp.py, templates/, static/)
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
    /loot → runtime/loot/    # Shared volume for tool artifacts
    /reports → runtime/reports/  # Reporting agents only — rendered docx
    /session → runtime/session/ (read-only)  # User-supplied session material
```

**Runtime layout under `WORK_DIR` (defaults to cwd, override with `TASKMASTER_WORK_DIR`):**

```
<WORK_DIR>/
  runtime/           # single umbrella for runtime artifacts (gitignored)
    loot/            # tool outputs, captures
    reports/         # rendered docx deliverables
    audit/           # session_report.md, audit_log.jsonl
    state/           # executions.db (sqlite + WAL)
    session/         # user-supplied session material (input; mounted read-only at /session)
```

**Providing session material to agents (cookies, tokens, browser state) — how to pass it:** When a spawned agent needs user-supplied session material, **never paste its contents** into the mission, arguments, or any tool call — that leaks it into the execution request, audit log, and dashboard. Instead:
1. Keep the file in a folder inside the current engagement directory, e.g. `./session/` (for a browser login, name it `storage_state.json`; otherwise `cookies.json`, a token file, etc.).
2. On `spawn_agent`, set `session_dir` to the **absolute** path of that folder — resolve `./session` to an absolute path first, because the Taskmaster server's working directory is not the same as yours. It is mounted **read-only** at `/session` (with `SESSION_DIR=/session`).
3. Point the skill/mission at the container path (`/session/cookies.json`), never the host path or the contents.

Playwright/patchright/camoufox agents auto-load `/session/storage_state.json` into every browser context (via `BaseBrowserSkill._context_options`), so for a browser session steps 1–2 are all you need. If instead you run a Taskmaster server scoped to a single engagement (`TASKMASTER_WORK_DIR` set to that folder), you can skip `session_dir` and just drop files in `<WORK_DIR>/runtime/session/` (or override globally with `TASKMASTER_SESSION_DIR`).

**Execution flow:** `request_security_action` queues work only. The default next step is `spawn_agent`, unless you have already verified a compatible live worker for the same target and executor type. After provisioning, use `wait_for_completion` as the normal monitor path. Use `query_execution_status` mainly for debugging or recovery.

## Key Concepts

**State Machine:** Executions move through QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED, with CANCELLED as a terminal state for work whose dependency failed. Only one RUNNING execution per target (target locking via `state/storage.py`).

**Task dependencies:** `request_security_action` accepts `depends_on` (a list of prerequisite execution ids); a queued execution is withheld from the ready set until every prerequisite is COMPLETED, and a failed/cancelled prerequisite recursively cancels everything blocked on it. `request_playbook` expands a named or inline step sequence into such a chain. `request_batch` fans one skill out over many bounded shards (parallel across different targets; `sequential` chains same-target shards) for work too large for one execution window. See `state/state.py` (`dependencies_satisfied`, `cancel_blocked_dependents`), `policies/playbooks.py`, and `tools/request_batch.py`.

**Security Phases:** Policy enforces ordering: `reconnaissance → enumeration → exploitation → post_exploitation → reporting`. See `policies/state_policy.py`.

**Skills:** Each skill extends `skills/base.py:BaseSkill` with one tool per class. Subclasses implement `build_command(**kwargs) -> str` and `parse_output(stdout, stderr, exit_code) -> dict`. The concrete `run()` orchestrator produces a JSON envelope with `skill`, `target`, `status`, `findings`, `artifacts`, `errors`. The `findings` key is legacy wire format; in user-facing language these are execution observations. See `skills/TEMPLATE.md` for creating new skills.

**Execution Pathways:** The Kali operator (`executors/kali_operator.py`) supports exactly two `action_type` values: `"skill"` (imports and runs a skill class) and `"python"` (sandboxed `exec()`). The Playwright operator (`executors/playwright_operator.py`) supports `"playwright_skill"` (imports a `BaseBrowserSkill` subclass) and `"playwright"` (raw script run via the container's Python interpreter using `playwright.sync_api`/`async_api` — **Python only, not JavaScript**). The Reporting operator (`executors/report_operator.py`) supports `"report_skill"` (imports a `BaseReportSkill` subclass — e.g. `reporting.FindingDocxReport` — to render branded deliverables via docxtpl). The Mobile operator (`executors/mobile_operator.py`) supports `"mobile_skill"` (imports a `BaseMobileSkill` subclass — see `skills/mobile.py` — for headless static analysis of Android APKs via apktool/jadx/nuclei; Phase 1, no device required). All six pathways produce JSON envelope output.

**Browser engines:** The Playwright agent ships three engines selectable per-spawn via `browser_engine` on `spawn_agent`: `playwright` (vanilla Chromium), `patchright` (anti-detection Chromium drop-in, **default**), `camoufox` (fingerprint-hardened Firefox). `BaseBrowserSkill` dispatches at run time on the engine; skills written for vanilla Playwright work unchanged across all three.

**Reporting database:** Execution results are an event log; client-facing report findings are curated records in Taskmaster's reporting tables (`engagements`, `report_assets`, `findings`, `finding_evidence`, `finding_references`). The dashboard's Observations tab shows execution-derived results only. Manage report findings through MCP tools or the dashboard's **Engagements** hub / **Report Findings** page, then render from stored findings with `request_reporting_docx` or the dashboard's queue action (rendered DOCX deliverables are downloadable from an engagement's render-history panel). Do not build a pwndoc sync path or carry pwndoc-specific IDs into Taskmaster report findings.

**Threat model:** A per-engagement, evidence-grounded model in the reporting tables (`threat_models` + twelve `tm_*` entity tables: assumptions, roles, assets, terminal goals, attack surface, trust boundaries, attack paths, test objectives, existing/recommended mitigations, open questions, evidence notes). The orchestrating LLM synthesizes it from recon/enumeration data and findings; Taskmaster stores and displays it. Cross-references are ref strings the LLM authors (`AP-1` impacts `CA-1, CA-4`); every element is evidence-tagged (`EVIDENCED`/`USER-CONFIRMED`/`ASSUMED`/`OUT-OF-SCOPE`). Assemble inputs with `assemble_threat_model_context`, build with `create_threat_model` + `add_threat_model_entry`, export with `export_threat_model_markdown`. Rendered as tables in the engagement workspace. See the Threat modeling workflow in `OPERATIONAL_GUIDE.md`.

**Audit:** Every state transition is logged to `runtime/audit/audit_log.jsonl`. Final report at `runtime/audit/session_report.md`.

**Dashboard:** Served on its own loopback-only listener (default `127.0.0.1:5001`), separate from the agent-facing MCP endpoint; both answer `GET /healthz`. Request routing is table-driven in `dashboard/webapp.py` (`Router` + `DashboardHandler`). The **Overview** page is the landing view; the sidebar groups Operations and Reporting; the engagement scope selector filters the Overview/Executions/Observations/Targets/Agents views.

**MCP Tools (in `tools/`):** Core orchestration: `request_security_action`, `request_playbook`, `request_batch` (fan one skill over many bounded shards — see `tools/request_batch.py`), `spawn_agent`, `query_execution_status`, `fetch_execution_result`, `aggregate_executions` (merge a fan of shard results into one deduped view — see `tools/aggregate_executions.py`), `wait_for_completion`, `mark_execution_complete`, `claim_execution`, `start_execution`, `complete_execution`, `fail_execution`, `list_queued_executions`, `cleanup_agents`, `recover_execution`. Planning: `suggest_next_action` (read-only prioritized gaps), `get_operational_guide` (serves the operating manual). Reporting: `create_reporting_engagement`, `list_reporting_engagements`, `create_reporting_finding`, `get_reporting_finding`, `update_reporting_finding`, `add_reporting_finding_evidence`, `add_reporting_finding_reference`, `list_reporting_findings`, `request_reporting_docx`. Threat modeling: `assemble_threat_model_context`, `create_threat_model`, `list_threat_models`, `get_threat_model`, `update_threat_model`, `add_threat_model_entry`, `update_threat_model_entry`, `delete_threat_model_entry`, `export_threat_model_markdown`.

## Environment

Copy `.env.example` to `.env`. Key vars: `TASKMASTER_HOST`, `TASKMASTER_PORT`, `TASKMASTER_DASHBOARD_HOST`, `TASKMASTER_DASHBOARD_PORT`, `HTTP_PROXY`, `SECLISTS_PATH`. Default `TASKMASTER_HOST` is `host.docker.internal` (Docker Desktop on macOS/Windows); Linux users should set it to the `docker0` bridge IP. See `.env.example` for the full list.

## Operating Taskmaster (driving the server)

The workflow for *driving* Taskmaster during an assessment — the queue → provision → monitor → finalize loop, playbooks and dependencies, session material, the reporting database, and threat modeling — lives in one canonical guide: **`OPERATIONAL_GUIDE.md`**.

That guide is served to the orchestrating LLM over MCP (the `initialize` handshake surfaces its "Core loop"; the `get_operational_guide` tool returns the whole file), so it applies from any working directory and any MCP client — you do not need this repo checked out to receive it. Call `suggest_next_action` at session start (or whenever unsure) to orient.

This file (`CLAUDE.md`) is the **development** guide for editing the Taskmaster codebase. When changing operator workflow, edit `OPERATIONAL_GUIDE.md` — it is the single source of truth. `AGENTS.md` (Codex) and `GEMINI.md` are thin pointers to it, not copies to keep in sync.

See also `policies/agent_mission_template.md` (mission briefing structure) and `policies/note_taking_template.md` (`Findings.md` / `recon-data.md` structure).
