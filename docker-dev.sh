#!/usr/bin/env bash
set -e

VOLUME_ARGS=()

if [ -n "$1" ]; then
    TARGET_DIR="$1"

    if [ ! -d "$TARGET_DIR" ]; then
        echo "Error: directory does not exist: $TARGET_DIR"
        exit 1
    fi

    TARGET_PATH="$(cd "$TARGET_DIR" && pwd)"

    VOLUME_ARGS=(
        -v "$TARGET_PATH:/root/dev"
        -w /root/dev
    )
fi

docker compose run --rm "${VOLUME_ARGS[@]}" sbv bash