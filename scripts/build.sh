#!/usr/bin/env bash
set -euo pipefail

# Taskmaster Agent Build Script
# Builds the kali-smart-operator container image

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EXECUTOR_DIR="$PROJECT_ROOT/executors"

IMAGE_NAME="${AGENT_IMAGE_NAME:-kali-smart-operator}"
PLATFORM="${CONTAINER_PLATFORM:-linux/arm64}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"

echo "🏗️  Building Taskmaster Agent Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Image: $IMAGE_NAME"
echo "Dockerfile: $DOCKERFILE"
echo "Platform: $PLATFORM"
echo "Build Context: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

if command -v docker &> /dev/null; then
    RUNTIME="docker"
elif command -v podman &> /dev/null; then
    RUNTIME="podman"
else
    echo "❌ Error: No container runtime found (docker or podman)"
    exit 1
fi

echo "Using runtime: $RUNTIME"
echo ""

$RUNTIME build \
    --platform "$PLATFORM" \
    -t "$IMAGE_NAME:latest" \
    -f "$EXECUTOR_DIR/$DOCKERFILE" \
    .

echo ""
echo "✅ Build complete!"
echo "Image: $IMAGE_NAME:latest"
echo ""
echo "To test the image:"
echo "  $RUNTIME run -it --rm $IMAGE_NAME:latest"
