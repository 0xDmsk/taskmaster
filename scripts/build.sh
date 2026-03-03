#!/usr/bin/env bash
set -euo pipefail

# Taskmaster Agent Build Script
# Builds the kali-smart-operator container image

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EXECUTOR_DIR="$PROJECT_ROOT/executors"

IMAGE_NAME="${AGENT_IMAGE_NAME:-kali-smart-operator}"
PLATFORM="${CONTAINER_PLATFORM:-linux/arm64}"

echo "🏗️  Building Taskmaster Agent Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Image: $IMAGE_NAME"
echo "Platform: $PLATFORM"
echo "Build Context: $EXECUTOR_DIR"
echo ""

cd "$EXECUTOR_DIR"

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

echo "Using runtime: $RUNTIME"
echo ""

$RUNTIME build \
    --platform "$PLATFORM" \
    -t "$IMAGE_NAME:latest" \
    -f Dockerfile \
    .

echo ""
echo "✅ Build complete!"
echo "Image: $IMAGE_NAME:latest"
echo ""
echo "To test the image:"
echo "  $RUNTIME run -it --rm $IMAGE_NAME:latest"
