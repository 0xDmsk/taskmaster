# Changelog

All notable changes to Taskmaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Agent reaper** (`tools/reaper.py`): background daemon thread started by the MCP server that periodically stops Taskmaster-managed agent containers under three conditions — hard age cap (default 4h), stale heartbeat on a claimed/running execution (default 2h since `updated_at`, also force-fails the execution to release the target lock), and idle past grace (default 15 min with no claimed work). Configurable via `TASKMASTER_REAPER_ENABLED`, `_INTERVAL`, `_IDLE_TIMEOUT`, `_STALE_TIMEOUT`, `_MAX_AGE`.
- 9 new unit tests in `tests/unit/test_reaper.py` covering each reap path, the keep cases, non-Taskmaster container filtering, and docker-timestamp parsing.
- **Burp Suite CA trust** in both agent images: drop a DER-exported Burp CA at `executors/burp-cacert.der` (gitignored, per-developer) and it's installed into the system trust store via `update-ca-certificates`. Kali tools and Chromium will then accept Burp's MITM cert without `verify=False` workarounds. Uses a BuildKit wildcard COPY so builds still work when the cert is absent.

### Changed
- `make build` now builds **both** the Kali and Playwright agent containers. Use `make build-kali` or `make build-playwright` for partial rebuilds.
- Planner-facing execution guidance now makes provisioning explicit: `request_security_action` only queues work, `spawn_agent` is the default next step unless a compatible live worker has already been verified for the target, and `query_execution_status` is positioned as a debugging/recovery tool rather than the standard monitor path.
- Added the same provisioning guidance to `CLAUDE.md` and a new repo-local `AGENTS.md` so non-Gemini agents receive the same workflow expectations.
- `spawn_agent` proxy is now **opt-in per call**: pass `proxy_url=...` explicitly to route container traffic through an intercepting proxy. The previous fallback to `.env`/shell `HTTP_PROXY` is removed — Docker containers reach external networks directly, and the always-on proxy injection was a leftover from the macOS-VM era that broke whenever Burp wasn't listening. Setting `HTTP_PROXY` in `.env` no longer affects spawned agents (`.env.example` updated to reflect this).
- `configure_proxychains` (kali operator) now parses `$HTTP_PROXY` to learn the upstream host/port instead of using `$TASKMASTER_HOST` and a hardcoded `8888`. Tools invoked via `proxychains4` now flow through the same upstream as `HTTP_PROXY`-aware clients (curl, requests, etc.); skips configuration silently when no proxy is set.
- `query_execution_status` now returns a slim projection by default (status, phase, target, executor, `updated_at`, `seconds_since_update`, `has_result`, `has_interpretation`) instead of dumping the full execution record — avoids kilobytes of request-payload and result-body bloat on every poll. Pass `verbose: true` to get the original full-record shape for debugging. `seconds_since_update` lets the orchestrator detect a likely-stuck worker without waiting for the server-side reaper.

### Fixed
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
