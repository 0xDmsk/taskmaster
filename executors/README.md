# Kali Cloud Smart Operator

A **minimal, macOS-friendly, Apple Silicon–native Kali Linux container** designed for automated orchestration and interactive use.

This version is integrated with **Taskmaster**, allowing it to act as an automated executor for security tasks.

---

## 🏗️ New Features

*   **Taskmaster Integration**: Ships with `kali-operator`, a Python-based agent that connects to the Taskmaster MCP server to claim and execute tasks.
*   **Smart Execution**: Supports both standard shell commands and **Coderunner-style Python execution** for complex analysis.
*   **Modern Tooling**: Includes `uv`, `pipx`, `proxychains4`, and the full `impacket` script suite.

## 🧰 What’s Included

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

## 🚀 Running the Operator

To start the container and immediately connect to your Taskmaster server:

```bash
container run -it --rm \
  -e TASKMASTER_HOST=10.0.0.X \
  -e TASKMASTER_PORT=5000 \
  kali-min kali-operator
```

Or start the container interactively and run the operator via the `operator` alias:

```bash
operator
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