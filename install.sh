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
FONTS_REL='panorama/fonts'
BACKUP="$GAME/.deadlock-persian-backup"
LOCK="$GAME/.deadlock-persian.lock"
SOURCE_MENU="$ROOT/data/citadel_main_english.txt"
SOURCE_VPK="$ROOT/data/$VPK_REL"
SOURCE_FONTS="$ROOT/data/fonts"
TRANSLATOR="$ROOT/tools/translate_common.py"
[[ -f $SOURCE_MENU && -f $SOURCE_VPK && -d $SOURCE_FONTS && -f $TRANSLATOR ]] || { echo 'Missing translation files, fonts, or tools/translate_common.py in the installer directory.' >&2; exit 1; }
# Do not silently install into an unrelated folder.
[[ -f "$GAME/$MENU_REL" || -f "$GAME/pak01_dir.vpk" || -f "$GAME/$VPK_REL" ]] || { echo "This does not appear to be the Deadlock citadel folder: $GAME" >&2; exit 1; }
mkdir -- "$LOCK" 2>/dev/null || { echo "Another install/uninstall is running, or a stale lock exists: $LOCK" >&2; exit 1; }
STAGE=''
cleanup() { [[ -z $STAGE ]] || rm -rf -- "$STAGE"; rmdir -- "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT
STAGE=$(mktemp -d "$GAME/.deadlock-persian-stage.XXXXXXXX")
STAGE_FONTS="$STAGE/fonts"

# Work on a private copy so the repository source is never modified.
cp -- "$SOURCE_VPK" "$STAGE/$VPK_REL"
cp -- "$SOURCE_MENU" "$STAGE/menu.txt"
cp -R -- "$SOURCE_FONTS/." "$STAGE_FONTS/"
python3 "$TRANSLATOR" "$STAGE/$VPK_REL"

# Preserve the very first pre-install state. Never replace a previous backup.
if [[ -e $BACKUP ]]; then
    [[ -d $BACKUP && -f "$BACKUP/format" && $(<"$BACKUP/format") == 'deadlock-persian-v1' && -f "$BACKUP/menu.state" && -f "$BACKUP/vpk.state" ]] || { echo "Invalid backup directory; refusing to overwrite it: $BACKUP" >&2; exit 1; }
    for item in menu vpk fonts; do
        # Backwards compatibility: backups made before the font addition only
        # contain menu.state / vpk.state; treat missing entries as absent.
        if [[ -f "$BACKUP/$item.state" ]]; then
            state=$(<"$BACKUP/$item.state")
        else
            state='absent'
        fi
        if [[ $item == fonts ]]; then
            [[ $state == absent || ( $state == present && -d "$BACKUP/$item.original" ) ]] || { echo "Backup for $item is incomplete." >&2; exit 1; }
        else
            [[ $state == absent || ( $state == present && -f "$BACKUP/$item.original" ) ]] || { echo "Backup for $item is incomplete." >&2; exit 1; }
        fi
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
    for item in menu vpk fonts; do
        if [[ $item == menu ]]; then target="$GAME/$MENU_REL"; kind='f'
        elif [[ $item == vpk ]]; then target="$GAME/$VPK_REL"; kind='f'
        else target="$GAME/$FONTS_REL"; kind='d'; fi
        if [[ -L $target || ( -e $target && ( ( $kind == d && ! -d $target ) || ( $kind == f && ! -f $target ) ) ) ]]; then echo "Refusing to replace non-$kind file or symlink: $target" >&2; exit 1; fi
        if [[ -e $target ]]; then
            cp -pR -- "$target" "$TEMP_BACKUP/$item.original"
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
    # Record every font file we are about to install, relative to the game dir.
    # TTFs land at panorama/fonts/ root, conf.d files keep their subdirectory.
    while IFS= read -r font; do
        rel="${font#$STAGE_FONTS/}"
        case "$rel" in
            vazirmatn/*.ttf) dest_rel="$(basename -- "$rel")" ;;
            *) dest_rel="$rel" ;;
        esac
        game_rel="$FONTS_REL/$dest_rel"
        printf '%s  %s\n' "$(sha256sum "$font" | cut -d' ' -f1)" "$game_rel"
        printf '%s\n' "$dest_rel" >> "$BACKUP/fonts.installed"
    done < <(find "$STAGE_FONTS" -type f | sort)
} > "$STAGE/installed.sha256"
mv -f -- "$STAGE/installed.sha256" "$BACKUP/installed.sha256"
mkdir -p -- "$(dirname -- "$GAME/$MENU_REL")"
# Staging and destination are on the same filesystem; renames are atomic.
mv -f -- "$STAGE/menu.txt" "$GAME/$MENU_REL"
mv -f -- "$STAGE/$VPK_REL" "$GAME/$VPK_REL"
# Merge the Vazirmatn font files into the game's panorama/fonts folder.
# TTFs belong at the folder root so fonts.conf can scan them; conf.d rules
# keep their subdirectory.
mkdir -p -- "$GAME/$FONTS_REL"
while IFS= read -r font; do
    rel="${font#$STAGE_FONTS/}"
    case "$rel" in
        vazirmatn/*.ttf) dest_rel="$(basename -- "$rel")" ;;
        *) dest_rel="$rel" ;;
    esac
    mkdir -p -- "$GAME/$FONTS_REL/$(dirname -- "$dest_rel")"
    cp -f -- "$font" "$GAME/$FONTS_REL/$dest_rel"
done < <(find "$STAGE_FONTS" -type f | sort)

# Patch the game's panorama/fonts/fonts.conf so Panorama uses Vazirmatn for
# Arabic-script (Persian) UI text. Deadlock already remaps fonts per-language
# in this same file, so we add a matching rule before </fontconfig>. The game
# directory's fonts.conf is part of the backed-up fonts folder, so uninstall
# restores the original automatically.
FONTS_CONF="$GAME/$FONTS_REL/fonts.conf"
if [[ -f $FONTS_CONF && ! -L $FONTS_CONF ]]; then
    if ! grep -q 'deadlock-persian' "$FONTS_CONF" 2>/dev/null; then
        python3 - "$FONTS_CONF" <<'PY'
import sys
path = sys.argv[1]
rule = (
    '    <!-- deadlock-persian: Vazirmatn for Persian (Arabic-script) UI text -->\n'
    '    <match>\n'
    '        <test qual="any" name="charset" compare="contains">\n'
    '            <string>Arabic</string>\n'
    '        </test>\n'
    '        <edit name="family" mode="prepend" binding="strong">\n'
    '            <string>Vazirmatn</string>\n'
    '        </edit>\n'
    '    </match>\n'
)
with open(path, 'r', encoding='utf-8') as f:
    data = f.read()
marker = '</fontconfig>'
idx = data.rfind(marker)
if idx < 0:
    raise SystemExit('fonts.conf: </fontconfig> not found; not patching')
data = data[:idx] + rule + data[idx:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(data)
PY
    fi
fi

echo "Installed Persian translation in: $GAME"
echo "Original files are backed up in: $BACKUP"
echo 'The menu translation is incomplete and has not been tested in game.'
echo 'Restart Deadlock for the Vazirmatn font to take effect.'
