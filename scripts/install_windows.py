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
BACKUP = '.deadlock-persian-backup'
LOCK = '.deadlock-persian.lock'


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
    for name in ('menu', 'vpk', 'fonts'):
        state = (backup / f'{name}.state').read_text(encoding='utf-8').strip()
        check = (backup / f'{name}.original').is_dir() if name == 'fonts' else (backup / f'{name}.original').is_file()
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
            if name not in (MENU.as_posix(), VPK.as_posix()) and not name.startswith(FONTS.as_posix() + '/'):
                return False
            expected[name] = digest.lower()
        for name in (MENU.as_posix(), VPK.as_posix()):
            if name not in expected or not (game / name).is_file() or file_hash(game / name) != expected[name]:
                return False
        for name, digest in expected.items():
            if name.startswith(FONTS.as_posix() + '/'):
                if not (game / name).is_file() or file_hash(game / name) != digest:
                    return False
        return True
    except (OSError, ValueError):
        return False


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
        if backup.exists():
            backup_states(backup)
            if not installed_matches(game, backup):
                raise ValueError('Installed files changed or installation was interrupted. Inspect them before updating.')
        else:
            new_backup = stage / 'backup'
            new_backup.mkdir()
            (new_backup / 'format').write_text('deadlock-persian-v1\n', encoding='ascii')
            for name, rel in (('menu', MENU), ('vpk', VPK), ('fonts', FONTS)):
                target = game / rel
                if name == 'fonts':
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
                (new_backup / f'{name}.state').write_text(state + '\\n', encoding='ascii')
            (new_backup / 'fonts.installed').write_text('', encoding='ascii')
            os.replace(new_backup, backup)
        stage_fonts = stage / 'fonts'
        font_lines = []
        for f in sorted(stage_fonts.rglob('*')):
            if f.is_file():
                rel = f.relative_to(stage_fonts).as_posix()
                if rel.startswith('vazirmatn/') and rel.endswith('.ttf'):
                    rel = Path(rel).name
                game_rel = (FONTS / rel).as_posix()
                font_lines.append(f'{file_hash(f)}  {game_rel}\\n')
        hashes = (f'{file_hash(stage / "menu.txt")}  {MENU.as_posix()}\\n'
                  f'{file_hash(stage / VPK)}  {VPK.as_posix()}\\n'
                  + ''.join(font_lines))
        (stage / 'installed.sha256').write_text(hashes, encoding='ascii')
        os.replace(stage / 'installed.sha256', backup / 'installed.sha256')
        (game / MENU).parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage / 'menu.txt', game / MENU)
        os.replace(stage / VPK, game / VPK)
        game_fonts = game / FONTS
        game_fonts.mkdir(parents=True, exist_ok=True)
        manifest_lines = []
        for f in sorted(stage_fonts.rglob('*')):
            if f.is_file():
                rel = f.relative_to(stage_fonts).as_posix()
                if rel.startswith('vazirmatn/') and rel.endswith('.ttf'):
                    rel = Path(rel).name
                manifest_lines.append(f'{rel}\\n')
                dest = game_fonts / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        (backup / 'fonts.installed').write_text(''.join(manifest_lines), encoding='ascii')
    print(f'Installed translation in: {game}\nOriginal files backed up in: {backup}')
    print('Menu translation is incomplete and has not been tested in game.')


def uninstall(game, force):
    backup = game / BACKUP
    states = backup_states(backup)
    if not force and not installed_matches(game, backup):
        raise ValueError('Installed files changed or installation was interrupted. Inspect them before restoring; use --force to restore the backup.')
    with tempfile.TemporaryDirectory(prefix='.deadlock-persian-restore.', dir=game) as tmp:
        stage = Path(tmp)
        for name in ('menu', 'vpk', 'fonts'):
            if states[name] == 'present':
                shutil.copytree(backup / f'{name}.original', stage / f'{name}.original')
        for name, rel in (('menu', MENU), ('vpk', VPK), ('fonts', FONTS)):
            target = game / rel
            if states[name] == 'present':
                if name == 'fonts':
                    shutil.rmtree(target, ignore_errors=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                if name == 'fonts':
                    shutil.copytree(stage / f'{name}.original', target)
                else:
                    os.replace(stage / f'{name}.original', target)
            elif name == 'fonts':
                manifest = backup / 'fonts.installed'
                if manifest.is_file():
                    for line in manifest.read_text(encoding='ascii').splitlines():
                        (game / line).unlink(missing_ok=True)
                shutil.rmtree(target, ignore_errors=True)
            elif target.is_dir() and not target.is_symlink():
                raise ValueError(f'Refusing to remove a directory: {target}')
            else:
                target.unlink(missing_ok=True)
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
            raise ValueError(f'Another operation is running or a stale lock exists: {lock}')
        try:
            if args.action == 'uninstall':
                uninstall(game, args.force)
            else:
                if args.action == 'update' and not (game / BACKUP).exists():
                    raise ValueError('Translation is not installed yet. Run install first.')
                install(game)
        finally:
            lock.rmdir()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
