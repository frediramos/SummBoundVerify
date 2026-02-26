#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Create symbolic link for SummBoundVerify
# ------------------------------------------------------------------------------

set -euo pipefail  # exit on errors, unset variables are errors, fail on pipe errors

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/colors.sh"

# Default values
DEFAULT_SRC="../../src/main.py"
DEFAULT_DIR="/usr/local/bin"
DEFAULT_NAME="summbv"

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} $0 <src_file> <symlink_dir> <link_name>"
    echo
    echo -e "${YELLOW}Defaults:${RESET}"
    echo -e "   ${BLUE}src_file${RESET} = $DEFAULT_SRC"
    echo -e "   ${BLUE}symlink_dir${RESET} = $DEFAULT_DIR"
    echo -e "   ${BLUE}link_name${RESET} = $DEFAULT_NAME"
    exit 0
fi

resolve_absolute_path() {
    local path="$1"
    local absolute_path

    # Convert to absolute path
    absolute_path=$(realpath "$path" 2>/dev/null || readlink -f "$path")

    # Check if file exists
    if [[ ! -f "$absolute_path" ]]; then
        echo -e "${RED}ERROR: File not found: $absolute_path${RESET}"
        exit 1
    fi

    # Return the absolute path
    echo "$absolute_path"
}

# Positional arguments with defaults
src_file="${1:-$DEFAULT_SRC}"
symlink_dir="${2:-$DEFAULT_DIR}"
link_name="${3:-$DEFAULT_NAME}"
link_path="$symlink_dir/$link_name"

# Check if source file exists
if [[ ! -f "$src_file" ]]; then
    echo -e "${RED}ERROR: Source file not found: $src_file${RESET}"
    exit 1
fi

# Check if target directory exists
if [[ ! -d "$symlink_dir" ]]; then
    echo -e "${RED}ERROR: Directory not found: $symlink_dir${RESET}"
    exit 1
fi

abs_file=$(resolve_absolute_path ${src_file})

# Create the symlink
echo -e "${BLUE}Creating symlink:${RESET} $link_path -> $abs_file"
sudo ln -sf "$abs_file" "$link_path"

# Verify creation
if [[ -L "$link_path" && -e "$link_path" ]]; then
    echo -e "${GREEN}✔ Symlink successfully created:${RESET} $link_name -> $abs_file"
else
    echo -e "${RED}ERROR: Failed to create symlink $link_path${RESET}"
    exit 1
fi