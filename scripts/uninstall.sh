#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Uninstall SummBoundVerify
# ------------------------------------------------------------------------------

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/utils/colors.sh"

# Show help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo -e "${YELLOW}Usage:${RESET} $0 <venv_name>"
    echo -e "${YELLOW}Removes the SummBoundVerify symlink. If <venv_name> is provided, removes that virtualenv as well.${RESET}"
    exit 0
fi


# Optional virtualenv name
VENV_NAME="${1:-}"

# Remove symlink
SYMLINK_DIR=/usr/local/bin
LINK_NAME=summbv
LINK_PATH="$SYMLINK_DIR/$LINK_NAME"

if [ -L "$LINK_PATH" ]; then
    sudo rm -f "$LINK_PATH"
    echo -e "${GREEN}✔ Symlink '$LINK_NAME' removed${RESET}"
else
    echo -e "${YELLOW}Symlink '$LINK_NAME' does not exist, skipping${RESET}"
fi

# Remove virtualenv if name provided
if [[ -n "$VENV_NAME" ]]; then
    
    if ! command -v rmvirtualenv &>/dev/null; then
        echo -e "${YELLOW}Virtualenvwrapper not available in this shell.${RESET}"
        echo -e "${YELLOW}Cannot remove virtualenv '$VENV_NAME'."
    
    elif workon "$VENV_NAME" &>/dev/null; then
        rmvirtualenv "$VENV_NAME"
        echo -e "${GREEN}✔ Virtualenv '$VENV_NAME' removed${RESET}"
    
    else
        echo -e "${YELLOW}Virtualenv '$VENV_NAME' does not exist, skipping${RESET}"
    fi
fi

# Always indicate uninstallation is done
echo -e "${GREEN}✔ SummBoundVerify ${YELLOW}uninstalled${RESET}"
