#!/usr/bin/env python3
"""Install/update or uninstall the translation on Windows using Python 3.

Also accepts --game-dir for non-default Steam libraries. Original files are
backed up using the same format as the Linux installer.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENU = Path('resource/localization/citadel_main/citadel_main_english.txt')
VPK = Path('pak82_dir.vpk')
FONTS = Path('panorama/fonts')
CORE_FONTS = Path('core/panorama/fonts')
BACKUP = '.deadlock-persian-backup'
LOCK = '.deadlock-persian.lock'
PATCH_MARKER = 'deadlock-persian'
PATCH_START = '<!-- deadlock-persian'
PATCH_END = '</fontconfig>'
PATCH_RULE = (
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
FONT_DIRS = (FONTS, CORE_FONTS)


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_game(path):
    path = path.expanduser().resolve()
    if not path.is_dir() or not any((path / p).is_file() for p in (MENU, VPK, Path('pak01_dir.vpk'))):
        raise ValueError(f'Not a Deadlock game/citadel directory: {path}')
    return path


def find_game():
    if sys.platform != 'win32':
        return None
    import winreg
    roots = []
    for hive, key, value in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                              (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')):
        try:
            with winreg.OpenKey(hive, key) as reg:
                roots.append(Path(winreg.QueryValueEx(reg, value)[0]))
        except OSError:
            pass
    for var in ('ProgramFiles(x86)', 'ProgramFiles'):
        if os.environ.get(var):
            roots.append(Path(os.environ[var]) / 'Steam')
    libraries = list(roots)
    for root in roots:
        file = root / 'steamapps' / 'libraryfolders.vdf'
        try:
            contents = file.read_text(encoding='utf-8-sig', errors='replace')
            for match in re.finditer(r'"path"\s+"((?:\\.|[^"\\])*)"', contents, re.I):
                libraries.append(Path(match.group(1).replace('\\\\', '\\')))
        except OSError:
            pass
    for lib in libraries:
        candidate = lib / 'steamapps' / 'common' / 'Deadlock' / 'game' / 'citadel'
        try:
            return validate_game(candidate)
        except ValueError:
            pass
    return None


def backup_states(backup):
    if not backup.is_dir() or (backup / 'format').read_text(encoding='utf-8').strip() != 'deadlock-persian-v1':
        raise ValueError(f'Invalid backup directory: {backup}')
    states = {}
    for name in ('menu', 'vpk', 'fonts', 'corefonts'):
        state_file = backup / f'{name}.state'
        # Backwards compatibility: backups made before the font addition only
        # contain menu.state / vpk.state; treat missing entries as absent.
        if state_file.is_file():
            state = state_file.read_text(encoding='utf-8').strip()
        else:
            state = 'absent'
        check = (backup / f'{name}.original').is_dir() if name in ('fonts', 'corefonts') else (backup / f'{name}.original').is_file()
        if state not in ('present', 'absent') or (state == 'present' and not check):
            raise ValueError(f'Backup is incomplete for {name}')
        states[name] = state
    return states


def installed_matches(game, backup):
    try:
        lines = (backup / 'installed.sha256').read_text(encoding='ascii').splitlines()
        expected = {}
        for line in lines:
            digest, name = line.split('  ', 1)
            if not re.fullmatch(r'[a-fA-F0-9]{64}', digest):
                return False
            if name not in (MENU.as_posix(), VPK.as_posix()) and not any(
                    name.startswith(d.as_posix() + '/') for d in FONT_DIRS):
                return False
            expected[name] = digest.lower()
        for name in (MENU.as_posix(), VPK.as_posix()):
            if name not in expected or not (game / name).is_file() or file_hash(game / name) != expected[name]:
                return False
        for name, digest in expected.items():
            if any(name.startswith(d.as_posix() + '/') for d in FONT_DIRS):
                if not (game / name).is_file() or file_hash(game / name) != digest:
                    return False
        return True
    except (OSError, ValueError):
        return False


def font_dest_rel(rel):
    # TTFs land at each font dir root; everything else keeps its subdirectory.
    if rel.startswith('vazirmatn/') and rel.endswith('.ttf'):
        return Path(Path(rel).name)
    return Path(rel)


def patch_fonts_conf(conf):
    """Insert the Vazirmatn rule before </fontconfig>; no-op if already patched."""
    if not conf.is_file() or conf.is_symlink():
        return
    data = conf.read_text(encoding='utf-8')
    if PATCH_MARKER in data:
        return
    idx = data.rfind(PATCH_END)
    if idx < 0:
        raise ValueError(f'{conf}: {PATCH_END} not found; not patching')
    conf.write_text(data[:idx] + PATCH_RULE + data[idx:], encoding='utf-8')


def unpatch_fonts_conf(conf):
    """Remove our rule from fonts.conf (leaves the rest of the file untouched)."""
    if not conf.is_file():
        return
    data = conf.read_text(encoding='utf-8')
    i = data.find(PATCH_START)
    if i < 0:
        return
    j = data.rfind(PATCH_END)
    if j < 0 or j < i:
        return
    conf.write_text(data[:i] + data[j:], encoding='utf-8')


def install(game):
    backup = game / BACKUP
    src_menu, src_vpk = ROOT / 'data/citadel_main_english.txt', ROOT / 'data/pak82_dir.vpk'
    src_fonts = ROOT / 'data/fonts'
    translator = ROOT / 'tools/translate_common.py'
    if (not all(p.is_file() for p in (src_menu, src_vpk, translator, ROOT / 'tools/persian_terms.py'))
            or not src_fonts.is_dir()):
        raise ValueError('Missing translation data, fonts, or translation tools')
    with tempfile.TemporaryDirectory(prefix='.deadlock-persian-stage.', dir=game) as tmp:
        stage = Path(tmp)
        shutil.copy2(src_menu, stage / 'menu.txt')
        shutil.copy2(src_vpk, stage / VPK)
        shutil.copytree(src_fonts, stage / 'fonts')
        subprocess.run([sys.executable, str(translator), str(stage / VPK)], check=True)
        items = (('menu', MENU), ('vpk', VPK), ('fonts', FONTS), ('corefonts', CORE_FONTS))
        if backup.exists():
            backup_states(backup)
            if not installed_matches(game, backup):
                raise ValueError('Installed files changed or installation was interrupted. Inspect them before updating.')
        else:
            new_backup = stage / 'backup'
            new_backup.mkdir()
            (new_backup / 'format').write_text('deadlock-persian-v1\n', encoding='ascii')
            for name, rel in items:
                target = game / rel
                if name in ('fonts', 'corefonts'):
                    if target.is_symlink() or (target.exists() and not target.is_dir()):
                        raise ValueError(f'Refusing to replace a non-directory: {target}')
                    state = 'present' if target.is_dir() else 'absent'
                    if state == 'present':
                        shutil.copytree(target, new_backup / f'{name}.original')
                else:
                    if target.is_symlink() or (target.exists() and not target.is_file()):
                        raise ValueError(f'Refusing to replace a non-regular file: {target}')
                    state = 'present' if target.is_file() else 'absent'
                    if state == 'present':
                        shutil.copy2(target, new_backup / f'{name}.original')
                (new_backup / f'{name}.state').write_text(state + '\n', encoding='ascii')
            (new_backup / 'fonts.installed').write_text('', encoding='ascii')
            os.replace(new_backup, backup)
        stage_fonts = stage / 'fonts'
        # Fresh manifest of installed font files (relative to each font dir).
        manifest_lines = []
        font_hashes = []
        for f in sorted(stage_fonts.rglob('*')):
            if f.is_file():
                rel = f.relative_to(stage_fonts).as_posix()
                dest_rel = font_dest_rel(rel).as_posix()
                manifest_lines.append(dest_rel + '\n')
                for dir_rel in FONT_DIRS:
                    font_hashes.append(f'{file_hash(f)}  {(dir_rel / dest_rel).as_posix()}\n')
        (backup / 'fonts.installed').write_text(''.join(manifest_lines), encoding='ascii')
        hashes = (f'{file_hash(stage / "menu.txt")}  {MENU.as_posix()}\n'
                  f'{file_hash(stage / VPK)}  {VPK.as_posix()}\n'
                  + ''.join(font_hashes))
        (stage / 'installed.sha256').write_text(hashes, encoding='ascii')
        os.replace(stage / 'installed.sha256', backup / 'installed.sha256')
        (game / MENU).parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage / 'menu.txt', game / MENU)
        os.replace(stage / VPK, game / VPK)
        for dir_rel in FONT_DIRS:
            game_fonts = game / dir_rel
            game_fonts.mkdir(parents=True, exist_ok=True)
            for f in sorted(stage_fonts.rglob('*')):
                if f.is_file():
                    rel = f.relative_to(stage_fonts).as_posix()
                    dest = game_fonts / font_dest_rel(rel)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
        # Patch fonts.conf in both font dirs so whichever one Panorama loads
        # picks up Vazirmatn for Arabic-script (Persian) UI text.
        for dir_rel in FONT_DIRS:
            patch_fonts_conf(game / dir_rel / 'fonts.conf')
        # Record which fonts.conf files carry our rule so uninstall can strip
        # it even when no directory backup exists.
        patched = []
        for dir_rel in FONT_DIRS:
            conf = game / dir_rel / 'fonts.conf'
            if conf.is_file() and PATCH_MARKER in conf.read_text(encoding='utf-8'):
                patched.append((dir_rel / 'fonts.conf').as_posix() + '\n')
        (backup / 'fonts.conf.patched').write_text(''.join(patched), encoding='ascii')
    print(f'Installed translation in: {game}\nOriginal files backed up in: {backup}')
    print('Menu translation is incomplete and has not been tested in game.')
    print('Restart Deadlock for the Vazirmatn font to take effect.')


def uninstall(game, force):
    backup = game / BACKUP
    states = backup_states(backup)
    if not force and not installed_matches(game, backup):
        raise ValueError('Installed files changed or installation was interrupted. Inspect them before restoring; use --force to restore the backup.')
    with tempfile.TemporaryDirectory(prefix='.deadlock-persian-restore.', dir=game) as tmp:
        stage = Path(tmp)
        items = (('menu', MENU), ('vpk', VPK), ('fonts', FONTS), ('corefonts', CORE_FONTS))
        for name, rel in items:
            if states[name] == 'present':
                src = backup / f'{name}.original'
                if name in ('fonts', 'corefonts'):
                    shutil.copytree(src, stage / f'{name}.original')
                else:
                    shutil.copy2(src, stage / f'{name}.original')
        for name, rel in items:
            target = game / rel
            if states[name] == 'present':
                if name in ('fonts', 'corefonts'):
                    shutil.rmtree(target, ignore_errors=True)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(stage / f'{name}.original', target)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(stage / f'{name}.original', target)
            elif name in ('fonts', 'corefonts'):
                manifest = backup / 'fonts.installed'
                if manifest.is_file():
                    for line in manifest.read_text(encoding='ascii').splitlines():
                        for dir_rel in FONT_DIRS:
                            (game / dir_rel / line).unlink(missing_ok=True)
                for dir_rel in FONT_DIRS:
                    d = game / dir_rel
                    if d.is_dir():
                        for sub in sorted((p for p in d.rglob('*') if p.is_dir()), reverse=True):
                            try:
                                sub.rmdir()
                            except OSError:
                                pass
                        try:
                            d.rmdir()
                        except OSError:
                            pass
            elif target.is_dir() and not target.is_symlink():
                raise ValueError(f'Refusing to remove a directory: {target}')
            else:
                target.unlink(missing_ok=True)
        # Strip our fonts.conf rule from any patched config. Handles backups
        # that predate the font feature, where the game's own fonts.conf was
        # patched in place and cannot be restored from a backup copy.
        patched_list = backup / 'fonts.conf.patched'
        if patched_list.is_file():
            for line in patched_list.read_text(encoding='ascii').splitlines():
                if line.strip():
                    unpatch_fonts_conf(game / line.strip())
    shutil.rmtree(backup)
    print(f'Translation removed; original files restored: {game}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', nargs='?', default='install', choices=('install', 'update', 'uninstall'))
    p.add_argument('--game-dir', type=Path, help='path to Deadlock/game/citadel')
    p.add_argument('--force', action='store_true', help='restore original backups even if installed files changed (uninstall only)')
    args = p.parse_args()
    if args.force and args.action != 'uninstall':
        p.error('--force is only supported for uninstall')
    try:
        game = validate_game(args.game_dir) if args.game_dir else find_game()
        if game is None:
            if not sys.stdin.isatty():
                raise ValueError('Could not find Deadlock. Run with --game-dir "C:\\path\\to\\Deadlock\\game\\citadel".')
            game = validate_game(Path(input('Deadlock game/citadel directory: ').strip().strip('"')))
        lock = game / LOCK
        try:
            lock.mkdir()
        except FileExistsError:
            raise ValueError(f'Another install/uninstall is running, or a stale lock exists: {lock}')
        try:
            if args.action == 'uninstall':
                uninstall(game, args.force)
            else:
                install(game)
        finally:
            try:
                lock.rmdir()
            except OSError:
                pass
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f'install_windows.py: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
