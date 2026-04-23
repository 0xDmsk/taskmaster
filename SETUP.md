# Taskmaster Setup Guide

Complete setup guide for getting Taskmaster up and running.

## 📋 Prerequisites

### Required Software

1. **Python 3.12+**
   ```bash
   python3 --version
   ```

2. **UV Package Manager**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Container Runtime** (Docker or Podman)
   ```bash
   # macOS (Docker Desktop recommended)
   brew install docker

   # Alternative: Podman
   brew install podman
   podman machine init
   podman machine start
   ```

4. **Socat** (for MCP bridge)
   ```bash
   brew install socat
   ```

### Optional Tools

- **SecLists** wordlists:
  ```bash
  git clone https://github.com/danielmiessler/SecLists.git ~/seclists
  ```

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd taskmaster
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to match your setup:
```bash
# Docker Desktop (macOS/Windows) — use the built-in DNS name:
TASKMASTER_HOST=host.docker.internal
TASKMASTER_PORT=5000

# Linux — use the docker0 bridge IP instead:
# TASKMASTER_HOST=172.17.0.1
```

**Finding your container-accessible host IP:**

**macOS / Windows (Docker Desktop):**
```bash
# Docker Desktop provides this automatically — no extra config needed
TASKMASTER_HOST=host.docker.internal
```

**Linux:**
```bash
# Find the docker0 bridge IP
ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
```

### 3. Install Python Dependencies

```bash
uv sync
```

### 4. Initialize Directories

```bash
# Create required directories
mkdir -p audit/loot state

# Verify structure
tree -L 2
```

### 5. Build the Agent Container(s)

```bash
# Kali executor (CLI pentesting tools)
make build

# Playwright executor (browser-based testing, optional)
make build-playwright
```

`make build` builds the `kali-smart-operator` image (~2-3 GB, takes 5-10 minutes on first build).

**Verify the builds:**
```bash
docker images | grep -E 'kali-smart-operator|playwright-operator'
```

## 🧪 Testing the Installation

### 1. Run Unit Tests

```bash
make test
```

Or directly with UV:
```bash
uv run pytest tests/
```

### 2. Start the MCP Server

In Terminal 1:
```bash
make start
```

### 3. Test MCP Connection

In Terminal 2, test with a simple tool call:
```bash
curl -s -X POST http://localhost:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Expected response: a JSON object listing all available Taskmaster tools.

### 4. Spawn a Test Agent

In Terminal 3:
```bash
make spawn
```

This opens an interactive Kali agent container. Try:
```bash
# Inside the container
operator  # Start the agent polling loop
# Or run commands manually
nmap --version
ffuf -V
```

## 🔧 Integration with Gemini

### Using with Gemini CLI

Taskmaster is designed to be controlled by Gemini (or other LLMs) via the MCP protocol.

1. **Configure Gemini CLI**:
   ```bash
   # Copy the example configuration
   cp examples/gemini-cli-settings.json ~/.gemini/settings.json

   # Edit if needed (adjust host IP)
   nano ~/.gemini/settings.json
   ```

2. **Start Taskmaster server**:
   ```bash
   ./scripts/start-server.sh
   ```

3. **Verify connection**:
   ```bash
   gemini-cli tools list
   # Should show: request_security_action, spawn_agent, etc.
   ```

4. **Provide Context**: Share `GEMINI.md` as context for the AI agent

5. **Start Assessment**: Use natural language to request security actions:
   ```
   "Perform reconnaissance on target 10.0.0.15, looking for open ports and services"
   ```

**See `examples/EXAMPLES.md` for detailed MCP client configuration options.**

### Workflow Example

The typical agentic workflow:

1. **Gemini requests an action** via `request_security_action`
   - Specifies target, phase, tool, command
   - Provides justification for audit trail

2. **Taskmaster queues the execution**
   - Validates phase transitions
   - Checks target locking
   - Returns execution_id

3. **Gemini spawns an agent** via `spawn_agent`
   - Provides structured mission
   - Agent auto-starts and polls for work

4. **Agent executes task**
   - Claims the execution
   - Runs the command
   - Saves artifacts to `/loot`
   - Reports results back

5. **Gemini reviews results**
   - Calls `wait_for_completion` to block until the execution finishes
   - Reads structured data from the result
   - Plans next action

## 📂 Directory Structure

After setup, your directory should look like:

```
taskmaster/
├── audit/
│   ├── audit_log.jsonl      # Event log
│   ├── session_report.md    # Assessment report
│   └── loot/                # Artifacts from agents
│       └── .gitkeep
├── executors/
│   ├── Dockerfile
│   ├── kali_operator.py
│   └── ...
├── policies/
│   ├── agent_mission_template.md
│   └── state_policy.py
├── scripts/
│   ├── build.sh
│   ├── start-server.sh
│   ├── spawn-agent.sh
│   └── test.sh
├── skills/
│   ├── base.py
│   ├── subdomain.py
│   ├── cloud.py
│   └── ...
├── state/
│   ├── executions.json      # Runtime state (auto-created)
│   ├── state.py
│   └── storage.py
├── tools/
│   ├── request_security_action.py
│   ├── spawn_agent.py
│   └── ...
├── .env                     # Your local config
├── .gitignore
├── pyproject.toml
├── server.py                # MCP server entry point
└── README.md
```

## 🔍 Troubleshooting

### Port Already in Use

```bash
# Find and kill the process
lsof -ti :5000 | xargs kill -9

# Or use a different port in .env
TASKMASTER_PORT=5001
```

### Container Can't Reach Host

**macOS / Windows (Docker Desktop):**
```bash
TASKMASTER_HOST=host.docker.internal
```

**Linux:**
```bash
# Use the docker0 bridge IP
ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
```

### Agent Build Fails

```bash
# Clear Docker cache
docker system prune -a

# Rebuild
./scripts/build.sh
```

### Dependencies Not Found

```bash
# Reinstall
rm -rf .venv
uv sync
```

## 🎯 Next Steps

1. **Read the operational guide**: See `GEMINI.md` for agent workflows
2. **Review skills**: Check `skills/` directory for available capabilities
3. **Create custom skills**: Use `skills/TEMPLATE.md` as a starting point
4. **Set up authorization**: Ensure you have proper authorization before testing any targets
5. **Read security policy**: Review `SECURITY.md` for ethical guidelines

## 💡 Tips

- **Use absolute paths** in `.env` if relative paths cause issues
- **Mount wordlists** to avoid downloading in containers (see `spawn-agent.sh`)
- **Keep audit logs** for compliance and documentation
- **Clean up containers** regularly: `docker container prune`
- **Update base image** periodically: rebuild with latest Kali packages

## 📚 Additional Resources

- [README.md](README.md) - Architecture overview
- [GEMINI.md](GEMINI.md) - Operational guide for AI agents
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
- [SECURITY.md](SECURITY.md) - Security and ethics

## 🆘 Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review logs in `audit/audit_log.jsonl`
3. Test components individually (server, agent, tools)
4. Open an issue on GitHub with details
