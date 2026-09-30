#!/usr/bin/env python3
"""STDIO-to-HTTP bridge for MCP clients.

Reads JSON-RPC messages from stdin, forwards them to a Taskmaster HTTP server,
and writes responses to stdout.  Drop-in replacement for the socat-based bridge.

Every byte written to stdout is a well-formed JSON-RPC message: when the bridge
cannot reach the server, or the server answers with something that is not
JSON-RPC (a 400/404 body, an HTML error page), the failure is wrapped in a
JSON-RPC error carrying the originating request's ``id`` so the client can
correlate it instead of hanging.  Diagnostics go to stderr, never stdout.

Usage (MCP client config):
    {
        "command": "python3",
        "args": ["/path/to/taskmaster/scripts/mcp-http-bridge.py"],
        "env": {
            "TASKMASTER_HOST": "127.0.0.1",
            "TASKMASTER_PORT": "5000"
        }
    }
"""

import json
import os
import sys
import urllib.error
import urllib.request

HOST = os.environ.get("TASKMASTER_HOST", "127.0.0.1")
PORT = os.environ.get("TASKMASTER_PORT", "5000")
URL = f"http://{HOST}:{PORT}/mcp"

DEFAULT_TIMEOUT = 900

# JSON-RPC 2.0 reserved error codes.
PARSE_ERROR = -32700
INTERNAL_ERROR = -32603

# Cap on foreign error bodies echoed back in ``error.data``.
MAX_DATA_CHARS = 2000


def log(message):
    """Write a diagnostic to stderr; stdout is reserved for JSON-RPC."""
    print(f"[mcp-http-bridge] {message}", file=sys.stderr, flush=True)


def resolve_timeout():
    """Read MCP_BRIDGE_TIMEOUT, falling back rather than dying on bad input."""
    raw = os.environ.get("MCP_BRIDGE_TIMEOUT")
    if raw is None:
        return DEFAULT_TIMEOUT
    try:
        timeout = int(raw)
    except ValueError:
        log(f"invalid MCP_BRIDGE_TIMEOUT={raw!r}, using {DEFAULT_TIMEOUT}s")
        return DEFAULT_TIMEOUT
    if timeout <= 0:
        log(f"non-positive MCP_BRIDGE_TIMEOUT={raw!r}, using {DEFAULT_TIMEOUT}s")
        return DEFAULT_TIMEOUT
    return timeout


BRIDGE_TIMEOUT = resolve_timeout()


def emit(text):
    """Write one JSON-RPC message to stdout."""
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def emit_error(request_id, code, message, data=None):
    """Emit a JSON-RPC error response correlated to ``request_id``."""
    error = {"code": code, "message": message}
    if data is not None:
        text = data if isinstance(data, str) else repr(data)
        if len(text) > MAX_DATA_CHARS:
            text = text[:MAX_DATA_CHARS] + "... (truncated)"
        error["data"] = text
    emit(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": error}))


def post(payload):
    """POST one raw JSON-RPC line to the server; return (status, body)."""
    request = urllib.request.Request(
        URL,
        data=payload.encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=BRIDGE_TIMEOUT) as response:
        if response.status == 204:
            return 204, ""
        return response.status, response.read().decode()


def handle(line):
    """Forward one stdin line and emit whatever the client is owed."""
    try:
        message = json.loads(line)
    except (json.JSONDecodeError, ValueError) as e:
        log(f"unparseable line from client: {e}")
        emit_error(None, PARSE_ERROR, f"Parse error: {e}")
        return

    # A notification has no "id" and, per JSON-RPC 2.0, must never be answered.
    is_notification = isinstance(message, dict) and "id" not in message
    request_id = message.get("id") if isinstance(message, dict) else None
    method = message.get("method", "?") if isinstance(message, dict) else "?"

    try:
        status, body = post(line)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        log(f"HTTP {e.code} from server for {method}: {body[:200]}")
        if is_notification:
            return
        # Pass through a genuine JSON-RPC error; wrap anything else.
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, dict) and "jsonrpc" in parsed:
            emit(body)
        else:
            emit_error(
                request_id,
                INTERNAL_ERROR,
                f"Taskmaster returned HTTP {e.code} for {method}",
                data=body,
            )
        return
    except Exception as e:
        log(f"cannot reach {URL} for {method}: {e!r}")
        if is_notification:
            return
        emit_error(
            request_id,
            INTERNAL_ERROR,
            f"Bridge could not reach Taskmaster at {URL}: {e}",
        )
        return

    if status == 204:
        # Expected for notifications; for a request it would hang the client.
        if not is_notification:
            log(f"server sent 204 (no content) for request id={request_id!r} {method}")
            emit_error(
                request_id,
                INTERNAL_ERROR,
                f"Taskmaster returned no response for {method}",
            )
        return

    # Never let a non-JSON-RPC 200 body reach the client's parser.
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, ValueError) as e:
        log(f"non-JSON 200 body for {method}: {body[:200]}")
        if not is_notification:
            emit_error(
                request_id,
                INTERNAL_ERROR,
                f"Taskmaster returned a malformed response for {method}: {e}",
                data=body,
            )
        return

    if is_notification:
        log(f"discarding unexpected response body for notification {method}")
        return

    if not (isinstance(parsed, dict) and "jsonrpc" in parsed) and not isinstance(parsed, list):
        log(f"200 body is JSON but not JSON-RPC for {method}: {body[:200]}")
        emit_error(
            request_id,
            INTERNAL_ERROR,
            f"Taskmaster returned a non-JSON-RPC response for {method}",
            data=body,
        )
        return

    emit(body)


def main():
    log(f"bridging stdio to {URL} (timeout {BRIDGE_TIMEOUT}s)")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        handle(line)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
