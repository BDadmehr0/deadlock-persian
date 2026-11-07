#!/usr/bin/env bash
# Interactive installer / uninstaller. Optional argument: game/citadel directory.
set -u
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
if (( $# > 1 )); then echo "Usage: $0 [path-to-game/citadel]" >&2; exit 2; fi
GAME=${1:-"$HOME/.local/share/Steam/steamapps/common/Deadlock/game/citadel"}
while true; do
    printf '\n%s\n' '=== Deadlock Persian Translation ===' "Game directory: $GAME" \
        '1) Install or update translation' \
        '2) Uninstall translation and restore original files' \
        '3) Exit'
    printf 'Select an option [1-3]: '
    if ! IFS= read -r choice; then printf '\n'; exit 0; fi
    case "$choice" in
        1) if bash "$ROOT/install.sh" "$GAME"; then
               printf '%s\n' 'Installation completed successfully.'
           else
               printf '%s\n' 'Installation failed; see the message above.' >&2
           fi ;;
        2) printf '%s' 'Restore the original files from backup? [y/N]: '
           if ! IFS= read -r answer; then printf '\n'; exit 0; fi
           case "$answer" in
               [yY]|[yY][eE][sS])
                   if bash "$ROOT/uninstall.sh" "$GAME"; then
                       printf '%s\n' 'Uninstallation completed successfully.'
                   else
                       printf '%s\n' 'Uninstallation failed; see the message above.' >&2
                   fi ;;
               *) printf '%s\n' 'Uninstallation cancelled.' ;;
           esac ;;
        3|q|Q) exit 0 ;;
        *) printf '%s\n' 'Invalid option; enter 1, 2, or 3.' >&2 ;;
    esac
done
