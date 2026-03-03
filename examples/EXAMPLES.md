# Taskmaster MCP Client Configuration Examples

This directory contains example configuration files for connecting various MCP clients to Taskmaster.

## 📋 Available Examples

### 1. Gemini CLI Configuration

**File**: `gemini-cli-settings.json`

For Google's Gemini CLI tool. Place this in your Gemini CLI configuration directory.

**Installation**:
```bash
# Copy to Gemini CLI config directory
cp examples/gemini-cli-settings.json ~/.gemini/settings.json

# Or merge with existing config
cat examples/gemini-cli-settings.json >> ~/.gemini/settings.json
```

**Features**:
- Global shortcuts for common tools
- Auto-approve settings
- Context sharing enabled

### 2. Claude Desktop Configuration

**File**: `claude-desktop-config.json`

For Anthropic's Claude Desktop application.

**macOS Installation**:
```bash
# Copy to Claude Desktop config
cp examples/claude-desktop-config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux Installation**:
```bash
# Copy to Claude Desktop config
cp examples/claude-desktop-config.json ~/.config/Claude/claude_desktop_config.json
```

### 3. STDIO Direct Connection

For MCP clients that support direct STDIO connection (no network needed).

**Note**: Update the paths with your actual username and project location.

```json
{
  "command": "uv",
  "args": ["run", "python", "/path/to/taskmaster/server.py"]
}
```

## 🔧 Connection Modes

### HTTP Bridge (Recommended for network access)

Uses the STDIO-to-HTTP bridge script to connect MCP clients to a running Taskmaster HTTP server. No external dependencies required (stdlib only).

**Pros**:
- Server runs persistently — no cold start per request
- Handles multiple clients simultaneously
- No socat or external tools required
- Easy to debug with curl

**Cons**:
- Server must be started separately

**Configuration**:
```json
{
  "mcpServers": {
    "taskmaster": {
      "command": "python3",
      "args": ["/path/to/taskmaster/scripts/mcp-http-bridge.py"],
      "env": {
        "TASKMASTER_HOST": "192.168.64.1",
        "TASKMASTER_PORT": "5000"
      }
    }
  }
}
```

**Prerequisites**:
1. Start Taskmaster server: `./scripts/start-server.sh`
2. Python 3 (no extra packages needed)

### STDIO Direct Connection

**Pros**:
- No extra dependencies
- Simpler setup
- Client automatically starts/stops server

**Cons**:
- One client at a time
- Server lifecycle tied to client

**Configuration**:
```json
{
  "mcpServers": {
    "taskmaster": {
      "command": "uv",
      "args": ["run", "python", "/path/to/server.py"],
      "cwd": "/path/to/taskmaster"
    }
  }
}
```

**Prerequisites**:
1. Install UV: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Update paths in config

## 🌐 Network Configuration

### Finding Your Host IP

The `TASKMASTER_HOST` should be the IP that Docker containers can use to reach your host machine.

**macOS with Docker Desktop**:
```bash
# Use the special DNS name
host.docker.internal

# Or find the IP
ipconfig getifaddr en0
```

**macOS with Lima/Colima**:
```bash
# Typically 192.168.64.1
limactl shell default ip route show default | awk '/default/ {print $3}'
```

**Linux**:
```bash
# Find docker0 bridge IP
ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
```

### Testing Connection

```bash
# Test if HTTP server is reachable
curl -s -X POST http://192.168.64.1:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Expected response: JSON with tools list

# Test the bridge script
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 scripts/mcp-http-bridge.py
```

## 📝 Environment Variables

All configurations support these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TASKMASTER_HOST` | `192.168.64.1` | Host IP for server |
| `TASKMASTER_PORT` | `5000` | TCP port for server |
| `TASKMASTER_WORK_DIR` | (cwd) | Assessment output directory |
| `HTTP_PROXY` | — | Proxy URL passed to agent containers |
| `SECLISTS_PATH` | — | Host path to SecLists wordlists |
| `MCP_BRIDGE_TIMEOUT` | `900` | HTTP bridge read timeout (seconds) |

## 🚀 Quick Setup Guide

### For Gemini CLI

1. **Start Taskmaster server**:
   ```bash
   cd /path/to/taskmaster
   make start
   ```

2. **Configure Gemini CLI**:
   ```bash
   # Update the absolute bridge script path and host IP in settings.json
   # Copy to Gemini config
   cp examples/gemini-cli-settings.json ~/.gemini/settings.json
   ```

3. **Test connection**:
   ```bash
   gemini-cli tools list
   # Should show Taskmaster tools including wait_for_completion
   ```

4. **Start using**:
   ```bash
   gemini-cli chat
   > "Perform reconnaissance on target 10.0.0.1"
   # The AI will now: 
   # 1. request_security_action
   # 2. spawn_agent
   # 3. wait_for_completion (blocks until result is ready)
   ```

### For Claude Desktop

1. **Start Taskmaster server**:
   ```bash
   make start
   ```

2. **Install config**:
   ```bash
   # Update absolute path in examples/claude-desktop-config.json first!
   cp examples/claude-desktop-config.json \
      ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Restart Claude Desktop**

4. **Verify**: Look for Taskmaster tools in Claude's tool menu

## 🔍 Troubleshooting

### "Connection refused"

**Problem**: Client can't connect to server

**Solutions**:
1. Ensure server is running: `lsof -i :5000`
2. Check firewall settings
3. Verify host IP is correct
4. Try `127.0.0.1` if on same machine

### "Command not found: uv"

**Problem**: UV not installed

**Solution**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # or ~/.bashrc
```

### "Invalid JSON" errors

**Problem**: Server returning errors

**Solutions**:
1. Check server logs
2. Verify JSON syntax in client messages
3. Test with curl:
   ```bash
   curl -X POST http://192.168.64.1:5000/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize"}'
   ```

### Tools not showing up

**Problem**: MCP client doesn't see Taskmaster tools

**Solutions**:
1. Restart the MCP client
2. Check client logs for errors
3. Verify server is responding with curl (see above)
4. Test initialization handshake

## 📚 Additional Resources

- **Gemini CLI**: Share `GEMINI.md` as context
- **Tool Schemas**: See `tools/*.json` for detailed schemas
- **MCP Protocol**: https://modelcontextprotocol.io
- **Taskmaster Docs**: See `README.md` and `SETUP.md`

## 💡 Tips

1. **Multiple Clients**: HTTP mode allows multiple clients simultaneously
2. **Development**: Use STDIO mode for debugging (easier to see errors)
3. **Production**: Use HTTP mode for stability
4. **Security**: Only bind to localhost unless you need network access
5. **Context**: Always provide `GEMINI.md` to AI agents for best results

## 🔐 Security Notes

1. **Network Exposure**: Only bind to localhost (`127.0.0.1`) unless needed
2. **Authorization**: Ensure proper authorization before security testing
3. **Audit Logs**: Always review `audit/audit_log.jsonl` after sessions
4. **Credentials**: Never commit API keys or credentials to config files

## 🆘 Getting Help

If you encounter issues:

1. Check `SETUP.md` for detailed setup instructions
2. Review server logs: `tail -f audit/audit_log.jsonl`
3. Test with curl: `curl -X POST http://HOST:PORT/mcp -H "Content-Type: application/json" -d '...'`
4. Open a GitHub issue with configuration and error details
