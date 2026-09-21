#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Install 32-bit Support
# ------------------------------------------------------------------------------

set -euo pipefail

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../utils/colors.sh"
source "${SCRIPT_DIR}/../utils/sudo.sh"

# 32-bit support is required by the symbolic engine's default -m32 build, so
# being unable to install it is fatal.
if [[ "$SUDO_OK" -ne 1 ]]; then
    sudo_unavailable_msg
    exit 1
fi

install_apt() {
    echo "Using APT (Debian/Ubuntu)"
    $SUDO apt-get update
    $SUDO apt-get install -y gcc-multilib libc6-dev-i386
}

install_dnf() {
    echo "Using DNF (Fedora)"
    $SUDO dnf install -y glibc-devel.i686 libstdc++-devel.i686
}

install_pacman() {
    echo "Using Pacman (Arch Linux)"

    # Enable multilib repo if not already enabled
    if ! grep -q '^\[multilib\]' /etc/pacman.conf; then
        echo "==> Enabling multilib repository..."
        $SUDO sed -i '/#\[multilib\]/,/Include/ s/^#//' /etc/pacman.conf
    fi

    $SUDO pacman -Syu --noconfirm
    $SUDO pacman -S --needed --noconfirm gcc lib32-glibc
}

install_zypper() {
    echo "Using Zypper (openSUSE)"
    $SUDO zypper install -y glibc-devel-32bit libstdc++6-32bit
}

if [[ ! -f /etc/os-release ]]; then
    echo -e "${RED}Cannot detect Linux distribution (missing /etc/os-release).${RESET}"
    exit 1
fi

# Load distro variables (ID, NAME, etc.)
source /etc/os-release

echo -e "${BLUE}Detected:${RESET} ${YELLOW}${PRETTY_NAME:-$ID}${RESET}"


case "$ID" in
    ubuntu|debian)
        install_apt
        ;;
    fedora)
        install_dnf
        ;;
    arch)
        install_pacman
        ;;
    opensuse*|suse)
        install_zypper
        ;;
    *)
        echo "${RED}Unsupported distribution:${RESET} ${YELLOW}$ID${RESET}"
        exit 1
        ;;
esac

echo -e "${GREEN} 32-bit support installation complete.${RESET}"