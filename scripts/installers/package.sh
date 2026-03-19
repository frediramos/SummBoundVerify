#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Install Python package into an existing virtualenv using pyproject.toml
# ------------------------------------------------------------------------------

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../utils/colors.sh"

# Default project root = parent of script directory
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} $0 <project_root>"
    echo
    echo -e "${BLUE}Installs the Python package using pyproject.toml into the current environment.${RESET}"
    echo
    echo -e "${YELLOW}Defaults:${RESET}"
    echo -e "  ${BLUE}project_root${RESET} = $PROJECT_ROOT"
    exit 0
fi

project_root="${1:-$PROJECT_ROOT}"

echo -e "${BLUE}Using project directory:${RESET} $project_root"
echo -e "${YELLOW}Warning${RESET}: installing into current environment (${YELLOW}${VIRTUAL_ENV:-global}${RESET})"

# Check pyproject.toml exists
if [[ ! -f "$project_root/pyproject.toml" ]]; then
    echo -e "${RED}ERROR: pyproject.toml not found in:${RESET} $project_root"
    exit 1
fi

echo -e "${BLUE}Installing Python package from pyproject.toml...${RESET}"

python3 -m pip install --upgrade pip
python3 -m pip install -e "$project_root"

echo -e "${GREEN}✔ Package installed successfully (editable/dev mode)${RESET}"