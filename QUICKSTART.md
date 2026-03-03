# Taskmaster Quick Start

Get Taskmaster running in 5 minutes.

## 🚀 One-Line Setup

```bash
# Clone, setup environment, and build container
git clone <repo-url> taskmaster && cd taskmaster && make dev && make build
```

## ⚡ Quick Commands (using Makefile)

```bash
# Start the MCP server (HTTP mode by default)
make start

# Run tests
make test

# Spawn an interactive agent for manual testing
make spawn

# Check project and environment status
make status
```

## 🎯 First Assessment

### 1. Start the Server

Terminal 1:
```bash
make start
```

### 2. Connect with your AI Agent

Taskmaster provides a **bridge** to connect standard MCP clients to its threaded HTTP server.

**For Gemini CLI:**
Edit your settings (usually `~/.gemini/settings.json`) to include:
```json
"mcpServers": {
  "taskmaster": {
    "command": "python3",
    "args": ["/absolute/path/to/taskmaster/scripts/mcp-http-bridge.py"],
    "env": {
      "TASKMASTER_HOST": "127.0.0.1",
      "TASKMASTER_PORT": "5000"
    }
  }
}
```

### 3. Request a Security Action

Ask your AI agent:
```
"Perform reconnaissance on target 192.168.1.1 using nmap to identify open ports"
```

The workflow is now fully autonomous:
1. AI calls `request_security_action`.
2. AI calls `spawn_agent`.
3. AI calls `wait_for_completion` (the call will block until results are ready).
4. AI analyzes the findings from `audit/session_report.md`.

### 4. Review Results

```bash
# View the live assessment report
cat audit/session_report.md

# See artifacts (scans, logs)
ls -la audit/loot/
```

## 📚 Learn More

- **Architecture**: [README.md](README.md)
- **AI Operational Guide**: [GEMINI.md](GEMINI.md)
- **Skills Development**: [skills/TEMPLATE.md](skills/TEMPLATE.md)

## 🐛 Troubleshooting

**Address already in use?**
```bash
make clean && make start
```

**Agent can't reach server?**
Check `.env` and ensure `TASKMASTER_HOST` is accessible from Docker (e.g., `host.docker.internal` on macOS).
