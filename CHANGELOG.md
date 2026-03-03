# Changelog

All notable changes to Taskmaster will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
