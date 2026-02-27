#!/usr/bin/env bash
set -e

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: $0 [path]"
    echo
    echo "Starts a temporary Docker container with the tool installed"
    echo
    echo "Optionally mounts [path] into ${CONTAINER_VOLUME}"
    echo "Defaults to current directory: '.'"
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

if [ -n "$1" ]; then
    HOST_VOLUME="$(cd "$1" 2>/dev/null && pwd)"
else
    HOST_VOLUME="$PWD"
fi

# -----------------------------
# Build image if it doesn't exist
# -----------------------------
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "Docker image '$IMAGE_NAME' not found. Building..."
    docker build --platform "$ARCH" -t "$IMAGE_NAME" .
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
