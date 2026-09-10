#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Install AFL++ (fuzzing engine)
#
# Required only by `summbv --engine fuzz`, which drives the generated test
# under AFL++ instead of angr. The symbolic engine does not need it, so a
# failure here is reported but does not abort the installation.
#
# The engine uses afl-clang-fast specifically: afl-gcc-fast ships broken on
# some releases (its GCC plugin is built against a different compiler version
# than the system one).
# ------------------------------------------------------------------------------

set -uo pipefail

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../utils/colors.sh"

UPSTREAM="https://github.com/AFLplusplus/AFLplusplus"

# Show help
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo -e "${BLUE}Usage:${RESET} $0"
    echo -e "${BLUE}Installs AFL++, used by 'summbv --engine fuzz'.${RESET}"
    exit 0
fi

manual_instructions() {
    echo -e "${YELLOW}Could not install AFL++ automatically.${RESET}"
    echo -e "${BLUE}The symbolic engine still works; only" \
            "'--engine fuzz' is unavailable.${RESET}"
    echo -e "${BLUE}To install it by hand, see:${RESET} ${UPSTREAM}"
}

# Already installed?
if command -v afl-clang-fast &>/dev/null && command -v afl-fuzz &>/dev/null; then
    echo -e "${GREEN}✔ AFL++ already installed${RESET}"
    exit 0
fi

if [[ ! -f /etc/os-release ]]; then
    echo -e "${RED}Cannot detect Linux distribution (missing /etc/os-release).${RESET}"
    manual_instructions
    exit 0
fi

# Load distro variables (ID, NAME, etc.)
source /etc/os-release

echo -e "${BLUE}Detected:${RESET} ${YELLOW}${PRETTY_NAME:-$ID}${RESET}"

# Only escalate once we know there is something to install.
source "${SCRIPT_DIR}/../utils/sudo.sh"

if [[ "$SUDO_OK" -ne 1 ]]; then
    sudo_unavailable_msg
    manual_instructions
    exit 0
fi

case "$ID" in
    ubuntu|debian)
        echo "Using APT (Debian/Ubuntu)"
        $SUDO apt-get update && $SUDO apt-get install -y afl++
        ;;
    fedora)
        echo "Using DNF (Fedora)"
        $SUDO dnf install -y american-fuzzy-lop++
        ;;
    arch)
        echo "Using Pacman (Arch Linux)"
        $SUDO pacman -S --needed --noconfirm aflplusplus
        ;;
    opensuse*|suse)
        echo "Using Zypper (openSUSE)"
        $SUDO zypper install -y afl++
        ;;
    *)
        echo -e "${YELLOW}Unsupported distribution:${RESET} ${YELLOW}$ID${RESET}"
        manual_instructions
        exit 0
        ;;
esac

if command -v afl-clang-fast &>/dev/null && command -v afl-fuzz &>/dev/null; then
    echo -e "${GREEN}✔ AFL++ installation complete.${RESET}"
else
    manual_instructions
fi

# Never fail the installation over an optional component.
exit 0
