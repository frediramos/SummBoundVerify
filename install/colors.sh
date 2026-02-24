#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Shared ANSI color definitions
# ------------------------------------------------------------------------------

# Prevent double sourcing
[[ -n "${__colors_loaded:-}" ]] && return
__colors_loaded=1

GREEN="\033[0;32m"
RED="\033[0;31m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RESET="\033[0m"