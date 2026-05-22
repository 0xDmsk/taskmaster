# AGENTS.md

Repository-local instructions for agentic coding assistants working in this codebase. This file applies to **any orchestrating LLM** (Codex, Claude, Gemini, etc.). Sister files `CLAUDE.md` and `GEMINI.md` mirror this guidance for tools that auto-load their own filename — keep them in sync when changing the workflow.

## Taskmaster Execution Workflow

`request_security_action` only queues work. A `QUEUED` execution does not provision a worker by itself.

Default workflow:
1. **Queue** — call `request_security_action`.
2. **Provision** — call `spawn_agent` unless you have already verified that a compatible live worker is running for the same target and executor type.
3. **Monitor** — call `wait_for_completion` to block until the execution reaches `COMPLETED` or `FAILED`.
4. **Finalize with analysis** — when the executor returns, call `mark_execution_complete` (or `complete_execution` / `fail_execution`) with an `interpretation` argument. This is a **markdown summary of what the raw output means** — notable findings, suspected misconfigurations, and the next investigative step. The dashboard renders it as the primary "Analysis" panel; the raw agent stdout sits behind a "See agent output" toggle. The interpretation should match what you would tell the user in the CLI when reviewing the result.
5. **Record notes** — append novel captures to `recon-data.md` and promote anything worth triage to `Findings.md` (see Note-Taking Discipline below).
6. **Cleanup** — once a target assessment or phase is finalized, use `cleanup_agents` to decommission the worker fleet.

Use `query_execution_status` mainly for debugging, recovery, or explicit spot-checks. Do not use it as the default next step after queuing work.

### Interpretation field — required for good UX

Every finalization call should include `interpretation`. Without it, the dashboard's findings panel only shows the raw executor stdout, which is often dense JSON or wall-of-text output. With it, the user sees:

- An **Analysis** card at the top of each execution and finding card containing your prose summary.
- The raw agent output collapsed under a `See agent output` toggle.

Markdown is supported (headers, `**bold**`, bullet lists, fenced code blocks, inline `code`, links). Aim for a few sentences to a few short paragraphs — same level of detail you would surface to a human reviewer.

## Executor Selection

- Use `agent_type: "kali"` for CLI-based `skill` and `python` actions.
- Use `agent_type: "playwright"` for `playwright` and `playwright_skill` actions.
- Use `agent_type: "reporting"` for `report_skill` actions — producing the final docx deliverables from settled findings, late in the engagement.

### Writing report content

When you build the `finding` dict you pass to a reporting skill, write for the **client**, not the internal team:

- Plain, succinct language; a few short paragraphs per field at most.
- **Never reference** `Findings.md`, `recon-data.md`, `F-NNN` IDs, or `§N.M` recon section markers — those are internal working files that are not shared with the client. Ground claims in URLs, parameters, response headers, or `/loot` artifacts the client can verify.
- `description` = what was found (concrete). `impact` = why it matters in plain consequences (not "severe security impact"). `proof_of_concept` = a self-contained, copy-pasteable reproduction. `remediation` = specific actions, not generic platitudes.
- Severity is a final value — strip "(pending triage)" qualifiers before rendering.

The full style contract is documented in the module docstring of `skills/reporting.py` and in `templates/README.md`.

## Executor Languages

- `action_type: "python"` — Python only (sandboxed `exec()` on the Kali agent).
- `action_type: "playwright"` — **Python only**. The Playwright operator invokes the container's Python interpreter and the `playwright.sync_api`/`async_api` bindings. JavaScript/Node scripts will fail. The script must print a single JSON envelope to stdout.
- `action_type: "skill"` / `"playwright_skill"` / `"report_skill"` — invokes a Python skill class on the matching agent (`BaseSkill` / `BaseBrowserSkill` / `BaseReportSkill` respectively).

## Mission Briefings

When spawning a worker, use the structure in `policies/agent_mission_template.md`.

## Note-Taking Discipline

Every engagement should produce two living files in the **current working directory** (the assessment folder you were launched from — not `audit/`):

- `Findings.md` — numbered `F-NNN` triage log. Every entry: **Where / Observation / Why it matters / Reproduction (when actionable) / Status / Recommendation**. Include informational and positive observations, not just defects. Severity is a working estimate pending triage.
- `recon-data.md` — the raw data dossier underlying the findings. Observations only, no exploitation. Numbered sections that `Findings.md` cites via `§{section}`.

Create both files on first observation; do not wait for the user to ask. Append after every execution that produced novel data. Do not rewrite history when a hypothesis flips — add a dated follow-up paragraph instead. Full structure and worked examples in `policies/note_taking_template.md`.

## Reference Docs

- `GEMINI.md`: fuller worker-queue operational guide (mirrored model-specific copy)
- `CLAUDE.md`: Claude-specific repository guidance (mirrored copy)
- `policies/agent_mission_template.md`: mission briefing template + interpretation wrap-up
- `policies/note_taking_template.md`: `Findings.md` / `recon-data.md` structure and conventions
- `policies/platform_constraints.md`: macOS VM networking limitations
- `templates/README.md`: how to turn an example docx into a docxtpl template the reporting executor can render
