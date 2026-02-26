#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Install 32-bit Support
# ------------------------------------------------------------------------------

set -euo pipefail

# Get directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/../utils/colors.sh"

install_apt() {
    echo "Using APT (Debian/Ubuntu)"
    apt-get update
    apt-get install -y gcc-multilib libc6-dev-i386
}

install_dnf() {
    echo "Using DNF (Fedora)"
    dnf install -y glibc-devel.i686 libstdc++-devel.i686
}

install_pacman() {
    echo "Using Pacman (Arch Linux)"

    # Enable multilib repo if not already enabled
    if ! grep -q '^\[multilib\]' /etc/pacman.conf; then
        echo "==> Enabling multilib repository..."
        sed -i '/#\[multilib\]/,/Include/ s/^#//' /etc/pacman.conf
    fi

    pacman -Syu --noconfirm
    pacman -S --needed --noconfirm gcc lib32-glibc
}

install_zypper() {
    echo "Using Zypper (openSUSE)"
    zypper install -y glibc-devel-32bit libstdc++6-32bit
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