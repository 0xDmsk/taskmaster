#!/usr/bin/env bash
set -euo pipefail

# Taskmaster Cleanup Script
# Removes runtime state, logs, and stopped containers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🧹 Taskmaster Cleanup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect container runtime
if command -v container &> /dev/null; then
    RUNTIME="container"
elif command -v docker &> /dev/null; then
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
    $RUNTIME ps -a --filter "name=kali-agent" --format "{{.Names}}" | while read -r container; do
        if [ -n "$container" ]; then
            echo "  Removing: $container"
            $RUNTIME rm -f "$container" 2>/dev/null || true
        fi
    done
    echo "✅ Containers cleaned"
    echo ""
fi

# Ask before cleaning state
echo "Clean runtime state? (y/n)"
echo "  - state/executions.json"
echo "  - audit/audit_log.jsonl"
echo "  - audit/session_report.md"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Cleaning state files..."
    rm -f state/executions.json
    rm -f audit/audit_log.jsonl
    rm -f audit/session_report.md
    echo "✅ State cleaned"
else
    echo "⏭️  Skipping state cleanup"
fi
echo ""

# Ask before cleaning loot
echo "Clean loot directory? (y/n)"
echo "  - audit/loot/*"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Cleaning loot..."
    rm -rf audit/loot/*
    touch audit/loot/.gitkeep
    echo "✅ Loot cleaned"
else
    echo "⏭️  Skipping loot cleanup"
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
