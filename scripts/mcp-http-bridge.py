#!/usr/bin/env python3
"""STDIO-to-HTTP bridge for MCP clients.

Reads JSON-RPC messages from stdin, forwards them to a Taskmaster HTTP server,
and writes responses to stdout.  Drop-in replacement for the socat-based bridge.

Usage (MCP client config):
    {
        "command": "python3",
        "args": ["/path/to/taskmaster/scripts/mcp-http-bridge.py"],
        "env": {
            "TASKMASTER_HOST": "192.168.64.1",
            "TASKMASTER_PORT": "5000"
        }
    }
"""
import json
import os
import sys
import urllib.request
import urllib.error

HOST = os.environ.get("TASKMASTER_HOST", "192.168.64.1")
PORT = os.environ.get("TASKMASTER_PORT", "5000")
URL = f"http://{HOST}:{PORT}/mcp"
BRIDGE_TIMEOUT = int(os.environ.get("MCP_BRIDGE_TIMEOUT", "900"))

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = urllib.request.Request(
            URL,
            data=line.encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=BRIDGE_TIMEOUT) as resp:
            # 204 No Content for notifications
            if resp.status == 204:
                continue
            sys.stdout.write(resp.read().decode() + "\n")
            sys.stdout.flush()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        sys.stdout.write(error_body + "\n")
        sys.stdout.flush()
    except Exception as e:
        error_resp = json.dumps({"error": f"Bridge connection failed: {e}"})
        sys.stdout.write(error_resp + "\n")
        sys.stdout.flush()
