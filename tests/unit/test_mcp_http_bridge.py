"""Black-box tests for scripts/mcp-http-bridge.py.

The bridge is a standalone script (its filename has a hyphen, so it cannot be
imported); every test drives it as a subprocess against a stub Taskmaster
endpoint.  The invariant under test: whatever the server or the client does,
stdout carries only well-formed JSON-RPC, correlated to the request's id, so a
client never hangs waiting on a reply it can't match.
"""

import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest

BRIDGE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..", "scripts", "mcp-http-bridge.py")
)

PARSE_ERROR = -32700
INTERNAL_ERROR = -32603

REQUEST = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/list", "params": {}})
NOTIFICATION = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
VALID_RESPONSE = b'{"jsonrpc": "2.0", "id": 7, "result": {"tools": []}}'


class _Stub:
    """Mutable knobs the stub endpoint reads when answering."""

    def __init__(self):
        self.status = 200
        self.body = VALID_RESPONSE
        self.received = []
        self.port = None


@pytest.fixture
def stub():
    """Run a stub Taskmaster /mcp endpoint on an ephemeral port."""
    state = _Stub()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            state.received.append(self.rfile.read(length).decode())
            if state.status == 204:
                self.send_response(204)
                self.end_headers()
                return
            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(state.body)))
            self.end_headers()
            self.wfile.write(state.body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield state
    server.shutdown()
    server.server_close()


def _closed_port():
    """A port with nothing listening, for the unreachable-server cases."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _run_bridge(port, *lines, **env_extra):
    """Feed lines to the bridge on stdin; return (parsed stdout, stderr)."""
    env = dict(os.environ)
    env.update(
        {
            "TASKMASTER_HOST": "127.0.0.1",
            "TASKMASTER_PORT": str(port),
            "MCP_BRIDGE_TIMEOUT": "10",
        }
    )
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, BRIDGE],
        input="".join(f"{line}\n" for line in lines),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    messages = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return messages, proc.stderr


# --- happy path -------------------------------------------------------------


def test_valid_response_is_passed_through(stub):
    messages, _ = _run_bridge(stub.port, REQUEST)
    assert messages == [json.loads(VALID_RESPONSE)]
    assert json.loads(stub.received[0])["method"] == "tools/list"


def test_notification_gets_no_reply(stub):
    stub.status = 204
    messages, _ = _run_bridge(stub.port, NOTIFICATION)
    # JSON-RPC forbids answering a notification; the server still saw it.
    assert messages == []
    assert len(stub.received) == 1


def test_blank_lines_are_skipped(stub):
    messages, _ = _run_bridge(stub.port, "", "   ", REQUEST)
    assert len(messages) == 1
    assert len(stub.received) == 1


# --- client-side failures ---------------------------------------------------


def test_unparseable_line_returns_parse_error(stub):
    messages, _ = _run_bridge(stub.port, "this is not json")
    assert messages[0]["error"]["code"] == PARSE_ERROR
    assert messages[0]["id"] is None
    # Garbage is rejected locally rather than forwarded for the server to 400 on.
    assert stub.received == []


def test_loop_survives_a_bad_line(stub):
    messages, _ = _run_bridge(stub.port, "not json", REQUEST)
    assert messages[0]["error"]["code"] == PARSE_ERROR
    assert messages[1] == json.loads(VALID_RESPONSE)


# --- transport failures -----------------------------------------------------


def test_unreachable_server_returns_correlated_error():
    port = _closed_port()
    messages, stderr = _run_bridge(port, REQUEST)
    assert messages[0]["id"] == 7
    assert messages[0]["error"]["code"] == INTERNAL_ERROR
    assert str(port) in messages[0]["error"]["message"]
    assert "cannot reach" in stderr


def test_unreachable_server_stays_silent_for_notification():
    messages, stderr = _run_bridge(_closed_port(), NOTIFICATION)
    assert messages == []
    assert "cannot reach" in stderr


def test_invalid_timeout_env_falls_back_instead_of_crashing(stub):
    messages, stderr = _run_bridge(stub.port, REQUEST, MCP_BRIDGE_TIMEOUT="not-a-number")
    # A bad env var used to raise at import, killing the bridge pre-handshake.
    assert messages == [json.loads(VALID_RESPONSE)]
    assert "invalid MCP_BRIDGE_TIMEOUT" in stderr


# --- server-side failures ---------------------------------------------------


def test_http_error_with_non_jsonrpc_body_is_wrapped(stub):
    stub.status = 400
    stub.body = b'{"error": "Invalid JSON: boom"}'
    messages, _ = _run_bridge(stub.port, REQUEST)
    assert messages[0]["id"] == 7
    assert messages[0]["error"]["code"] == INTERNAL_ERROR
    assert "400" in messages[0]["error"]["message"]
    assert "Invalid JSON: boom" in messages[0]["error"]["data"]


def test_html_error_body_is_wrapped(stub):
    stub.status = 500
    stub.body = b"<html><body>500 Internal Server Error</body></html>"
    messages, _ = _run_bridge(stub.port, REQUEST)
    assert messages[0]["error"]["code"] == INTERNAL_ERROR
    assert "<html>" in messages[0]["error"]["data"]


def test_jsonrpc_error_body_passes_through_untouched(stub):
    stub.status = 500
    stub.body = b'{"jsonrpc": "2.0", "id": 7, "error": {"code": -32601, "message": "nope"}}'
    messages, _ = _run_bridge(stub.port, REQUEST)
    # The server's own code survives; the bridge must not relabel it.
    assert messages[0]["error"]["code"] == -32601
    assert messages[0]["error"]["message"] == "nope"


def test_204_for_a_request_unblocks_the_client(stub):
    stub.status = 204
    messages, _ = _run_bridge(stub.port, REQUEST)
    # Silence here would strand the client on a reply that never comes.
    assert messages[0]["id"] == 7
    assert messages[0]["error"]["code"] == INTERNAL_ERROR


def test_malformed_200_body_is_wrapped(stub):
    stub.body = b"not json at all"
    messages, _ = _run_bridge(stub.port, REQUEST)
    assert messages[0]["error"]["code"] == INTERNAL_ERROR
    assert "not json at all" in messages[0]["error"]["data"]


def test_non_jsonrpc_json_200_is_wrapped(stub):
    stub.body = b'{"status": "ok", "not": "jsonrpc"}'
    messages, _ = _run_bridge(stub.port, REQUEST)
    assert messages[0]["error"]["code"] == INTERNAL_ERROR
    assert "non-JSON-RPC" in messages[0]["error"]["message"]


def test_oversized_error_body_is_truncated(stub):
    stub.status = 500
    stub.body = b"x" * 9000
    messages, _ = _run_bridge(stub.port, REQUEST)
    data = messages[0]["error"]["data"]
    assert data.endswith("... (truncated)")
    assert len(data) < 9000


# --- the invariant ----------------------------------------------------------


@pytest.mark.parametrize(
    "status,body",
    [
        (400, b'{"error": "Invalid JSON"}'),
        (404, b'{"error": "Not found"}'),
        (500, b"<html>boom</html>"),
        (200, b"not json"),
        (200, b'{"plain": "json"}'),
        (204, b""),
    ],
)
def test_every_reply_to_a_request_is_correlated_jsonrpc(stub, status, body):
    stub.status = status
    stub.body = body
    messages, _ = _run_bridge(stub.port, REQUEST)
    assert len(messages) == 1
    assert messages[0]["jsonrpc"] == "2.0"
    assert messages[0]["id"] == 7
