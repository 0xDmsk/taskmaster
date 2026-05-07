# Gemini Operational Guide: Taskmaster Infrastructure

This document serves as the "mental model" for AI agents operating the Taskmaster platform.

## ⚠️ CRITICAL: Platform Constraints (Read First)

Taskmaster containers run inside a **Linux VM on macOS** (not native Linux). This imposes hard networking limitations. **Violating these will produce silent failures or garbage data.**

### Broken — NEVER use these:
- `nmap -sS` (SYN scan) — requires raw sockets, will silently fall back or error
- `nmap -sU` (UDP scan) — unreliable through double NAT
- `nmap -O` (OS fingerprinting) — requires raw sockets
- `nmap -sA`, `-sY`, `-sZ`, `-sI` — all raw-socket dependent
- `arp-scan`, `nmap -PR` — can only see the VM's virtual bridge
- `tcpdump`, `tshark` for sniffing — captures VM traffic, not real network
- `scapy`, `hping3` — raw packets go to VM's virtual NIC
- `nmap --traceroute` — shows VM hops, not real path

### Reliable — ALWAYS use these instead:
- **Port scanning**: `nmap -sT` (TCP connect scan) — works through NAT
- **Service detection**: `nmap -sT -sV -sC` — connect-based, fully reliable
- **OS inference**: Use `-sV` banners + `--script=smb-os-discovery,http-server-header` instead of `-O`
- **Web tools**: `ffuf`, `gobuster`, `sqlmap`, `nikto` — all HTTP-based, fully functional
- **DNS**: `dig`, `nslookup`, `dnsrecon` — works fine
- **Cloud/API tools**: `aws`, `gcloud`, `kubectl` — HTTPS API calls
- **Credential testing**: `hydra`, `impacket` — TCP-based, works fine

### Nmap Quick Reference:
```bash
# CORRECT
nmap -sT -sV -sC -p 1-10000 target -oX /loot/scan.xml

# WRONG — will fail silently
nmap -sS -sV -O target
```

**Full reference**: See `policies/platform_constraints.md` for complete details.

## 🎯 Core Objectives
1.  **Autonomous Execution**: Do not just suggest commands; spawn agents to execute them.
2.  **Structured Data**: Prefer the simplest execution pathway that can reliably produce the needed result. Use `action_type: "skill"` for established tool workflows, `action_type: "python"` for lightweight fetch/parse/custom logic, and `action_type: "playwright_skill"` or `"playwright"` for browser work.
3.  **Self-Documentation**: Ensure every action has a strong `justification` for the audit report.

## 🧭 Execution Path Selection

Before queuing an execution, explicitly decide between these three options:

1.  **Use an existing skill**
    *   Choose this when the task clearly maps to one installed tool and the tool adds real value over plain Python.
    *   Good examples: `nmap` port scanning, `ffuf` content discovery, `gobuster` DNS brute-force, `nuclei` takeover checks.
    *   Do not use a skill just because one exists. If the task is only “fetch one page and summarize headers/title/scripts,” a skill is usually overkill.
    *   For ProjectDiscovery-backed skills, assume the agent may need to install the binary with `pdtm` before first use if it is missing.

2.  **Use `action_type: "python"`**
    *   Choose this for lightweight passive HTTP requests, HTML parsing, JSON parsing, response-header inspection, small transformations, and glue logic between previous findings.
    *   Prefer Python when the task can be solved with the standard library or a small amount of straightforward code.
    *   Default to Python for simple passive web recon against one or a few URLs unless a dedicated tool is specifically needed.

3.  **Create a new skill**
    *   Choose this only when the task is likely to recur and requires a stable wrapper around one external tool or one repeatable browser workflow.
    *   A new skill should encapsulate real reusable behavior, not a one-off fetch or a tiny parsing script.
    *   If the task is novel but short-lived, solve it with `python` first instead of expanding the skill library prematurely.

## 🎭 When To Use Playwright

Use the Playwright executor when:

*   The page depends on client-side rendering and a plain HTTP fetch misses meaningful content
*   You need the post-JavaScript DOM, runtime-loaded resources, visible UI text, or browser navigation behavior
*   The task is to observe what loads in a real browser rather than just what the origin returns over HTTP

When you choose this path:

*   Spawn the agent with `agent_type: "playwright"`
*   Queue work with `action_type: "playwright"` or `action_type: "playwright_skill"`
*   Do not send browser tasks to a Kali agent and hope they will be handled correctly
*   Prefer `wait_until="domcontentloaded"` or `wait_until="load"` plus a short settle delay for modern apps
*   Avoid `networkidle` by default on challenge-heavy, analytics-heavy, or long-polling apps because it often never settles
*   Keep `interactive_browser` enabled unless the task is explicitly unattended; Playwright agents expose a local noVNC session by default
*   Increase `interactive_hold_ms` when the user may need time to complete MFA, SSO, cookie consent, or bot challenges in the live browser session

## ✅ Decision Heuristics

Use this checklist:

*   **Single URL, passive fetch, simple parsing** → `python`
*   **Need browser rendering, JS execution, SPA interaction** → `playwright` or `playwright_skill`
*   **Need a well-known external tool with structured output** → existing `skill`
*   **Need the same external tool workflow repeatedly across targets** → create a new `skill`
*   **Need to combine prior findings, post-process JSON, or reshape data** → `python`
*   **Need a real browser session to see what a user sees** → spawn `agent_type: "playwright"`

## 🚫 Anti-Patterns

Avoid these planning mistakes:

*   Do not choose `web.HttpxDetect` for a task that only needs a basic GET, headers, title, and a few HTML counts.
*   Do not create a new skill for a one-off page fetch, one-off regex extraction, or small response comparison.
*   Do not force a skill when the external binary may be absent and Python can solve the task directly.
*   Do not use browser automation when plain HTTP requests are sufficient.
*   Do not create a new skill just to wrap one missing ProjectDiscovery binary; prefer the existing skill plus `pdtm` bootstrap if the workflow already fits.

## 🛠 Available Skills

### Kali Skills (run in the Kali executor — `action_type: "skill"`)

| Skill Class | Tool | Use For |
|-------------|------|---------|
| `network.FpingSweep` | `fping` | Host discovery / ping sweeps |
| `network.NmapScan` | `nmap` | Port scanning and service detection |
| `web.FfufFuzz` | `ffuf` | Directory and endpoint fuzzing |
| `web.HttpxDetect` | `httpx` | Web technology fingerprinting |
| `subdomain.GobusterDns` | `gobuster` | Active DNS subdomain brute-force |
| `subdomain.SubfinderEnum` | `subfinder` | Passive subdomain enumeration |
| `takeover.NucleiTakeover` | `nuclei` | Subdomain takeover detection |
| `cloud.AwsCliAudit` | `aws` | AWS security audit |
| `cloud.GcloudAudit` | `gcloud` | GCP security audit |

### Browser Skills (run in the Playwright executor — `action_type: "playwright_skill"`)

Extend `BaseBrowserSkill` from `skills/browser.py`. Subclasses implement `run_browser(page, context, **kwargs) -> dict`. The orchestrator handles browser lifecycle, loot saving, and envelope assembly.

### Invoking a Kali Skill
```json
{
  "action_type": "skill",
  "skill": "network.NmapScan",
  "target": "10.0.0.1",
  "arguments": {"ports": "80,443", "flags": "-sT -sV -sC"}
}
```

### Invoking a Browser Skill
```json
{
  "action_type": "playwright_skill",
  "skill": "browser.RenderedPageObserve",
  "target": "https://example.com",
  "arguments": {"wait_until": "domcontentloaded", "settle_ms": 5000}
}
```

### Running a Raw Playwright Script

**The Playwright executor runs Python, not JavaScript.** Scripts are executed via the container's Python interpreter using the `playwright.sync_api` (or `async_api`) bindings. Submitting a Node/JS script will fail. The script must print a single JSON envelope to stdout.

```json
{
  "action_type": "playwright",
  "target": "https://example.com",
  "script": "import json, os\nfrom playwright.sync_api import sync_playwright\n# ... script prints a JSON envelope to stdout"
}
```

### JSON Envelope (returned by every skill)
```json
{
  "skill": "network.NmapScan",
  "target": "10.0.0.1",
  "status": "success",
  "tool": "nmap",
  "tool_version": "7.94",
  "command": "nmap -sT -sV -sC 10.0.0.1 -p 80,443 -oX /loot/nmap_10_0_0_1.xml",
  "findings": { "hosts": [...] },
  "artifacts": ["/loot/nmap_10_0_0_1.xml"],
  "errors": []
}
```

## 🔄 The Standard Loop (Worker-Queue Model)

1.  **Analyze**: Look at the current `audit/session_report.md` and check `docker ps` for active workers.
2.  **Request**: Use `request_security_action` to queue the task.
3.  **Provision**: 
    *   **Default**: After queuing an execution, immediately call `spawn_agent`.
    *   **Reuse**: Skip `spawn_agent` only if you have already verified that a compatible worker is currently running for the same `TARGET` and executor type.
    *   **Do not assume**: A `QUEUED` execution does not provision a worker by itself. `request_security_action` only writes to the queue.
    *   Pass `agent_type: "kali"` (default) for CLI-based tasks or `agent_type: "playwright"` for browser-based tasks. The correct container image and operator command are selected automatically.
    *   Use the structured mission template from `policies/agent_mission_template.md`.
4.  **Monitor**: Call `wait_for_completion` with the `execution_id`. The tool blocks server-side until the execution reaches `COMPLETED` or `FAILED` (default timeout: 10 min). If it times out, call it again or investigate.
    *   **Do not poll by default**: Do not call `query_execution_status` as the normal next step after queuing work. Use it only for debugging, recovery, or an explicit spot-check.
    *   **Note**: Do NOT attempt to read `/loot` or container logs until Taskmaster confirms completion.
5.  **Pivot**: Read the JSON envelope from the execution result — `findings` contains structured data, `artifacts` lists saved files.
6.  **Cleanup**: Once a target assessment or security phase is finalized, use `cleanup_agents` MCP tool or `docker stop` + `docker rm` to decommission the worker fleet.

## 🏗 Skill Expansion Protocol
If a task is complex and no existing skill fits:
1.  **Consult `skills/TEMPLATE.md`**.
2.  **Check reuse first**: If the task is a simple passive fetch/parse or small analysis step, use `action_type: "python"` instead of creating a skill.
3.  **Create a new Skill**: Write a Python file to the `skills/` directory on the host only if the workflow is tool-backed and reusable.
4.  **Invoke**: Spawn an agent and call that new skill via `action_type: "skill"`.

## 📦 Data Management (Loot)
- **Host Path**: `audit/loot/`
- **Container Path**: `/loot/`
- Skills automatically save artifacts to `/loot` and track them in the envelope's `artifacts` list.
- All findings are returned as structured JSON in the envelope's `findings` field — no manual parsing needed.

## 🛡 Concurrency & Phase Rules
- **One Target, One Task**: Do not attempt to start an execution if a target is already `RUNNING`.
- **Phase Order**: Respect the transition from `reconnaissance` -> `enumeration` -> `exploitation`. Do not skip phases without an override justification.

## 📝 Reporting Standards
The `audit/session_report.md` is our primary deliverable.
- Ensure `justification` is professional and security-focused.
- If a task fails, use a `python` analysis action to investigate the logs in `audit/loot/` before retrying.
