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
2.  **Structured Data**: Prefer `action_type: "skill"` or tools that output JSON to maximize data quality.
3.  **Self-Documentation**: Ensure every action has a strong `justification` for the audit report.

## 🔄 The Standard Loop (Worker-Queue Model)

1.  **Analyze**: Look at the current `audit/session_report.md` and check `container ls` for active workers.
2.  **Request**: Use `request_security_action` to queue the task.
3.  **Provision**: 
    *   **Reuse**: If an agent for the `TARGET` is already running, wait for it to pick up the task.
    *   **Spawn**: Only use `spawn_agent` if no active worker exists or if scaling is required.
    *   Use the structured mission template from `policies/agent_mission_template.md`.
4.  **Monitor**: Call `wait_for_completion` with the `execution_id`. The tool blocks server-side until the execution reaches `COMPLETED` or `FAILED` (default timeout: 10 min). If it times out, call it again or investigate.
    *   **Note**: Do NOT attempt to read `/loot` or container logs until Taskmaster confirms completion.
5.  **Pivot**: Read `structured_data` from the execution result and plan the next step.
6.  **Cleanup**: Once a target assessment or security phase is finalized, use `container stop` and `rm` to decommission the worker fleet.

## 🏗 Skill Expansion Protocol
If a task is complex and no existing skill fits:
1.  **Consult `skills/TEMPLATE.md`**.
2.  **Create a new Skill**: Write a Python file to the `skills/` directory on the host.
3.  **Invoke**: Spawn an agent and call that new skill via `action_type: "skill"`.

## 📦 Data Management (Loot)
- **Host Path**: `audit/loot/`
- **Container Path**: `/loot/`
- Any file saved to `/loot` is an "Artifact".
- Any `.json` or `.xml` (Nmap) file is "Structured Data" and will be auto-parsed.

## 🛡 Concurrency & Phase Rules
- **One Target, One Task**: Do not attempt to start an execution if a target is already `RUNNING`.
- **Phase Order**: Respect the transition from `reconnaissance` -> `enumeration` -> `exploitation`. Do not skip phases without an override justification.

## 📝 Reporting Standards
The `audit/session_report.md` is our primary deliverable.
- Ensure `justification` is professional and security-focused.
- If a task fails, use a `python` analysis action to investigate the logs in `audit/loot/` before retrying.
