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
CORE_FONTS_REL='core/panorama/fonts'
BACKUP="$GAME/.deadlock-persian-backup"
LOCK="$GAME/.deadlock-persian.lock"
[[ -d $BACKUP && -f "$BACKUP/format" && $(<"$BACKUP/format") == 'deadlock-persian-v1' ]] || { echo "No valid installer backup found: $BACKUP" >&2; exit 1; }
mkdir -- "$LOCK" 2>/dev/null || { echo "Another install/uninstall is running, or a stale lock exists: $LOCK" >&2; exit 1; }
STAGE=''
cleanup() { [[ -z $STAGE ]] || rm -rf -- "$STAGE"; rmdir -- "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT
FONT_DIRS=(menu vpk fonts corefonts)
declare -A FONT_TARGET=(
    [fonts]="$GAME/$FONTS_REL"
    [corefonts]="$GAME/$CORE_FONTS_REL"
)
for item in "${FONT_DIRS[@]}"; do
    # Backwards compatibility: older backups only have menu.state / vpk.state;
    # treat missing entries as absent.
    if [[ -f "$BACKUP/$item.state" ]]; then
        state=$(<"$BACKUP/$item.state")
    else
        state='absent'
    fi
    if [[ $item == fonts || $item == corefonts ]]; then
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
for item in "${FONT_DIRS[@]}"; do
    if [[ -f "$BACKUP/$item.state" && $(<"$BACKUP/$item.state") == present ]]; then
        cp -pR -- "$BACKUP/$item.original" "$STAGE/$item.original"
    fi
done
for item in "${FONT_DIRS[@]}"; do
    case "$item" in
        menu) target="$GAME/$MENU_REL" ;;
        vpk)  target="$GAME/$VPK_REL" ;;
        *)    target="${FONT_TARGET[$item]}" ;;
    esac
    if [[ -f "$BACKUP/$item.state" && $(<"$BACKUP/$item.state") == present ]]; then
        if [[ $item == fonts || $item == corefonts ]]; then rm -rf -- "$target"; fi
        mkdir -p -- "$(dirname -- "$target")"
        if [[ $item == fonts || $item == corefonts ]]; then
            cp -pR -- "$STAGE/$item.original" "$target"
        else
            mv -f -- "$STAGE/$item.original" "$target"
        fi
    else
        if [[ $item == fonts || $item == corefonts ]]; then
            if [[ -f "$BACKUP/fonts.installed" ]]; then
                while IFS= read -r font; do
                    for dir_rel in "$FONTS_REL" "$CORE_FONTS_REL"; do
                        rm -f -- "$GAME/$dir_rel/$font"
                    done
                done < "$BACKUP/fonts.installed"
            fi
            # Remove empty subdirectories the installer may have added (conf.d/, vazirmatn/).
            find "$GAME/$FONTS_REL" -mindepth 1 -type d -empty -delete 2>/dev/null || true
            find "$GAME/$CORE_FONTS_REL" -mindepth 1 -type d -empty -delete 2>/dev/null || true
            rmdir -- "$GAME/$FONTS_REL" 2>/dev/null || true
            rmdir -- "$GAME/$CORE_FONTS_REL" 2>/dev/null || true
        elif [[ -d $target && ! -L $target ]]; then
            echo "Refusing to remove directory: $target" >&2; exit 1
        else
            rm -f -- "$target"
        fi
    fi
done
# Strip our fonts.conf rule from any patched config. Handles backups that
# predate the font feature (no directory backup for the font folders), where
# the game's own fonts.conf was patched in place and cannot be restored from a
# backup copy.
if [[ -f "$BACKUP/fonts.conf.patched" && -s "$BACKUP/fonts.conf.patched" ]]; then
    command -v python3 >/dev/null || { echo 'Missing dependency: python3' >&2; exit 1; }
    while IFS= read -r conf_rel; do
        [[ -n $conf_rel ]] || continue
        conf="$GAME/$conf_rel"
        [[ -f $conf ]] || continue
        python3 - "$conf" <<'PY'
import sys
path = sys.argv[1]
start = '<!-- deadlock-persian'
end = '</fontconfig>'
with open(path, encoding='utf-8') as f:
    data = f.read()
i = data.find(start)
if i < 0:
    raise SystemExit(0)
j = data.rfind(end)
if j < 0 or j < i:
    raise SystemExit(0)
data = data[:i] + data[j:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(data)
PY
    done < "$BACKUP/fonts.conf.patched"
fi
rm -rf -- "$BACKUP"
echo "Translation removed and original files restored: $GAME"
