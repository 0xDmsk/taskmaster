#!/usr/bin/env bash
set -euo pipefail

# Taskmaster Cleanup Script
# Removes runtime state, logs, and stopped containers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Honor TASKMASTER_WORK_DIR if the server was launched against a per-engagement
# folder. Falls back to the project root, which matches the in-place dev flow.
WORK_DIR="${TASKMASTER_WORK_DIR:-$PROJECT_ROOT}"
cd "$WORK_DIR"

echo "🧹 Taskmaster Cleanup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect container runtime
if command -v docker &> /dev/null; then
    RUNTIME="docker"
elif command -v podman &> /dev/null; then
    RUNTIME="podman"
else
    echo "⚠️  No container runtime found, skipping container cleanup"
    RUNTIME=""
fi

# Clean up containers
if [ -n "$RUNTIME" ]; then
    echo "Stopping and removing Taskmaster agent containers..."
    # Match both kali-agent-* and playwright-agent-* containers
    for filter in "name=kali-agent" "name=playwright-agent"; do
        $RUNTIME ps -a --filter "$filter" --format "{{.Names}}" | while read -r container; do
            if [ -n "$container" ]; then
                echo "  Removing: $container"
                $RUNTIME rm -f "$container" 2>/dev/null || true
            fi
        done
    done
    echo "✅ Containers cleaned"
    echo ""
fi

# Ask before cleaning state
echo "Clean runtime state? (y/n)"
echo "  - runtime/state/executions.db (+ -wal, -shm)"
echo "  - runtime/audit/audit_log.jsonl"
echo "  - runtime/audit/session_report.md"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Cleaning state files..."
    rm -f runtime/state/executions.db runtime/state/executions.db-wal runtime/state/executions.db-shm
    rm -f runtime/audit/audit_log.jsonl
    rm -f runtime/audit/session_report.md
    echo "✅ State cleaned"
else
    echo "⏭️  Skipping state cleanup"
fi
echo ""

# Ask before cleaning loot and reports
echo "Clean loot and reports? (y/n)"
echo "  - runtime/loot/*"
echo "  - runtime/reports/*"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Cleaning loot and reports..."
    rm -rf runtime/loot/*
    rm -rf runtime/reports/*
    touch runtime/loot/.gitkeep
    touch runtime/reports/.gitkeep
    echo "✅ Loot and reports cleaned"
else
    echo "⏭️  Skipping loot/reports cleanup"
fi
echo ""

# Ask before cleaning Python cache
echo "Clean Python cache? (y/n)"
echo "  - __pycache__/"
echo "  - *.pyc"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Cleaning Python cache..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "✅ Python cache cleaned"
else
    echo "⏭️  Skipping cache cleanup"
fi
echo ""

echo "🎉 Cleanup complete!"
