#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Install Python requirements into an existing virtualenv
# ------------------------------------------------------------------------------

set -euo pipefail

source "colors.sh"

DEFAULT_REQ_FILE="requirements.txt"

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} $0 <requirements_file>"
    echo
    echo -e "${BLUE}Installs a requirements file into an existing virtualenv.${RESET}"
    echo
    echo -e "${YELLOW}Defaults:${RESET}"
    echo -e "  ${BLUE}requirements_file${RESET} = $DEFAULT_REQ_FILE"
    exit 0
fi

req_file="${1:-$DEFAULT_REQ_FILE}"
echo -e "${BLUE}Using requirements file:${RESET} $req_file"
echo -e "${YELLOW}Warning${RESET}: installing in the current python environment"

# Check requirements file exists
if [[ ! -f "$req_file" ]]; then
    echo -e "${RED}ERROR: requirements file not found:${RESET} $req_file"
    exit 1
fi

# Install requirements
echo -e "${BLUE}Installing Python requirements...${RESET}"
python3 -m pip install --upgrade pip
python3 -m pip install -r "$req_file"

echo -e "${GREEN}✔ Requirements installed successfully in'${RESET}"