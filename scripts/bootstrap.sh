#!/usr/bin/env bash
# Fetch a sparse, updatable checkout and install the translation on Linux.
set -Eeuo pipefail
ACTION=${1:-install}
GAME=${2:-}
[[ $ACTION == install || $ACTION == update ]] && (( $# <= 2 )) || { echo 'Usage: bootstrap.sh [install|update] [game/citadel]' >&2; exit 2; }
for tool in git python3 bash; do command -v "$tool" >/dev/null || { echo "Missing dependency: $tool" >&2; exit 1; }; done
REPO='https://github.com/BDadmehr0/deadlock-persian.git'
REF='arena/435414a8-deadlock-persian'
DIR="${XDG_DATA_HOME:-$HOME/.local/share}/deadlock-persian"
if [[ ! -e $DIR ]]; then
    [[ $ACTION == install ]] || { echo 'No checkout found. Run the install command first.' >&2; exit 1; }
    mkdir -p -- "$(dirname -- "$DIR")"
    STAGE=$(mktemp -d "${DIR}.clone.XXXXXXXX")
    trap 'rm -rf -- "$STAGE"' EXIT
    git clone --filter=blob:none --no-checkout --single-branch --branch "$REF" "$REPO" "$STAGE/repo"
    git -C "$STAGE/repo" sparse-checkout init --no-cone
    git -C "$STAGE/repo" sparse-checkout set --no-cone '/.gitignore' '/data/citadel_main_english.txt' '/data/pak82_dir.vpk' '/tools/translate_common.py' '/tools/persian_terms.py' '/install.sh' '/uninstall.sh' '/manage.sh' '/scripts/install_windows.py'
    git -C "$STAGE/repo" checkout "$REF"
    mv -- "$STAGE/repo" "$DIR"
else
    [[ -d "$DIR/.git" ]] || { echo "Not a Git checkout: $DIR" >&2; exit 1; }
    [[ $(git -C "$DIR" remote get-url origin) == "$REPO" ]] || { echo "Unexpected repository origin: $DIR" >&2; exit 1; }
    [[ $(git -C "$DIR" symbolic-ref --short HEAD) == "$REF" ]] || { echo "Unexpected branch in $DIR" >&2; exit 1; }
    [[ -z $(git -C "$DIR" status --porcelain --untracked-files=all) ]] || { echo "Local changes found in $DIR; inspect them before updating." >&2; exit 1; }
    git -C "$DIR" pull --ff-only origin "$REF"
fi
if [[ $ACTION == update ]]; then
    check_game=${GAME:-"$HOME/.local/share/Steam/steamapps/common/Deadlock/game/citadel"}
    [[ -d "$check_game/.deadlock-persian-backup" ]] || { echo 'No existing installation found. Run the install command first.' >&2; exit 1; }
fi
if [[ -n $GAME ]]; then bash "$DIR/install.sh" "$GAME"; else bash "$DIR/install.sh"; fi
