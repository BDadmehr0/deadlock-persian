#!/usr/bin/env bash
# Copy to scripts/install-prerequisites.sh in deadlockpersian/deadlock-persian.
# Installs system packages only; does not download or install the translation.
set -Eeuo pipefail

main() {
    local manager=''
    local -a elevate=() packages=() command=()
    if [[ $(uname -s) != Linux ]]; then
        echo 'This helper supports Linux only.' >&2
        return 1
    fi
    for manager in apt-get dnf yum pacman zypper apk; do
        if command -v "$manager" >/dev/null 2>&1; then break; fi
        manager=''
    done
    if [[ -z $manager ]]; then
        echo 'Unsupported package manager. Install Bash, Git, Python 3 and curl manually.' >&2
        return 1
    fi
    if (( EUID != 0 )); then
        if ! command -v sudo >/dev/null 2>&1; then
            echo 'sudo is unavailable. Ask your administrator to install Bash, Git, Python 3 and curl.' >&2
            return 1
        fi
        elevate=(sudo)
    fi
    packages=(bash git python3 curl ca-certificates)
    case "$manager" in
        apt-get)
            "${elevate[@]}" apt-get update
            command=(apt-get install "${packages[@]}") ;;
        dnf|yum) command=("$manager" install "${packages[@]}") ;;
        pacman)
            # Full upgrade avoids unsupported partial upgrades on Arch.
            packages=(bash git python curl ca-certificates)
            command=(pacman -Syu --needed "${packages[@]}") ;;
        zypper) command=(zypper install "${packages[@]}") ;;
        apk) command=(apk add --no-cache "${packages[@]}") ;;
    esac
    printf 'Package manager: %s\n' "$manager"
    printf 'Running:'; printf ' %q' "${elevate[@]}" "${command[@]}"; printf '\n'
    "${elevate[@]}" "${command[@]}"
    for tool in bash git python3 curl; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            printf 'Required tool is still missing: %s\n' "$tool" >&2
            return 1
        fi
    done
    python3 -c 'import sys; assert sys.version_info.major == 3'
    echo 'Prerequisites are ready. You can now run the translation installer.'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
