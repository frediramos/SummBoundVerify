#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Install Claude Code (the `claude` CLI)
#
# Required only by summaries/generation/run.py, which asks Claude to write
# summaries. summbv does not need it, so a failure here is reported but does
# not abort the installation.
#
# Set CLAUDE_VERSION to install a specific version (e.g. CLAUDE_VERSION=2.1.285),
# so that every generation run uses the same one. The default is the latest.
# ------------------------------------------------------------------------------

set -uo pipefail

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../utils/colors.sh"

INSTALLER="https://claude.ai/install.sh"
DOCS="https://docs.claude.com/en/docs/claude-code/setup"
VERSION="${CLAUDE_VERSION:-latest}"

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} [CLAUDE_VERSION=x.y.z] $0"
    echo -e "${BLUE}Installs Claude Code, used by summaries/generation/run.py.${RESET}"
    exit 0
fi

manual_instructions() {
    echo -e "${YELLOW}Could not install Claude Code automatically.${RESET}"
    echo -e "${BLUE}summbv still works; only summary generation is" \
            "unavailable.${RESET}"
    echo -e "${BLUE}To install it manually, see:${RESET} ${DOCS}"
}

# Already installed?
if command -v claude &>/dev/null; then
    echo -e "${GREEN}✔ Claude Code already installed:${RESET}" \
            "$(claude --version 2>/dev/null)"
    exit 0
fi

if ! command -v curl &>/dev/null; then
    echo -e "${RED}curl not found.${RESET}"
    manual_instructions
    exit 0
fi

echo -e "${BLUE}Installing Claude Code (${YELLOW}${VERSION}${BLUE})...${RESET}"

if ! curl -fsSL "$INSTALLER" | bash -s "$VERSION"; then
    manual_instructions
    exit 0
fi

# The installer puts claude in ~/.local/bin (not on PATH by default)
if command -v claude &>/dev/null; then
    echo -e "${GREEN}✔ Claude Code installation complete.${RESET}"
elif [[ -x "$HOME/.local/bin/claude" ]]; then
    echo -e "${GREEN}✔ Claude Code installed in ~/.local/bin.${RESET}"
    echo -e "${YELLOW}Add ~/.local/bin to your PATH to use it.${RESET}"
else
    manual_instructions
fi

echo -e "${BLUE}Run ${YELLOW}claude${BLUE} once to log in before using" \
        "summaries/generation/run.py.${RESET}"

exit 0
