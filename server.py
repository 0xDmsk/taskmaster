import argparse
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

import config
from tools.request_security_action import handle_request
from tools.query_execution_status import handle_query_execution_status
from tools.fetch_execution_result import handle_fetch_execution_result
from tools.mark_execution_complete import handle_mark_execution_complete
from tools.claim_execution import handle_claim_execution
from tools.start_execution import handle_start_execution
from tools.complete_execution import handle_complete_execution
from tools.fail_execution import handle_fail_execution
from tools.list_queued_executions import handle_list_queued_executions
from tools.spawn_agent import handle_spawn_agent
from tools.cleanup_agents import handle_cleanup_agents
from tools.recover_execution import handle_recover_execution
from tools.wait_for_completion import handle_wait_for_completion


def load_tool_schema(tool_name):
    """Load tool schema from JSON file if it exists."""
    schema_path = os.path.join(config.PROJECT_DIR, "tools", f"{tool_name}.json")
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            return json.load(f)
    return None


TOOLS = {
    "request_security_action": {
        "description": (
            "Request execution of a security-related action. Commands are validated "
            "against macOS VM platform constraints — raw-socket scans (nmap -sS, -sU, "
            "-O) are blocked. Use nmap -sT."
        ),
        "handler": handle_request,
        "schema": load_tool_schema("request_security_action"),
    },
    "spawn_agent": {
        "description": "Spawn a new Kali agent container for a specific target or task",
        "handler": handle_spawn_agent,
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP, hostname, or URL to assign to the agent",
                },
                "mission": {
                    "type": "string",
                    "description": "Mission briefing text for the agent",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Custom agent/container name (auto-generated if omitted)",
                },
                "taskmaster_host": {
                    "type": "string",
                    "description": "Override Taskmaster host IP",
                },
                "taskmaster_port": {
                    "type": "string",
                    "description": "Override Taskmaster port",
                },
                "proxy_url": {
                    "type": "string",
                    "description": "HTTP proxy URL for the container",
                },
            },
        },
    },
    "query_execution_status": {
        "description": "Get current status of an execution by execution_id",
        "handler": handle_query_execution_status,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "The execution ID to query",
                },
            },
        },
    },
    "fetch_execution_result": {
        "description": "Fetch result for a completed/failed execution",
        "handler": handle_fetch_execution_result,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "The execution ID to fetch results for",
                },
            },
        },
    },
    "mark_execution_complete": {
        "description": "Mark an execution as completed or failed (generic)",
        "handler": handle_mark_execution_complete,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
                "result": {
                    "type": "string",
                    "description": "Result text or error info",
                },
                "status": {
                    "type": "string",
                    "enum": ["COMPLETED", "FAILED"],
                    "description": "Target status (default: COMPLETED)",
                },
            },
        },
    },
    "claim_execution": {
        "description": "Transition QUEUED -> CLAIMED and bind executor_id",
        "handler": handle_claim_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {
                    "type": "string",
                    "description": "ID of the agent claiming this execution",
                },
            },
        },
    },
    "start_execution": {
        "description": "Transition CLAIMED -> RUNNING (enforces target locking)",
        "handler": handle_start_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
            },
        },
    },
    "complete_execution": {
        "description": "Transition RUNNING -> COMPLETED and attach results",
        "handler": handle_complete_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
                "result": {
                    "type": "string",
                    "description": "Execution output / findings",
                },
            },
        },
    },
    "fail_execution": {
        "description": "Transition RUNNING -> FAILED and attach error info",
        "handler": handle_fail_execution,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id", "executor_id"],
            "properties": {
                "execution_id": {"type": "string"},
                "executor_id": {"type": "string"},
                "error_info": {
                    "type": "string",
                    "description": "Error description or traceback",
                },
            },
        },
    },
    "list_queued_executions": {
        "description": "List all executions in QUEUED status",
        "handler": handle_list_queued_executions,
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Optional target filter",
                },
            },
        },
    },
    "cleanup_agents": {
        "description": "Stop and remove one or more agent containers by target, ID, or state",
        "handler": handle_cleanup_agents,
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Cleanup agents assigned to this target",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Cleanup a specific agent by name",
                },
                "all": {
                    "type": "boolean",
                    "description": "Cleanup all kali-agent containers",
                },
                "state": {
                    "type": "string",
                    "enum": ["running", "stopped"],
                    "description": "Filter by container state",
                },
            },
        },
    },
    "recover_execution": {
        "description": (
            "Recover stuck executions. Provide execution_id for single recovery, "
            "or set recover_stale=true to bulk-fail executions stuck longer than "
            "timeout_minutes (default 30)."
        ),
        "handler": handle_recover_execution,
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "Specific execution to recover",
                },
                "recover_stale": {
                    "type": "boolean",
                    "description": "Bulk-recover all stale executions",
                },
                "timeout_minutes": {
                    "type": "integer",
                    "description": "Staleness threshold in minutes (default: 30)",
                },
                "reason": {
                    "type": "string",
                    "description": "Recovery reason for audit log",
                },
            },
        },
    },
    "wait_for_completion": {
        "description": (
            "Block until an execution reaches COMPLETED or FAILED (or timeout). "
            "Eliminates polling — call once, get the result when ready."
        ),
        "handler": handle_wait_for_completion,
        "inputSchema": {
            "type": "object",
            "required": ["execution_id"],
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "The execution ID to wait on",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Max seconds to wait (default: 600 = 10 min)",
                },
            },
        },
    },
}


def _get_input_schema(tool):
    """Return the inputSchema for a tool, checking schema file then inline then default."""
    if tool.get("schema") and "inputSchema" in tool["schema"]:
        return tool["schema"]["inputSchema"]
    if tool.get("inputSchema"):
        return tool["inputSchema"]
    return {"type": "object", "properties": {}}


def dispatch(message):
    """Dispatch a parsed JSON message and return a response dict.

    Handles both JSON-RPC 2.0 (MCP protocol) and legacy message formats.
    Returns None for notifications that require no response.
    """
    # Handle JSON-RPC 2.0 format (MCP protocol)
    if "jsonrpc" in message and message.get("jsonrpc") == "2.0":
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})

        logging.info(f"JSON-RPC method: {method}, id: {msg_id}")

        # Handle notifications (no id = no response expected)
        if msg_id is None:
            if method and method.startswith("notifications/"):
                logging.info(f"Received notification: {method} (no response needed)")
            else:
                logging.warning(f"Received JSON-RPC message without id: {method}")
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "taskmaster", "version": "0.2.0"},
                    "capabilities": {"tools": {}},
                },
            }

        elif method == "tools/list":
            tools_list = []
            for name, tool in TOOLS.items():
                tools_list.append(
                    {
                        "name": name,
                        "description": tool["description"],
                        "inputSchema": _get_input_schema(tool),
                    }
                )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools_list},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name not in TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }
            try:
                result = TOOLS[tool_name]["handler"](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    },
                }
            except Exception as e:
                logging.error(f"Tool execution error: {e}", exc_info=True)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    # Handle legacy format (for backwards compatibility with tests)
    if message.get("type") == "initialize":
        tools_list = []
        for name, tool in TOOLS.items():
            tool_def = {"name": name, "description": tool["description"]}
            schema = _get_input_schema(tool)
            if schema.get("properties"):
                tool_def["inputSchema"] = schema
            tools_list.append(tool_def)

        return {
            "type": "initialize_response",
            "protocolVersion": "1.0.0",
            "serverInfo": {"name": "taskmaster", "version": "0.2.0"},
            "capabilities": {"tools": {}},
            "tools": tools_list,
        }

    if message.get("type") == "tool_call":
        tool_name = message.get("tool")
        payload = message.get("arguments", {})

        if tool_name not in TOOLS:
            return {"error": f"Unknown tool: {tool_name}"}

        result = TOOLS[tool_name]["handler"](payload)
        return {"type": "tool_result", "tool": tool_name, "result": result}

    return {"error": "Unknown message type"}


# ---------------------------------------------------------------------------
# HTTP mode — persistent server using stdlib http.server
# ---------------------------------------------------------------------------


class TaskmasterHTTPHandler(BaseHTTPRequestHandler):
    """Handle POST /mcp requests by dispatching JSON body through dispatch()."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            message = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {"error": f"Invalid JSON: {e}"})
            return

        logging.debug(f"HTTP received: {message}")
        response = dispatch(message)

        if response is None:
            # Notification — no response body expected, send 204
            self.send_response(204)
            self.end_headers()
        else:
            self._send_json(200, response)

    def _send_json(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        """Route http.server logs through the logging module."""
        logging.info(format % args)


def run_http(host, port):
    """Start a persistent HTTP server."""
    server = ThreadingHTTPServer((host, port), TaskmasterHTTPHandler)
    logging.info(f"Taskmaster HTTP server listening on {host}:{port}")
    print(f"Taskmaster HTTP server listening on {host}:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down HTTP server")
        server.server_close()


# ---------------------------------------------------------------------------
# STDIO mode — original line-based JSON protocol
# ---------------------------------------------------------------------------


def _send_stdio(response):
    output = json.dumps(response) + "\n"
    logging.debug(f"Sending: {output.strip()}")
    sys.stdout.write(output)
    sys.stdout.flush()


def run_stdio():
    """Run the server in STDIO mode (MCP transport)."""
    logging.info("Taskmaster MCP server starting (STDIO mode)...")

    for line in sys.stdin:
        logging.debug(f"Received: {line.strip()}")

        try:
            message = json.loads(line)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            _send_stdio({"error": "Invalid JSON"})
            continue

        logging.debug(f"Parsed message: {message}")

        response = dispatch(message)
        if response is not None:
            _send_stdio(response)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Taskmaster MCP Server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as a persistent HTTP server instead of STDIO",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("TASKMASTER_HOST", "0.0.0.0"),
        help="HTTP server bind address (default: $TASKMASTER_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("TASKMASTER_PORT", "5000")),
        help="HTTP server port (default: $TASKMASTER_PORT or 5000)",
    )
    args = parser.parse_args()

    if args.http:
        run_http(args.host, args.port)
    else:
        run_stdio()


if __name__ == "__main__":
    main()
