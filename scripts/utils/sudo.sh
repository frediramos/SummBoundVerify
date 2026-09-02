#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Privilege escalation helper
#
# Package managers need root, but the installer as a whole must not run as
# root: it pip-installs into the active virtualenv, and doing that under sudo
# either loses $VIRTUAL_ENV or leaves root-owned files inside it.
#
# So escalate for the package manager only. Sourcing this sets:
#
#   SUDO      "sudo", or empty when already root
#   SUDO_OK   1 when a package manager can be run, 0 otherwise
#
# It deliberately does not exit: it is sourced, so exiting would terminate the
# caller, and not every caller is installing something mandatory.
# ------------------------------------------------------------------------------

# Prevent double sourcing
[[ -n "${__sudo_loaded:-}" ]] && return
__sudo_loaded=1

__sudo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${__sudo_dir}/colors.sh"

SUDO=""
SUDO_OK=1

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        SUDO_OK=0
    fi
fi

# Print the standard explanation for SUDO_OK=0. Callers decide whether that is
# fatal.
sudo_unavailable_msg() {
    echo -e "${RED}Root privileges are required to install system packages," \
            "but sudo is not available.${RESET}"
    echo -e "${BLUE}Re-run as root, or install the packages by hand.${RESET}"
}
