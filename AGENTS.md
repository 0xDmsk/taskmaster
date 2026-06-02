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

**Voice for `interpretation`, `Findings.md`, and `recon-data.md` prose:** pentester drafting working notes. Plain and concrete — cite the URL, header, parameter, or payload that proves the claim instead of abstract risk language. No scaremongering ("catastrophic", "trivially exploitable"), no marketing tone ("robust", "world-class"), no hedging fluff. Length follows the observation. Full tone contract in `policies/note_taking_template.md`.

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

## Bot-Protected Targets (Akamai, Cloudflare, Datadome…)

When a target sits behind fingerprint-based bot defenses, plain headless Chromium and Burp's outbound Java TLS stack both get blocked **below** the HTTP layer — you see `ERR_HTTP2_PROTOCOL_ERROR`, silent 403s, challenge pages, or a "Burp Suite" upstream-failure page rendered by Burp itself. Burp cannot fix this; its own outbound fingerprint is part of what's being detected. Skip the proxy for these targets and lean on the agent's own logging instead.

Pick the **lowest tier** that produces the data you need:

1. **`curl_cffi`** — Kali agent, `action_type: "python"`. Use when you do not need JavaScript execution: API probes, OAuth/redirect chasing, raw endpoint enumeration, sitemap/robots fetches. Wraps a real Chrome/Firefox/Safari TLS + HTTP/2 fingerprint around a `requests`-like API. Fastest by far.

   ```python
   from curl_cffi import requests
   r = requests.get("https://target", impersonate="chrome124")
   ```

2. **Patchright** — Playwright agent, `browser_engine: "patchright"` on `spawn_agent`. Drop-in Playwright replacement with anti-detection patches on Chromium. Default for `agent_type: "playwright"` — pick this first when JS is required.

3. **Camoufox** — Playwright agent, `browser_engine: "camoufox"`. Custom-built Firefox tuned for fingerprint resistance. Escalate to it when Patchright still gets flagged (HTTP/2 protocol errors, persistent challenge pages, silent 403s). Slower cold start and narrower site-compat surface than Patchright, so don't reach for it first.

`BaseBrowserSkill` reads the engine from kwargs / the `BROWSER_ENGINE` env var (set by `spawn_agent`), so a skill written for vanilla Playwright works unchanged across all three engines.

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
