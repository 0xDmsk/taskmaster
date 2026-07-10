# Changelog

All notable changes to Taskmaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Executions are bound to a reporting engagement.** New nullable `engagement_id` column on the `executions` table (online-migrated onto existing databases, with an `idx_executions_engagement` index). `request_security_action` accepts an optional `engagement_id` (validated — an unknown id is rejected) and tags the queued execution with it; `request_reporting_docx` tags render executions with the explicit engagement or the one shared by its findings. This replaces the earlier scope-asset/finding-source *derivation*, which could not tell apart two engagements assessed over the same or overlapping scope.
- **Global engagement scope selector**: a dashboard-wide selector (top of the main pane, persisted in the `tm_scope` cookie) that filters the stats bar plus the Executions and Observations lists to a single engagement by its `engagement_id`. Selecting "All engagements" restores the global view; a stale cookie (deleted engagement) is validated server-side and ignored so it can't pin every metric to zero. Untagged/legacy executions appear only under "All engagements".
- **Assign an execution to an engagement from the dashboard**: the execution detail panel gained an engagement dropdown (`POST /executions/<id>/engagement`) to tag or re-assign an execution after the fact — useful for legacy executions queued before the engagement existed, or to correct a mistag.
- **Engagement workspace dashboard UI**: new **Engagements** nav item and two pages that make the reporting database engagement-centric rather than execution-centric.
  - `/reporting/engagements` — engagement overview cards (client, status, finding/open counts, scope count, per-severity chips) plus an inline create form.
  - `/reporting/engagements/<id>` — the engagement hub: severity distribution and status-pipeline rollups, a filtered findings list with an **inline status control** (change `draft → needs_review → confirmed → reported → …` per finding via htmx without leaving the page), a **scope panel** that reads and edits `report_assets` (add/remove hosts, domains, URLs — previously unreachable from the UI), and a **render history** panel listing rendered deliverables with one-click "Queue DOCX".
  - New `api.py` helpers: `get_engagements_overview`, `get_engagement_workspace`, `get_engagement_findings`, `get_engagement_renders`, plus severity/status count helpers. New `state/reporting.py` helper `delete_asset`.
- **Rendered DOCX download** from the dashboard: `GET /reporting/download?exec=<id>&i=<index>` streams a report execution's artifact as an attachment. Downloads are addressed by execution + artifact index (no raw path input); `api.resolve_artifact_host_path` maps container paths (`/reports/…`, `/loot/…`) to host files under `runtime/reports` / `runtime/loot` and rejects — via a `realpath` containment check — anything that resolves outside those roots or does not exist. Render-history artifacts are now download links.
- **Findings rollup in the stats bar**: a second stats row shows total / open / reported report findings plus per-severity counts, alongside the existing execution counters.
- **Report findings dashboard UI**: `/reporting/findings` page for the database-backed reporting workflow. It lists curated report findings separately from execution observations, supports engagement/status/severity/search filters, creates engagements, creates and edits report findings, appends evidence and references, and queues DOCX renders through the existing `request_reporting_docx` path.
- **Three-tier bot-evasion ladder** for fingerprint-protected targets (Akamai, Cloudflare, Datadome, etc.) where vanilla headless Chromium and Burp's outbound TLS both get blocked at the transport layer (`ERR_HTTP2_PROTOCOL_ERROR`, silent 403, challenge page, or "Burp Suite" upstream-failure page):
  - **`curl_cffi`** + **`httpx[http2]`** installed in the Kali image (`executors/Dockerfile`). `python` and `skill` actions can now `from curl_cffi import requests; requests.get(url, impersonate="chrome124")` for JS-free recon (API probes, OAuth/redirect chasing, sitemap/robots, raw endpoint enum) with a real Chrome/Firefox/Safari TLS+HTTP2 fingerprint.
  - **Patchright** browser engine in the Playwright image — anti-detection Playwright drop-in on patched Chromium. **Default** for `agent_type: "playwright"` going forward.
  - **Camoufox** browser engine in the Playwright image — fingerprint-hardened custom Firefox. Escalation tier for the cases Patchright still gets flagged.
  - **`browser_engine` argument on `spawn_agent`** (`"playwright" | "patchright" | "camoufox"`, default `"patchright"`). Propagated into the container as `BROWSER_ENGINE` and consumed by `BaseBrowserSkill` and raw `playwright` scripts.
  - **`BaseBrowserSkill` engine dispatch** (`skills/browser.py`): `run()` now branches on the resolved engine (kwargs → `BROWSER_ENGINE` env → class attr). Camoufox's combined browser+context launcher is wrapped behind the same `page, context` contract, so existing skills work unchanged across all three engines. JSON envelope gains an `engine` field; `tool_version` is sourced from whichever engine actually ran.
  - Selection guidance added to `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, the `request_security_action` tool description, and the MCP schema for `spawn_agent.browser_engine`. Decision rule: pick the lowest tier that gets the data; escalate on `ERR_HTTP2_PROTOCOL_ERROR` / silent 403 / visible challenge.
  - New tests in `tests/unit/test_browser_skill.py` exercise per-engine version resolution. `_playwright_version()` renamed to `_engine_version(engine)`.
- **Reporting executor** (`executors/Dockerfile.reporting` + `executors/report_operator.py`): dedicated `report-operator` container (slim `python:3.12` + `docxtpl` / `python-docx` / `jinja2` / `pyyaml`) that exclusively claims tasks with `action_type: "report_skill"`. Mirrors the playwright operator's lifecycle: claim → start → run skill → complete, with a server-error log on every state-write rejection.
- **`skills/reporting.py`**: `BaseReportSkill` ABC — non-CLI counterpart to `BaseSkill` / `BaseBrowserSkill`. Subclasses implement `render(**kwargs) -> dict`; the orchestrator handles timing, artifact tracking, and JSON envelope assembly.
- **`skills/reporting.FindingDocxReport`**: first reporting skill. Takes a `finding` dict, a list of `findings`, or a `findings_path` (YAML/JSON) and renders one branded docx per finding via docxtpl. Writes to `/loot/reports/` by default; supports `template_path` and `output_dir` overrides. Jinja autoescape is enabled so payloads containing `<`, `>`, `&` (typical XSS PoCs) render correctly instead of corrupting the document.
- **`templates/finding_template.docx`**: docxtpl-tagged finding template — produced from a hand-formatted source docx by `scripts/build_finding_template.py`. Layout (fonts, table widths, headers/footers) is preserved from the source; only placeholder text is rewritten with Jinja tags.
- **`scripts/build_finding_template.py`**: one-shot builder that converts an example docx into the docxtpl template. Re-runnable when the source layout changes; fails loudly on layout drift via a snippet-based sanity check.
- **`templates/README.md`**: guide for producing a docxtpl template from a provided example docx — covers the layout contract, the builder script's mental model, the autoescape gotcha, and how to adapt the builder for a new template variant.
- **Finding-content style contract** for the reporting pathway. Documented in the `skills/reporting.py` module docstring, `templates/README.md`, and the agent guides (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`). Core rules: plain, succinct, client-facing language; each field has one job (description = what / impact = why it matters / PoC = how to reproduce / remediation = specific actions); **no references to `Findings.md`, `recon-data.md`, `F-NNN` triage IDs, or `§N.M` recon section markers** — those internal working files are not shared with the client, and citing them in the deliverable creates confusion.
- **New `action_type: "report_skill"`** in `request_security_action` — invokes a `BaseReportSkill` subclass by name (e.g. `reporting.FindingDocxReport`), mirroring the `playwright_skill` pathway. Requires the `skill` field.
- **New `agent_type: "reporting"`** in `spawn_agent` — selects the `report-operator` image and `reporting-agent-*` container name.
- **`make build-reporting`** target and inclusion in `make build`.
- Reporting deliverables are recognized by `cleanup_agents` (new `reporting-agent` prefix + `report-operator` image name).
- **Agent reaper** (`tools/reaper.py`): background daemon thread started by the MCP server that periodically stops Taskmaster-managed agent containers under three conditions — hard age cap (default 4h), stale heartbeat on a claimed/running execution (default 2h since `updated_at`, also force-fails the execution to release the target lock), and idle past grace (default 15 min with no claimed work). Configurable via `TASKMASTER_REAPER_ENABLED`, `_INTERVAL`, `_IDLE_TIMEOUT`, `_STALE_TIMEOUT`, `_MAX_AGE`.
- 9 new unit tests in `tests/unit/test_reaper.py` covering each reap path, the keep cases, non-Taskmaster container filtering, and docker-timestamp parsing.
- **Burp Suite CA trust** in both agent images: drop a DER-exported Burp CA at `executors/burp-cacert.der` (gitignored, per-developer) and it's installed into the system trust store via `update-ca-certificates`. Kali tools and Chromium will then accept Burp's MITM cert without `verify=False` workarounds. Uses a BuildKit wildcard COPY so builds still work when the cert is absent.

### Changed
- **Report finding bodies now render markdown in the dashboard.** The engagement workspace passes `description`, `impact`, `proof_of_concept`, and `remediation` through the same lightweight markdown filter used for execution analysis (headers, lists, inline/fenced code), so stored finding content reads like the DOCX output instead of flat text. A finding's `source_execution_id` is now a deep-link to the originating execution.
- **Dashboard naming split**: the old execution-derived **Findings** view is now **Observations** (`/observations`, `/api/observations`) to avoid conflating raw worker output with client-facing report findings. `/findings` and `/api/findings` remain compatibility redirects/aliases.
- **Runtime layout reorganized under a single `runtime/` umbrella.** Loot, reports, audit logs, and state DB now live at `<WORK_DIR>/runtime/{loot,reports,audit,state}/` instead of being scattered across `audit/loot/`, `audit/`, and `state/` at the top of `WORK_DIR`. One folder to gitignore, one to delete, no more namespace collision between the on-disk `state/` and the `state/` Python package, and no `taskmaster/taskmaster/` visual collision when running in-place from the project root. `config.py` now exposes `RUNTIME_DIR`, `LOOT_DIR`, `REPORTS_DIR`, `AUDIT_DIR`, and `STATE_DIR`; downstream callers (`state/storage.py`, `audit/audit_manager.py`, `tools/spawn_agent.py`, `Makefile`, `scripts/cleanup.sh`, `.gitignore`) updated. Per-engagement isolation continues to work through `TASKMASTER_WORK_DIR`. No auto-migration — move any existing `audit/`/`state/` into `runtime/` once by hand.
- **`FindingDocxReport` now emits a single combined docx for any number of findings.** The template body is wrapped in `{%p for finding in findings %}…{%p endfor %}` with a hard page break between findings, so one `doc.render()` call produces one output file. Filename derives from the common dotted prefix of the finding ids (e.g. `BHI-OFFSEC-25.05-findings-2026-06-10.docx`) or the target slug when ids don't share one. Single-finding callers (`finding=…`) keep the per-finding `{id}-{title}.docx` naming. Output defaults to `/reports/` (host `runtime/reports/`) via a new bind mount, falling back to `/loot/reports/` when the mount is absent. The envelope's `findings` now returns `{output_path, finding_ids, template_path}` instead of a `rendered: [...]` list. Builder script (`scripts/build_finding_template.py`) updated to emit the wrap on re-runs.
- `make build` now builds **all three** agent containers (Kali + Playwright + Reporting). Use `make build-kali`, `make build-playwright`, or `make build-reporting` for partial rebuilds.
- `kali_operator.py` skip-list extended: `report_skill` joins `playwright`/`playwright_skill` as action types the Kali operator leaves in the queue for its dedicated executor.
- Direct project dependencies now include `docxtpl`, `python-docx`, and `pyyaml` so the reporting renderer runs on the host (e.g. for local smoke tests, dashboard-side rendering experiments) without spinning up the container.
- Planner-facing execution guidance now makes provisioning explicit: `request_security_action` only queues work, `spawn_agent` is the default next step unless a compatible live worker has already been verified for the target, and `query_execution_status` is positioned as a debugging/recovery tool rather than the standard monitor path.
- Added the same provisioning guidance to `CLAUDE.md` and a new repo-local `AGENTS.md` so non-Gemini agents receive the same workflow expectations.
- `spawn_agent` proxy is now **opt-in per call**: pass `proxy_url=...` explicitly to route container traffic through an intercepting proxy. The previous fallback to `.env`/shell `HTTP_PROXY` is removed — Docker containers reach external networks directly, and the always-on proxy injection was a leftover from the macOS-VM era that broke whenever Burp wasn't listening. Setting `HTTP_PROXY` in `.env` no longer affects spawned agents (`.env.example` updated to reflect this).
- `configure_proxychains` (kali operator) now parses `$HTTP_PROXY` to learn the upstream host/port instead of using `$TASKMASTER_HOST` and a hardcoded `8888`. Tools invoked via `proxychains4` now flow through the same upstream as `HTTP_PROXY`-aware clients (curl, requests, etc.); skips configuration silently when no proxy is set.
- `query_execution_status` now returns a slim projection by default (status, phase, target, executor, `updated_at`, `seconds_since_update`, `has_result`, `has_interpretation`) instead of dumping the full execution record — avoids kilobytes of request-payload and result-body bloat on every poll. Pass `verbose: true` to get the original full-record shape for debugging. `seconds_since_update` lets the orchestrator detect a likely-stuck worker without waiting for the server-side reaper.
- `spawn_agent` now bind-mounts the host `templates/` directory onto `/app/templates` for reporting agents, so template edits take effect on the next spawn without rebuilding `report-operator`. The `COPY templates /app/templates` step in `Dockerfile.reporting` is retained as a fallback when the host directory is missing (e.g. CI / shipped images). `templates/README.md` updated to reflect the new dev flow.

### Fixed
- **Reporting executor was invisible to MCP clients.** `spawn_agent`'s `agent_type` enum in `server.py` was hardcoded to `["kali", "playwright"]`, even though the handler and `request_security_action` (with `action_type: "report_skill"`) already supported reporting. LLMs reading the MCP schema concluded no reporting executor existed and fell back to running `FindingDocxReport` in a Kali python sandbox, where the host-mounted template path doesn't exist — so they hand-rolled minimal `python-docx` templates and produced unbranded deliverables. Enum and description now expose all three executor types. Stale guidance in `GEMINI.md` and the `cleanup_agents` docstring updated to match.
- **Wedged target locks**: both operators previously discarded the responses from `start_execution`, `complete_execution`, and `fail_execution`. If one execution got stuck `RUNNING` (e.g. an agent crash mid-action), every later CLAIMED→RUNNING transition for that target was silently rejected by the target-lock policy, the operator kept running the action and failing every state write, and rows stayed at CLAIMED until the reaper swept them — with no diagnostic signal anywhere. Operators now check each response: a rejected start skips execution with a logged reason, and rejected complete/fail calls print the server's error so the wedge is visible in `docker logs`.

## [0.5.0] - 2026-04-21

### Added
- **Playwright executor**: dedicated `playwright-operator` container (`executors/Dockerfile.playwright`) built on `python:3.12-slim` with Playwright + Chromium. No Kali tooling — browser-only, minimal footprint.
- **`executors/playwright_operator.py`**: operator that polls Taskmaster and exclusively claims tasks with `action_type: "playwright"` or `"playwright_skill"`. All other action types are left for the Kali operator.
- **`skills/browser.py`**: `BaseBrowserSkill` ABC — the browser-native counterpart to `BaseSkill`. Subclasses implement a single `run_browser(page, context, **kwargs) -> dict` method; the orchestrator handles browser lifecycle, timing, loot saving, and envelope assembly. Supports `BROWSER_PROXY` env var for Burp/ZAP routing.
- **Two new `action_type` values** in `request_security_action`: `"playwright"` (raw Python/Playwright script provided in `script` field) and `"playwright_skill"` (imports a `BaseBrowserSkill` subclass by name, mirrors existing `"skill"` pathway).
- **`agent_type` parameter** in `spawn_agent`: `"kali"` (default) or `"playwright"` — spawns the correct container image and operator command.
- **`make build-playwright`** target and `DOCKERFILE` env var support in `scripts/build.sh`.
- 35 new unit tests across `test_playwright_operator.py` and `test_browser_skill.py` covering dispatch, script execution, envelope structure, context options, artifact helpers, and error handling.

### Changed
- `kali_operator.py`: skips tasks with `action_type` in `("playwright", "playwright_skill")` before claiming — they are left in the queue for the playwright operator.
- `request_security_action` schema: added `"playwright"` and `"playwright_skill"` to the `action_type` enum; added `script` field definition; added conditional validation for both new types.

## [0.4.0] - 2026-04-03

### Added
- **Web dashboard** with 4 tabs: Executions, Targets, Agents, Findings.
- **Execution detail views**: Click any execution row to expand full request/result breakdown — justification, skill, arguments, tool, command, timing, findings, artifacts, errors.
- **Target detail views**: "Show Details" button expands executions grouped by security phase in collapsible sections with mini-tables.
- **Agent history**: Agents tab now shows execution history per `executor_id`, merged with active container data. Includes task stats and full task history table.
- **Rich findings**: Severity badges (critical/high/medium/low/info), CVSS scores, risk descriptions, remediation guidance, and references extracted from skill output when available.
- **Deep-linking**: Cross-view links with auto-expand. Click a target, agent, or execution ID in any detail view to navigate and auto-expand the linked item (`#exec:<id>`, `#target:<ip>`, `#agent:<name>`).
- **Auto-refresh pause**: HTMX polling automatically pauses when any detail panel or finding card is expanded, preventing content from being replaced while reading.
- New API endpoints: `/api/executions/<id>/detail`, `/api/targets/<target>/detail`, `/api/agents/<id>/detail`, `/api/agents/history`.
- New backend functions: `get_execution_detail()`, `get_target_detail()`, `get_agent_history()`.
- New templates: `execution_detail.html`, `target_detail.html`, `agent_detail.html`.
- CSS: detail panels, mini-tables, severity badges, expand buttons, historical agent dots.

### Changed
- Dashboard nav reordered: Executions → Targets → Agents → Findings (findings moved last).
- Targets and agents layouts changed from grid to single-column stack for better detail expansion.
- `get_findings()` now includes `executor_id`, `justification`, `tool`, `severity`, `cvss`, `risk`, `remediation`, `references`, `description` from request/result data.
- Agents page route uses `get_agent_history()` instead of `get_agents()`.

## [0.3.0] - 2026-03-26

### Added
- **Structured skill system**: New `BaseSkill` with `build_command()` + `parse_output()` abstract methods and a concrete `run()` orchestrator that produces a standardized JSON envelope for every skill execution.
- **One-tool-per-skill architecture**: Each skill class wraps exactly one CLI tool, replacing the old multi-action classes.
- New skill classes: `FpingSweep`, `NmapScan`, `FfufFuzz`, `HttpxDetect`, `GobusterDns`, `SubfinderEnum`, `NucleiTakeover`, `AwsCliAudit`, `GcloudAudit`.
- JSON envelope output for all executions (skills and python sandbox), providing consistent `skill`, `target`, `status`, `findings`, `artifacts`, and `errors` fields.
- Tool version detection via `tool_version_command` class attribute on skills.
- Artifact tracking via `self._artifacts` list in `BaseSkill`.
- `fetch_execution_result` now parses JSON results before returning, so LLMs receive a dict instead of a raw string.
- 48 new unit tests: `test_base_skill.py` (envelope assembly, error handling, version detection), `test_skills.py` (all skill `build_command`/`parse_output`), `test_kali_operator.py` (two-pathway dispatch).

### Changed
- **Breaking**: `request_security_action` `action_type` enum changed from `["network_scan", "web_probe", "credential_test", "exploit_attempt", "data_extraction", "analysis"]` to `["skill", "python"]`.
- **Breaking**: `request_security_action` no longer requires `tool` and `command` at top level. Instead: `skill` + `arguments` for skill actions, `command` for python actions.
- `kali_operator.py` reduced to two execution pathways: `_execute_skill()` and `_execute_python_sandbox()`. Raw shell pathway removed.
- Python sandbox output now wrapped in the same JSON envelope format as skills.
- `skills/TEMPLATE.md` rewritten to document the new `build_command()` + `parse_output()` pattern.

### Removed
- `parse_nmap_xml()` from `kali_operator.py` — absorbed into `NmapScan.parse_output()`.
- Raw shell execution pathway in `kali_operator.py` (lines 196-257 of old code).
- `[STRUCTURED_DATA]` and `[ARTIFACTS]` ad-hoc markers in output — replaced by JSON envelope.
- Multi-action skill classes: `NetworkScanner`, `WebReconSkill`, `SubdomainSkill`, `TakeoverSkill`, `CloudAuditSkill`.

## [0.2.0] - 2026-03-03

### Added
- `wait_for_completion` MCP tool — blocks server-side until execution reaches terminal state, eliminating client polling loops.
- Threaded HTTP server (`ThreadingHTTPServer`) to support concurrent requests while `wait_for_completion` blocks.
- Configurable timeouts via env vars: `WAIT_DEFAULT_TIMEOUT`, `WAIT_POLL_INTERVAL`, `MCP_BRIDGE_TIMEOUT`.
- Long timeout on HTTP bridge (`mcp-http-bridge.py`) to support blocking tool calls.

### Changed
- Cleaned up `.env.example` — removed dead vars not read by any code (`CONTAINER_RUNTIME`, `HOST_IP`, `AGENT_IMAGE_NAME`, `AGENT_BASE_NAME`, `AUDIT_DIR`, `LOOT_DIR`, `STATE_DIR`, `WORDLISTS_PATH`, `LOG_LEVEL`).
- Updated `GEMINI.md` step 4: agents now use `wait_for_completion` instead of polling `query_execution_status`.
- Optimized `Makefile` with a `status` command and simplified dev workflow.

## [0.1.0] - 2026-02-10

### Added
- Initial release of Taskmaster
- Agentic security orchestration platform
- MCP server for LLM-driven security assessments
- Kali Linux container fleet management
- Skills-based extensibility framework
