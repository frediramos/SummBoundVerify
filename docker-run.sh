#!/usr/bin/env bash
set -e

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: $0 [--rebuild] [path]"
    echo
    echo "Starts a temporary Docker container with the tool installed"
    echo
    echo "Optionally mounts [path] into ${CONTAINER_VOLUME}"
    echo "Defaults to current directory: '.'"
    echo
    echo "Options:"
    echo "  -r, --rebuild   Rebuild the Docker image"
    echo
    echo "The container runs interactively and is removed on exit."
    exit 0
fi

# -----------------------------
# Config
# -----------------------------
ARCH="linux/amd64"
HOSTNAME="sbv"
IMAGE_NAME="sbv-image"
CONTAINER_VOLUME="/root/dev"

REBUILD=false

# Detect rebuild flag
if [[ "${1:-}" == "-r" || "${1:-}" == "--rebuild" ]]; then
    REBUILD=true
    shift
fi

if [ -n "$1" ]; then
    HOST_VOLUME="$(cd "$1" 2>/dev/null && pwd)"
else
    HOST_VOLUME="$PWD"
fi

# -----------------------------
# Build image if needed
# -----------------------------
BUILD_CMD=(docker build --platform "$ARCH" -t "$IMAGE_NAME" .)

if $REBUILD; then
    echo "Rebuilding Docker image '$IMAGE_NAME'..."
    "${BUILD_CMD[@]}"
    docker image prune -f > /dev/null

elif ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "Docker image '$IMAGE_NAME' not found. Building..."
    "${BUILD_CMD[@]}"
    
else
    echo "Using existing image: '$IMAGE_NAME'"
fi

# -----------------------------
# Run container
# -----------------------------
echo "Starting container..."
docker run -it --rm \
    --platform "$ARCH" \
    --hostname "$HOSTNAME" \
    -v "$HOST_VOLUME":"$CONTAINER_VOLUME" \
    -w "$CONTAINER_VOLUME" \
    "$IMAGE_NAME"
