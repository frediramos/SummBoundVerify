#!/usr/bin/env bash
set -e

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Usage: $0 [TARGET_DIR] <command> [args...]"
    echo
    echo "Runs a command in the SBV Docker container."
    echo "By default, the current directory is mounted at /root/summboundverify."
    echo "If TARGET_DIR is given, it is mounted at /root/dev instead."
    exit 0
fi

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

docker compose run --rm "${VOLUME_ARGS[@]}" sbv "$@"