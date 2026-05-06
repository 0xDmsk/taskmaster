# AGENTS.md

Repository-local instructions for agentic coding assistants working in this codebase.

## Taskmaster Execution Workflow

`request_security_action` only queues work. A `QUEUED` execution does not provision a worker by itself.

Default workflow:
1. Call `request_security_action`.
2. Call `spawn_agent` unless you have already verified that a compatible live worker is running for the same target and executor type.
3. Call `wait_for_completion` to monitor execution to completion.

Use `query_execution_status` mainly for debugging, recovery, or explicit spot-checks. Do not use it as the default next step after queuing work.

## Executor Selection

- Use `agent_type: "kali"` for CLI-based `skill` and `python` actions.
- Use `agent_type: "playwright"` for `playwright` and `playwright_skill` actions.

## Mission Briefings

When spawning a worker, use the structure in `policies/agent_mission_template.md`.

## Reference Docs

- `GEMINI.md`: fuller worker-queue operational guide
- `CLAUDE.md`: Claude-specific repository guidance
