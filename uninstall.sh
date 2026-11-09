#!/usr/bin/env bash
# Restore the exact pre-install game files, or remove files that did not exist.
set -Eeuo pipefail
DEFAULT_GAME="$HOME/.local/share/Steam/steamapps/common/Deadlock/game/citadel"
FORCE=0
GAME=''
for arg in "$@"; do
    if [[ $arg == --force ]]; then FORCE=1
    elif [[ -z $GAME ]]; then GAME=$arg
    else echo "Usage: $0 [--force] [path-to-game/citadel]" >&2; exit 2
    fi
done
GAME=${GAME:-$DEFAULT_GAME}
[[ -d $GAME ]] || { echo "Game directory not found: $GAME" >&2; exit 1; }
GAME=$(cd -- "$GAME" && pwd -P)
MENU_REL='resource/localization/citadel_main/citadel_main_english.txt'
VPK_REL='pak82_dir.vpk'
FONTS_REL='panorama/fonts'
BACKUP="$GAME/.deadlock-persian-backup"
LOCK="$GAME/.deadlock-persian.lock"
[[ -d $BACKUP && -f "$BACKUP/format" && $(<"$BACKUP/format") == 'deadlock-persian-v1' ]] || { echo "No valid installer backup found: $BACKUP" >&2; exit 1; }
mkdir -- "$LOCK" 2>/dev/null || { echo "Another install/uninstall is running, or a stale lock exists: $LOCK" >&2; exit 1; }
STAGE=''
cleanup() { [[ -z $STAGE ]] || rm -rf -- "$STAGE"; rmdir -- "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT
for item in menu vpk fonts; do
    [[ -f "$BACKUP/$item.state" ]] || { echo "Missing backup state: $item" >&2; exit 1; }
    state=$(<"$BACKUP/$item.state")
    if [[ $item == fonts ]]; then
        [[ $state == absent || ( $state == present && -d "$BACKUP/$item.original" ) ]] || { echo "Backup for $item is incomplete." >&2; exit 1; }
    else
        [[ $state == absent || ( $state == present && -f "$BACKUP/$item.original" ) ]] || { echo "Backup for $item is incomplete." >&2; exit 1; }
    fi
done
if [[ $FORCE -eq 0 ]]; then
    command -v sha256sum >/dev/null || { echo 'Missing dependency: sha256sum' >&2; exit 1; }
    [[ -f "$BACKUP/installed.sha256" ]] && (cd -- "$GAME" && sha256sum --status -c "$BACKUP/installed.sha256") || {
        echo 'Installed files have changed or installation was interrupted; refusing to overwrite them.' >&2
        echo 'Inspect the files and rerun with --force if you want to restore the original backup.' >&2
        exit 1
    }
fi
STAGE=$(mktemp -d "$GAME/.deadlock-persian-restore.XXXXXXXX")
# Stage every available original before replacing anything. Keep backups on error.
for item in menu vpk fonts; do
    [[ $(<"$BACKUP/$item.state") != present ]] || cp -pR -- "$BACKUP/$item.original" "$STAGE/$item.original"
done
for item in menu vpk fonts; do
    if [[ $item == menu ]]; then target="$GAME/$MENU_REL"
    elif [[ $item == vpk ]]; then target="$GAME/$VPK_REL"
    else target="$GAME/$FONTS_REL"; fi
    if [[ $(<"$BACKUP/$item.state") == present ]]; then
        if [[ $item == fonts ]]; then rm -rf -- "$target"; fi
        mkdir -p -- "$(dirname -- "$target")"
        mv -f -- "$STAGE/$item.original" "$target"
    else
        if [[ $item == fonts ]]; then
            if [[ -f "$BACKUP/fonts.installed" ]]; then
                while IFS= read -r font; do rm -f -- "$GAME/$FONTS_REL/$font"; done < "$BACKUP/fonts.installed"
            fi
            # Remove empty subdirectories the installer may have added (conf.d/, vazirmatn/).
            find "$GAME/$FONTS_REL" -mindepth 1 -type d -empty -delete 2>/dev/null || true
            rmdir -- "$GAME/$FONTS_REL" 2>/dev/null || true
        elif [[ -d $target && ! -L $target ]]; then
            echo "Refusing to remove directory: $target" >&2; exit 1
        else
            rm -f -- "$target"
        fi
    fi
done
rm -rf -- "$BACKUP"
echo "Translation removed and original files restored: $GAME"
