#!/usr/bin/env bash
set -euo pipefail

# Taskmaster MCP Server Startup Script
# Starts the MCP server as a persistent HTTP server

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

echo "🚀 Starting Taskmaster MCP Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Server: server.py --http"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Warning: Port $PORT is already in use"
    echo "Kill existing process? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        lsof -ti :$PORT | xargs kill -9
        echo "✅ Killed existing process"
    else
        exit 1
    fi
fi

echo "Starting server..."
echo "Press Ctrl+C to stop"
echo ""

# Start the persistent HTTP server
uv run python server.py --http --host "$HOST" --port "$PORT"
