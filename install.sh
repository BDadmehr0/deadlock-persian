#!/usr/bin/env bash
# Install the Persian menu and VPK while preserving the original game files.
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
DEFAULT_GAME="$HOME/.local/share/Steam/steamapps/common/Deadlock/game/citadel"
GAME=${1:-$DEFAULT_GAME}
if (( $# > 1 )); then echo "Usage: $0 [path-to-game/citadel]" >&2; exit 2; fi
for command in python3 sha256sum mktemp; do command -v "$command" >/dev/null || { echo "Missing dependency: $command" >&2; exit 1; }; done
[[ -d $GAME ]] || { echo "Game directory not found: $GAME" >&2; exit 1; }
GAME=$(cd -- "$GAME" && pwd -P)
MENU_REL='resource/localization/citadel_main/citadel_main_english.txt'
VPK_REL='pak82_dir.vpk'
BACKUP="$GAME/.deadlock-persian-backup"
LOCK="$GAME/.deadlock-persian.lock"
SOURCE_MENU="$ROOT/data/citadel_main_english.txt"
SOURCE_VPK="$ROOT/data/$VPK_REL"
TRANSLATOR="$ROOT/tools/translate_common.py"
[[ -f $SOURCE_MENU && -f $SOURCE_VPK && -f $TRANSLATOR ]] || { echo 'Missing translation files or tools/translate_common.py in the installer directory.' >&2; exit 1; }
# Do not silently install into an unrelated folder.
[[ -f "$GAME/$MENU_REL" || -f "$GAME/pak01_dir.vpk" || -f "$GAME/$VPK_REL" ]] || { echo "This does not appear to be the Deadlock citadel folder: $GAME" >&2; exit 1; }
mkdir -- "$LOCK" 2>/dev/null || { echo "Another install/uninstall is running, or a stale lock exists: $LOCK" >&2; exit 1; }
STAGE=''
cleanup() { [[ -z $STAGE ]] || rm -rf -- "$STAGE"; rmdir -- "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT
STAGE=$(mktemp -d "$GAME/.deadlock-persian-stage.XXXXXXXX")

# Work on a private copy so the repository source is never modified.
cp -- "$SOURCE_VPK" "$STAGE/$VPK_REL"
cp -- "$SOURCE_MENU" "$STAGE/menu.txt"
python3 "$TRANSLATOR" "$STAGE/$VPK_REL"

# Preserve the very first pre-install state. Never replace a previous backup.
if [[ -e $BACKUP ]]; then
    [[ -d $BACKUP && -f "$BACKUP/format" && $(<"$BACKUP/format") == 'deadlock-persian-v1' && -f "$BACKUP/menu.state" && -f "$BACKUP/vpk.state" ]] || { echo "Invalid backup directory; refusing to overwrite it: $BACKUP" >&2; exit 1; }
    for item in menu vpk; do
        state=$(<"$BACKUP/$item.state")
        [[ $state == absent || ( $state == present && -f "$BACKUP/$item.original" ) ]] || { echo "Backup for $item is incomplete." >&2; exit 1; }
    done
    if [[ -f "$BACKUP/installed.sha256" ]]; then
        (cd -- "$GAME" && sha256sum --status -c "$BACKUP/installed.sha256") || { echo 'Installed files changed since the previous install. Restore or inspect them before reinstalling.' >&2; exit 1; }
    else
        echo 'Incomplete previous installation; run uninstall.sh to restore the original files.' >&2
        exit 1
    fi
else
    TEMP_BACKUP="$STAGE/backup"
    mkdir -- "$TEMP_BACKUP"
    printf '%s\n' 'deadlock-persian-v1' > "$TEMP_BACKUP/format"
    for item in menu vpk; do
        if [[ $item == menu ]]; then target="$GAME/$MENU_REL"; else target="$GAME/$VPK_REL"; fi
        if [[ -L $target || ( -e $target && ! -f $target ) ]]; then echo "Refusing to replace non-regular file or symlink: $target" >&2; exit 1; fi
        if [[ -f $target ]]; then
            cp -p -- "$target" "$TEMP_BACKUP/$item.original"
            printf 'present\n' > "$TEMP_BACKUP/$item.state"
        else
            printf 'absent\n' > "$TEMP_BACKUP/$item.state"
        fi
    done
    mv -- "$TEMP_BACKUP" "$BACKUP"
fi
# Record intended hashes before replacing either file, so a failed install can
# still be recovered using uninstall.sh --force.
{
    printf '%s  %s\n' "$(sha256sum "$STAGE/menu.txt" | cut -d' ' -f1)" "$MENU_REL"
    printf '%s  %s\n' "$(sha256sum "$STAGE/$VPK_REL" | cut -d' ' -f1)" "$VPK_REL"
} > "$STAGE/installed.sha256"
mv -f -- "$STAGE/installed.sha256" "$BACKUP/installed.sha256"
mkdir -p -- "$(dirname -- "$GAME/$MENU_REL")"
# Staging and destination are on the same filesystem; each rename is atomic.
mv -f -- "$STAGE/menu.txt" "$GAME/$MENU_REL"
mv -f -- "$STAGE/$VPK_REL" "$GAME/$VPK_REL"
echo "Installed Persian translation in: $GAME"
echo "Original files are backed up in: $BACKUP"
echo 'The menu translation is incomplete and has not been tested in game.'
