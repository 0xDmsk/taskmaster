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
make build              # Build all three agent containers (Kali + Playwright + Reporting)
make build-kali         # Build only the Kali agent container (executors/Dockerfile)
make build-playwright   # Build only the Playwright agent container (executors/Dockerfile.playwright)
make build-reporting    # Build only the Reporting agent container (executors/Dockerfile.reporting)

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

**State Machine:** Executions move through QUEUED → CLAIMED → RUNNING → COMPLETED/FAILED. Only one RUNNING execution per target (target locking via `state/storage.py`).

**Security Phases:** Policy enforces ordering: `reconnaissance → enumeration → exploitation → post_exploitation → reporting`. See `policies/state_policy.py`.

**Skills:** Each skill extends `skills/base.py:BaseSkill` with one tool per class. Subclasses implement `build_command(**kwargs) -> str` and `parse_output(stdout, stderr, exit_code) -> dict`. The concrete `run()` orchestrator produces a JSON envelope with `skill`, `target`, `status`, `findings`, `artifacts`, `errors`. The `findings` key is legacy wire format; in user-facing language these are execution observations. See `skills/TEMPLATE.md` for creating new skills.

**Execution Pathways:** The Kali operator (`executors/kali_operator.py`) supports exactly two `action_type` values: `"skill"` (imports and runs a skill class) and `"python"` (sandboxed `exec()`). The Playwright operator (`executors/playwright_operator.py`) supports `"playwright_skill"` (imports a `BaseBrowserSkill` subclass) and `"playwright"` (raw script run via the container's Python interpreter using `playwright.sync_api`/`async_api` — **Python only, not JavaScript**). The Reporting operator (`executors/report_operator.py`) supports `"report_skill"` (imports a `BaseReportSkill` subclass — e.g. `reporting.FindingDocxReport` — to render branded deliverables via docxtpl). All five pathways produce JSON envelope output.

**Browser engines:** The Playwright agent ships three engines selectable per-spawn via `browser_engine` on `spawn_agent`: `playwright` (vanilla Chromium), `patchright` (anti-detection Chromium drop-in, **default**), `camoufox` (fingerprint-hardened Firefox). `BaseBrowserSkill` dispatches at run time on the engine; skills written for vanilla Playwright work unchanged across all three.

**Reporting database:** Execution results are an event log; client-facing report findings are curated records in Taskmaster's reporting tables (`engagements`, `report_assets`, `findings`, `finding_evidence`, `finding_references`). The dashboard's Observations tab shows execution-derived results only. Manage report findings through MCP tools or the dashboard's **Engagements** hub / **Report Findings** page, then render from stored findings with `request_reporting_docx` or the dashboard's queue action (rendered DOCX deliverables are downloadable from an engagement's render-history panel). Do not build a pwndoc sync path or carry pwndoc-specific IDs into Taskmaster report findings.

**Audit:** Every state transition is logged to `runtime/audit/audit_log.jsonl`. Final report at `runtime/audit/session_report.md`.

**MCP Tools (in `tools/`):** Core orchestration: `request_security_action`, `spawn_agent`, `query_execution_status`, `fetch_execution_result`, `wait_for_completion`, `mark_execution_complete`, `claim_execution`, `start_execution`, `complete_execution`, `fail_execution`, `list_queued_executions`, `cleanup_agents`, `recover_execution`. Reporting: `create_reporting_engagement`, `list_reporting_engagements`, `create_reporting_finding`, `get_reporting_finding`, `update_reporting_finding`, `add_reporting_finding_evidence`, `add_reporting_finding_reference`, `list_reporting_findings`, `request_reporting_docx`.

## Environment

Copy `.env.example` to `.env`. Key vars: `TASKMASTER_HOST`, `TASKMASTER_PORT`, `HTTP_PROXY`, `SECLISTS_PATH`. Default `TASKMASTER_HOST` is `host.docker.internal` (Docker Desktop on macOS/Windows); Linux users should set it to the `docker0` bridge IP. See `.env.example` for the full list.

## Agent Operational Guide

This section applies whenever Claude is the orchestrating LLM driving Taskmaster (not just when editing source code in this repo). Sister files `AGENTS.md` (Codex) and `GEMINI.md` carry the same workflow — keep them in sync when changing it.

Standard workflow:
1. **Queue** — call `request_security_action`. When the work belongs to a known reporting engagement, pass its `engagement_id` so the execution is scoped to that engagement in the dashboard (create it first with `create_reporting_engagement`).
2. **Provision** — call `spawn_agent` unless you have already verified that a compatible live worker is running for the same target and executor type.
3. **Monitor** — call `wait_for_completion` to block until the execution reaches `COMPLETED` or `FAILED`.
4. **Finalize with analysis** — when the executor returns, call `mark_execution_complete` (or `complete_execution` / `fail_execution`) with an `interpretation` argument. This is a **markdown summary of what the raw output means** — notable observations, suspected misconfigurations, and the next investigative step. The dashboard renders it as the primary "Analysis" panel; the raw agent stdout sits behind a "See agent output" toggle. Match the level of detail you would surface to a human reviewer in the CLI.
5. **Record notes** — append novel captures to `recon-data.md` and promote anything worth triage to `Findings.md` in the current working directory (see Note-Taking Discipline below).
6. **Cleanup** — once a target assessment or phase is finalized, use `cleanup_agents` to decommission the worker fleet.

Do not assume that a `QUEUED` execution provisions a worker by itself. Use `query_execution_status` mainly for debugging, recovery, or explicit spot-checks — not as the default next step after queuing work.

### Bot-Protected Targets (Akamai, Cloudflare, Datadome…)

Fingerprint-based bot defenses block below the HTTP layer — `ERR_HTTP2_PROTOCOL_ERROR`, silent 403s, challenge pages, or a "Burp Suite" upstream-failure page rendered by Burp itself. Burp cannot help here: its own Java TLS stack is part of what's detected. Skip the proxy for these targets and lean on the agent's own logging.

Three-tier ladder — pick the **lowest tier** that yields the data you need:

1. **`curl_cffi`** — Kali agent, `action_type: "python"`. JS not needed (API probes, OAuth/redirect chasing, sitemap/robots, raw endpoint enum). Wraps a real Chrome/Firefox/Safari TLS+HTTP2 fingerprint around a `requests`-like API.
   ```python
   from curl_cffi import requests
   r = requests.get("https://target", impersonate="chrome124")
   ```
2. **Patchright** — Playwright agent with `browser_engine: "patchright"` (default). Anti-detection Chromium drop-in. First choice when JS is required.
3. **Camoufox** — Playwright agent with `browser_engine: "camoufox"`. Fingerprint-hardened custom Firefox. Escalate to it when Patchright is still getting flagged.

### Note-Taking Discipline

Every engagement should produce two living files in the **current working directory** (the assessment folder, not `audit/`):

- `Findings.md` — numbered `F-NNN` triage log. Each entry: **Where / Observation / Why it matters / Reproduction (when actionable) / Status / Recommendation**. Include informational and positive observations (e.g. "PII filter confirmed working against canary input"). Severity is a working estimate pending triage.
- `recon-data.md` — the raw data dossier behind the findings. Captures, tables, request/response shapes. Numbered sections that `Findings.md` cites via `§{section}`.

Create both files on first observation; do not wait for the user to ask. Append after every execution that produced novel data. When a hypothesis flips, add a dated follow-up paragraph rather than rewriting history. Full structure and worked examples in `policies/note_taking_template.md`.

### Interpretation field — required for good UX

Every finalization call should include `interpretation`. Without it the dashboard's observations panel only shows the raw executor stdout, which is often dense JSON or wall-of-text output. Markdown is supported (headers, `**bold**`, bullet lists, fenced code blocks, inline `code`, links). Aim for a few sentences to a few short paragraphs.

**Voice for `interpretation`, `Findings.md`, and `recon-data.md` prose:** pentester drafting working notes. Plain and concrete — cite the URL, header, parameter, or payload that proves the claim instead of abstract risk language. No scaremongering ("catastrophic", "trivially exploitable"), no marketing tone ("robust", "world-class"), no hedging fluff. Length follows the observation. Full tone contract in `policies/note_taking_template.md`.

### Reporting database workflow

Use the database-backed reporting tools for normal engagements:

1. Create an engagement with `create_reporting_engagement`.
2. Add settled report findings with `create_reporting_finding`; include `source_execution_id` when the finding is based on a Taskmaster execution.
3. Use `update_reporting_finding` for scalar edits. Use `add_reporting_finding_evidence` and `add_reporting_finding_reference` for proof material so edits do not silently replace the evidence trail.
4. Review stored findings with `get_reporting_finding` or `list_reporting_findings`; responses include `report_shape`.
5. Queue rendering with `request_reporting_docx`, then spawn `agent_type: "reporting"` and call `wait_for_completion`.

Dashboard equivalent: the **Engagements** hub (`/reporting/engagements`) is the primary surface — per-engagement severity/status rollups, an editable scope panel, a filtered findings list with inline status transitions, and a render-history panel with DOCX download links. The flat **Report Findings** page (`/reporting/findings`) covers cross-engagement create/edit, evidence and references, filtering, and queuing DOCX renders. The queue action still creates a normal Taskmaster execution; a `reporting` worker must claim it. A global **scope selector** (top of the dashboard, cookie-persisted) filters the stats bar plus the Executions and Observations lists to one engagement. Executions are bound to an engagement by an explicit `engagement_id`: pass `engagement_id` to `request_security_action` when queuing work for a known engagement (create the engagement first with `create_reporting_engagement`) so its metrics and lists are accurate. Reporting renders inherit the engagement automatically. Untagged or legacy executions can be assigned from the execution detail panel in the dashboard.

`request_reporting_docx` validates report-readiness and returns `not_ready` when required client-facing fields are missing. Fill the stored finding instead of bypassing that validation with a direct `report_skill` payload.

Current DOCX output renders the finding body fields plus references. Inline backticks and fenced code blocks are formatted as Word code. Markdown pipe tables are not converted into Word tables yet, and stored evidence records are not rendered into a separate evidence section.

### Writing report content (`report_skill` deliverables)

When creating or updating report findings, the stored fields become the **client-facing deliverable**. Translate, do not transcribe:

- Never carry over `F-NNN` triage IDs, `§N.M` recon section markers, or "(pending triage)" qualifiers from `Findings.md` / `recon-data.md`. Those files are internal working artifacts and are not shared with the client; referencing them in the deliverable creates confusion.
- Each field has one job: `description` = what was found (concrete), `impact` = why it matters in plain consequences, `proof_of_concept` = self-contained reproduction, `remediation` = specific actions.
- Plain, succinct language — a few short paragraphs per field, not pages of prose.
- Severity is a final value; strip working-estimate qualifiers.

Full style contract lives in the `skills/reporting.py` module docstring and `templates/README.md`.

See `AGENTS.md` for the canonical model-agnostic guide, `GEMINI.md` for the fuller worker-queue context, `policies/agent_mission_template.md` for mission briefing structure plus the interpretation wrap-up, and `policies/note_taking_template.md` for the `Findings.md` / `recon-data.md` structure.
