#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Top-level installer
# ------------------------------------------------------------------------------

set -eo pipefail

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/utils/colors.sh"

# Show help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} $0"
    echo -e "${BLUE}Steps:${RESET}"
    echo -e "   ${YELLOW}1)${RESET} check prerequisites"
    echo -e "   ${YELLOW}2)${RESET} install requirements"
    echo -e "   ${YELLOW}3)${RESET} create symlink"
    exit 0
fi

# ------------------------------------------------------------------------------
# Check if a Python virtual environment is active
# ------------------------------------------------------------------------------

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}No Python virtual environment detected.${RESET}"
    read -n 1 -p "Proceed without a virtualenv? (y/n): " confirm
    echo

    case "$confirm" in
        [yY])
            echo -e "${BLUE}Continuing without virtualenv...${RESET}"
            ;;
        *)
            echo -e "${RED}Aborted. Please activate a virtualenv and try again.${RESET}"
            exit 1
            ;;
    esac
else
    echo -e "${GREEN}✔ Using virtualenv: $VIRTUAL_ENV${RESET}"
fi

FILE="../src/main.py"
BIN_FOLDER="/usr/local/bin"
BIN_NAME="summbv"

./utils/check-prerequisites.sh
./installers/m32.sh
./installers/python-requirements.sh
./utils/create-symlink.sh "${FILE}" "${BIN_FOLDER}" "${BIN_NAME}"

echo -e "${GREEN}✔ SummBoundVerify installed successfully!${RESET}"
