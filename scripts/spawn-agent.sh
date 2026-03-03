#!/usr/bin/env bash
set -euo pipefail

# Quick Agent Spawn Helper
# Spawns a Kali agent container connected to Taskmaster

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

IMAGE_NAME="${AGENT_IMAGE_NAME:-kali-smart-operator}"
TASKMASTER_HOST="${TASKMASTER_HOST:-192.168.64.1}"
TASKMASTER_PORT="${TASKMASTER_PORT:-5000}"
LOOT_DIR="${LOOT_DIR:-$PROJECT_ROOT/audit/loot}"
SKILLS_DIR="${SKILLS_DIR:-$PROJECT_ROOT/skills}"

# Generate unique agent name
AGENT_NAME="kali-agent-$(date +%s | tail -c 5)"

echo "🤖 Spawning Taskmaster Agent"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Agent Name: $AGENT_NAME"
echo "Image: $IMAGE_NAME"
echo "Taskmaster: $TASKMASTER_HOST:$TASKMASTER_PORT"
echo ""

# Detect container runtime
if command -v container &> /dev/null; then
    RUNTIME="container"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
elif command -v podman &> /dev/null; then
    RUNTIME="podman"
else
    echo "❌ Error: No container runtime found (container, docker, or podman)"
    exit 1
fi

# Ensure directories exist
mkdir -p "$LOOT_DIR"

# Optional: Mount seclists if available
SECLISTS_MOUNT=""
if [ -n "${SECLISTS_PATH:-}" ] && [ -d "$SECLISTS_PATH" ]; then
    SECLISTS_MOUNT="-v $SECLISTS_PATH:/usr/share/seclists:ro"
    echo "📚 Mounting SecLists from: $SECLISTS_PATH"
fi

echo "Starting container..."
echo ""

# Run the container interactively
$RUNTIME run -it --rm \
    --name "$AGENT_NAME" \
    -e TASKMASTER_HOST="$TASKMASTER_HOST" \
    -e TASKMASTER_PORT="$TASKMASTER_PORT" \
    -v "$LOOT_DIR:/loot:rw" \
    -v "$SKILLS_DIR:/skills:ro" \
    $SECLISTS_MOUNT \
    "$IMAGE_NAME:latest" \
    /usr/bin/zsh

echo ""
echo "✅ Agent session ended"
