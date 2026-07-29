# Taskmaster Operational Guide

Canonical, distilled guide for the LLM orchestrating Taskmaster during a security
assessment. This is the single source of truth for *how to drive the tools*. The
server surfaces the **Core loop** section below via the MCP `initialize`
handshake, and serves this whole file through the `get_operational_guide` tool —
so it reaches you regardless of which directory you launched in. This is the
single source of truth for operator workflow; the repo's `CLAUDE.md` is the
separate guide for *developing* the Taskmaster codebase.

<!-- MCP-INSTRUCTIONS-START -->
## Core loop

You are orchestrating Taskmaster: a stateful MCP server that runs security work
in Kali / Playwright / reporting containers. You call tools; workers execute.
The intelligence and methodology are yours.

To orient at the start of a session (or any time you're unsure what's next), call
`suggest_next_action` — it returns the current state's prioritized gaps.

Standard cycle for every unit of work:
1. **Queue** — `request_security_action` for a single action, or `request_playbook`
   for an ordered sequence (see below). Pass `engagement_id` when the work belongs
   to a known reporting engagement.
2. **Provision** — `spawn_agent`, unless you've already verified a compatible live
   worker for the same target and executor type.
3. **Monitor** — `wait_for_completion` (blocks until COMPLETED/FAILED). Use
   `query_execution_status` only for debugging/recovery.
4. **Finalize with analysis** — `mark_execution_complete` (or `complete_execution`
   / `fail_execution`) **with an `interpretation`** — a markdown summary of what the
   raw output *means*, notable observations, and the next step. Without it the
   dashboard shows only raw stdout. This is required for good UX.
5. **Take notes** — maintain two living files in your **current working directory**
   (the assessment folder): `Findings.md` (numbered `F-NNN` triage log:
   Where / Observation / Why it matters / Reproduction / Status / Recommendation)
   and `recon-data.md` (the raw data dossier the findings cite via `§section`).
   Create them on first observation; append after every execution with novel data.
6. **Cleanup** — `cleanup_agents` once a phase/target is done.

Queuing does **not** provision a worker. `request_security_action` returns QUEUED;
you must spawn (or reuse) an agent before anything runs.

**Playbooks & dependencies** (prefer over hand-sequencing): `request_playbook`
expands a named playbook (call it bare to list them) or an inline `steps` list into
a dependency chain for one target — each step runs only after the previous COMPLETES,
and the chain is cancelled if a step fails. For manual control, pass `depends_on`
(a list of prerequisite execution_ids) to `request_security_action`.

**Phase order is enforced** per target: reconnaissance → enumeration → exploitation
→ post_exploitation → reporting. Only one RUNNING execution per target.

**Bot-protected targets** (Akamai/Cloudflare/Datadome — `ERR_HTTP2_PROTOCOL_ERROR`,
silent 403, challenge pages): skip any intercepting proxy and climb the *lowest tier
that works*: (1) `curl_cffi` in a `python` action (no JS needed) → (2) Playwright with
`browser_engine: "patchright"` (default, JS needed) → (3) `browser_engine: "camoufox"`
(when patchright is still flagged).

**Voice** for `interpretation`, `Findings.md`, `recon-data.md`: pentester working
notes — plain, concrete, cite the URL/header/param/payload that proves the claim. No
scaremongering, no marketing tone, no hedging fluff.

Call `get_operational_guide` for the full workflow: reporting database, threat
modeling, session material, and report-writing style.
<!-- MCP-INSTRUCTIONS-END -->

## Providing session material (cookies, tokens, browser state)

Never paste session material into a mission, arguments, or any tool call — it leaks
into the request, audit log, and dashboard. Instead: keep the file in a folder (e.g.
`./session/`, browser state as `storage_state.json`), pass `session_dir` (the
**absolute** host path) on `spawn_agent`; it mounts read-only at `/session`. Point the
skill at the container path (`/session/cookies.json`), never the host path or contents.
Playwright/patchright/camoufox agents auto-load `/session/storage_state.json` into every
browser context.

## Execution pathways

- **Kali** operator: `action_type` `"skill"` (imports a `BaseSkill` subclass) or
  `"python"` (sandboxed `exec()`; `curl_cffi` + `httpx[http2]` available).
- **Playwright** operator: `"playwright_skill"` (a `BaseBrowserSkill` subclass) or
  `"playwright"` (raw Python using `playwright.sync_api`/`async_api` — **Python, not JS**).
  Engines per-spawn via `browser_engine`: `patchright` (default), `playwright`, `camoufox`.
- **Reporting** operator: `"report_skill"` (a `BaseReportSkill` subclass, e.g.
  `reporting.FindingDocxReport`) to render branded DOCX.

Every pathway emits a JSON envelope: `skill`, `target`, `status`, `findings`,
`artifacts`, `errors`. (`findings` is the legacy wire key; user-facing these are
execution *observations*, distinct from curated report findings.)

## Reporting database workflow

Execution results are an event log; client-facing findings are curated records in the
reporting tables. Flow:
1. `create_reporting_engagement`.
2. `create_reporting_finding` (include `source_execution_id` when based on an execution).
3. `update_reporting_finding` for scalar edits; `add_reporting_finding_evidence` /
   `add_reporting_finding_reference` for proof (don't overwrite the evidence trail).
4. Review with `get_reporting_finding` / `list_reporting_findings`.
5. `request_reporting_docx` → spawn a `reporting` agent → `wait_for_completion`.
   It returns `not_ready` when required client-facing fields are missing — fill the
   stored finding rather than bypassing the check.

**Report-writing style** (stored fields ARE the client deliverable — translate, don't
transcribe): never carry over `F-NNN` IDs, `§N.M` markers, or "(pending triage)". Each
field has one job — `description` (what was found), `impact` (plain consequences),
`proof_of_concept` (self-contained repro), `remediation` (specific actions). Severity is
final, not a working estimate. `category` is a fixed enum — pick the closest, `TBD` when
unknown; off-list values are coerced to `Other`.

## Threat modeling (evidence-grounded, two-pass)

A per-engagement artifact you synthesize; Taskmaster stores/renders/exports it.
**First pass:** `assemble_threat_model_context(engagement_id)` for DB-side evidence;
read the engagement's `Findings.md` / `recon-data.md`; `create_threat_model`; build with
`add_threat_model_entry` (roles, assets, terminal goals, attack surface, trust
boundaries, then a *small* set of high-quality attack paths; a `test_objective` for every
High/Critical path; split existing vs recommended mitigations; record assumptions and
open questions). Tag every element `EVIDENCED` (link an execution_id/finding_id) /
`USER-CONFIRMED` / `ASSUMED` / `OUT-OF-SCOPE` — never present an assumption as fact.
Author cross-refs as ref strings (`AP-1` impacts `CA-1, CA-4`).
**Validation pass:** ask open questions one at a time, then `update_threat_model_entry` to
**propagate** each answer into affected paths' likelihood/impact/priority and mitigations.
Promote `draft → in_review → final`; `export_threat_model_markdown` as
`<name>-threat-model.md` in the engagement dir. Keep the threat set small and evidenced.

## MCP tool map

- **Orchestration:** `request_security_action`, `request_playbook`, `spawn_agent`,
  `wait_for_completion`, `mark_execution_complete`, `query_execution_status`,
  `fetch_execution_result`, `list_queued_executions`, `cleanup_agents`, `recover_execution`
  (+ worker-side `claim_execution` / `start_execution` / `complete_execution` /
  `fail_execution`).
- **Planning:** `suggest_next_action` — read-only; given an engagement (or global),
  returns prioritized gaps (failed work, executions missing an interpretation, ready
  queue, untriaged observations, findings not report-ready, phase gaps, threat-model
  status). Call it to orient at session start or whenever deciding what to do next.
- **Reporting:** `create_reporting_engagement`, `list_reporting_engagements`,
  `create_reporting_finding`, `get_reporting_finding`, `update_reporting_finding`,
  `add_reporting_finding_evidence`, `add_reporting_finding_reference`,
  `list_reporting_findings`, `request_reporting_docx`.
- **Threat modeling:** `assemble_threat_model_context`, `create_threat_model`,
  `list_threat_models`, `get_threat_model`, `update_threat_model`, `add_threat_model_entry`,
  `update_threat_model_entry`, `delete_threat_model_entry`, `export_threat_model_markdown`.
- **This guide:** `get_operational_guide`.
