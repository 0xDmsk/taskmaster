# Taskmaster Executors

Taskmaster ships three executor containers. Each claims a distinct subset of task `action_type` values — they coexist on the same queue without conflict.

---

## 🐉 Kali Smart Operator (`Dockerfile` + `kali_operator.py`)

A **minimal, macOS-friendly, Apple Silicon–native Kali Linux container** designed for automated orchestration and interactive use.

*   **Taskmaster Integration**: Ships with `kali-operator`, a Python-based agent that connects to the Taskmaster MCP server to claim and execute tasks.
*   **Two-Pathway Execution**: Supports `action_type: "skill"` (one-tool-per-class with JSON envelope output) and `action_type: "python"` (Python sandbox for custom analysis). Raw shell execution has been removed.
*   **Modern Tooling**: Includes `uv`, `pipx`, `proxychains4`, and the full `impacket` script suite.
*   **Skips**: tasks with `action_type` of `"playwright"`, `"playwright_skill"`, or `"report_skill"` — those are left for their dedicated executors.

## 🎭 Playwright Executor (`Dockerfile.playwright` + `playwright_operator.py`)

A **lightweight `python:3.12-slim` container** with Playwright + Chromium. No Kali tooling — browser-only, minimal footprint.

*   **Taskmaster Integration**: Ships with `playwright-operator`, which polls Taskmaster and exclusively claims tasks with `action_type: "playwright"` or `"playwright_skill"`. All other action types are left for the Kali operator.
*   **Two-Pathway Execution**: `action_type: "playwright_skill"` imports a `BaseBrowserSkill` subclass and calls `run()`; `action_type: "playwright"` runs a raw Python/Playwright script in a subprocess.
*   **Proxy support**: Set `BROWSER_PROXY` env var to route browser traffic through Burp or ZAP.
*   **Interactive browser exposure**: Playwright agents default to a headful Chromium session with a local noVNC view so operators can handle MFA, bot checks, and cookie banners in the live browser.

## 📄 Reporting Executor (`Dockerfile.reporting` + `report_operator.py`)

A **slim `python:3.12` container** with `docxtpl`, `python-docx`, `jinja2`, and `pyyaml`. No security tooling — its only job is to turn structured findings into branded deliverables.

*   **Taskmaster Integration**: Ships with `report-operator`, which polls Taskmaster and exclusively claims tasks with `action_type: "report_skill"`. Everything else is left for the Kali / Playwright operators.
*   **One-Pathway Execution**: `action_type: "report_skill"` imports a `BaseReportSkill` subclass (e.g. `reporting.FindingDocxReport`) and calls `run()`. The skill renders templates from `/app/templates` and writes documents to `/loot/reports/` by default.
*   **Template provenance**: Templates are produced from a hand-formatted example docx by `scripts/build_finding_template.py`. The builder preserves the source's table layout, fonts, and headers/footers; only the placeholder text in specific cells/paragraphs is rewritten with Jinja tags. See `templates/README.md` for the layout contract and how to adapt the builder for a new template variant.
*   **Output safety**: docxtpl renders run through a Jinja env with `autoescape=True`, so finding content containing `<`, `>`, or `&` (typical XSS PoCs) survives intact instead of breaking the document XML.

---

## 🏗️ Common Features

## 🧰 Kali: What’s Included

### Core Utilities
* `curl`, `jq`, `git`, `uv`, `pipx`
* `vim`, `tmux`, `zsh`, `iputils-ping`
* `ca-certificates`, `gnupg`, `unzip`

### Pentest Tools
* `nmap`, `ffuf`, `gobuster`, `sqlmap`, `dnsutils`
* `python3-impacket` + `impacket-scripts`
* `proxychains4`
* `netcat-traditional`, `socat`

### Cloud & Kubernetes Tooling (ARM64-native)
* ☁️ AWS CLI v2, Google Cloud CLI
* ☸️ `kubectl`, `helm`
* 🐳 Docker CLI (client only)

---

## 🚀 Running the Operators

### Kali Operator

Build and spawn via Makefile:
```bash
make build    # builds kali-smart-operator image
make spawn    # interactive Kali container (run `operator` inside)
```

Or directly:
```bash
docker run -it --rm \
  -e TASKMASTER_HOST=10.0.0.X \
  -e TASKMASTER_PORT=5000 \
  kali-smart-operator kali-operator
```

### Playwright Operator

Build and spawn via Makefile:
```bash
make build-playwright   # builds playwright-operator image
```

### Reporting Operator

Build and spawn via Makefile:
```bash
make build-reporting    # builds report-operator image
```

Or via the `spawn_agent` MCP tool with `agent_type: "reporting"`:
```json
{
  "tool": "spawn_agent",
  "arguments": {
    "agent_type": "reporting",
    "target": "example.test",
    "mission": "Render final docx deliverables for the example.test engagement."
  }
}
```

The agent will claim any queued `report_skill` execution against the configured target and write the rendered docx files into `audit/loot/reports/` on the host.


Or via `spawn_agent` MCP tool with `agent_type: "playwright"`:
```json
{
  "tool": "spawn_agent",
  "arguments": {
    "agent_type": "playwright",
    "target": "https://example.com",
    "mission": "Crawl the SPA and identify exposed API endpoints.",
    "interactive_browser": true,
    "interactive_hold_ms": 180000,
    "novnc_port": 6085
  }
}
```

While a Playwright task is running, open `http://127.0.0.1:6085/vnc.html` on the host to view and control the same browser session the agent is using. If `novnc_port` is omitted, use the `novnc_url` returned by `spawn_agent`.

Or directly:
```bash
docker run -d \
  -p 127.0.0.1:6085:6080 \
  -e TASKMASTER_HOST=10.0.0.X \
  -e TASKMASTER_PORT=5000 \
  -e BROWSER_PROXY=http://10.0.0.X:8080 \
  -e PLAYWRIGHT_HEADLESS=false \
  -e PLAYWRIGHT_DEVTOOLS=true \
  -e PLAYWRIGHT_INTERACTIVE=1 \
  -e PLAYWRIGHT_INTERACTIVE_HOLD_MS=180000 \
  -e PLAYWRIGHT_SESSION_URL=http://127.0.0.1:6085/vnc.html \
  -v /path/to/audit/loot:/loot \
  -v /path/to/skills:/work/skills \
  playwright-operator
```

---

## ⌨️ Shell Experience (Aliases)

| Alias | Command |
| --- | --- |
| `u`, `ur` | `uv`, `uv run` |
| `px` | `pipx` |
| `pc` | `proxychains4` |
| `operator` | `/usr/local/bin/kali-operator` |
| `http-server` | `python3 -m http.server` |

---

## 📂 Wordlists (SecLists)
Remember to mount SecLists from your host:
`-v ~/seclists:/usr/share/seclists:ro`

---

## 🧠 Who This Is For
Red teamers and automation engineers who want a lean, high-performance execution environment on macOS that can be controlled by an LLM-based agent.
