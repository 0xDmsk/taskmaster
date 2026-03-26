# Changelog

All notable changes to Taskmaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
