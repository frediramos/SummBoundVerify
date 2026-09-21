#!/usr/bin/env bash
set -e

echo "Rebuilding Docker image"
docker compose build --no-cache sbv