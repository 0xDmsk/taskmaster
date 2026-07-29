#!/usr/bin/env bash
set -euo pipefail

# Taskmaster MCP Server Startup Script (Debug Mode)
# Starts the server with debug logging to see what clients are sending

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "📄 Loading environment from .env"
    export $(grep -v '^#' .env | xargs)
fi

PORT="${TASKMASTER_PORT:-5000}"
HOST="${TASKMASTER_HOST:-0.0.0.0}"
DASHBOARD_HOST="${TASKMASTER_DASHBOARD_HOST:-127.0.0.1}"
DASHBOARD_PORT="${TASKMASTER_DASHBOARD_PORT:-5001}"

echo "🐛 Starting Taskmaster MCP Server (DEBUG MODE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "MCP endpoint:  http://$HOST:$PORT"
echo "Dashboard:     http://$DASHBOARD_HOST:$DASHBOARD_PORT  (loopback only)"
echo "Debug logs will appear below"
echo ""

# Kill existing process if running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Killing existing process on port $PORT..."
    lsof -ti :$PORT | xargs kill -9
    sleep 1
fi

echo "Starting server with debug logging..."
echo "Press Ctrl+C to stop"
echo ""

# Start the persistent HTTP server (stderr debug logs show inline)
uv run python server.py --http --host "$HOST" --port "$PORT" \
    --dashboard-host "$DASHBOARD_HOST" --dashboard-port "$DASHBOARD_PORT" 2>&1
