#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Check basic Pre-Requisites
# ------------------------------------------------------------------------------

set -eo pipefail

source colors.sh

# Show help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} $0"
    echo -e "${BLUE}Checks that python3, pip, and virtualenvwrapper are installed.${RESET}"
    exit 0
fi


# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}ERROR: python3 is not installed.${RESET}"
    exit 1
fi

# Check pip
if ! command -v pip &>/dev/null; then
    echo -e "${RED}ERROR: pip is not installed.${RESET}"
    exit 1
fi


echo -e "${GREEN}✔ All prerequisites satisfied${RESET}"