#!/usr/bin/env python3
"""Inventory Deadlock localization and in-map text assets without extracting VPKs.

Run from game/citadel: python3 /path/to/inspect_vpk.py
Optionally pass another game directory and/or --output REPORT. The script only
reads the game files; it writes a UTF-8 report in the current directory by default.
"""
from __future__ import annotations

import argparse
import collections
import re
import struct
import sys
from pathlib import Path

SIGNATURE = 0x55AA1234
INLINE_ARCHIVE = 0x7FFF
ENTRY = struct.Struct('<IHHIIH')
MAX_TREE_BYTES = 128 * 1024 * 1024


def read_directory(path):
    """Yield (virtual path, archive index, offset, size, preload bytes)."""
    with path.open('rb') as f:
        header = f.read(12)
        if len(header) != 12:
            raise ValueError('header is too short')
        signature, version, tree_size = struct.unpack('<III', header)
        if signature != SIGNATURE or version not in (1, 2):
            raise ValueError(f'unsupported signature/version: {signature:#x}, {version}')
        header_size = 12 if version == 1 else 28
        if tree_size > MAX_TREE_BYTES or tree_size > max(0, path.stat().st_size - header_size):
            raise ValueError(f'invalid directory tree size: {tree_size}')
        f.seek(header_size)
        tree = f.read(tree_size)
    pos = 0

    def cstring():
        nonlocal pos
        end = tree.find(b'\0', pos)
        if end < 0:
            raise ValueError('unterminated string in directory tree')
        value = tree[pos:end].decode('utf-8', errors='replace')
        pos = end + 1
        return value

    while True:
        ext = cstring()
        if not ext:
            break
        while True:
            folder = cstring()
            if not folder:
                break
            while True:
                name = cstring()
                if not name:
                    break
                if pos + ENTRY.size > len(tree):
                    raise ValueError('truncated directory entry')
                _crc, preload, archive, offset, size, terminator = ENTRY.unpack_from(tree, pos)
                pos += ENTRY.size
                if terminator != 0xFFFF or pos + preload > len(tree):
                    raise ValueError('invalid entry terminator or preload')
                pos += preload
                prefix = '' if folder == ' ' else folder + '/'
                suffix = '' if ext == ' ' else '.' + ext
                yield prefix + name + suffix, archive, offset, size, preload
    if pos != len(tree):
        raise ValueError('unexpected trailing bytes in directory tree')


def categories(path):
    lower = path.lower().replace('\\', '/')
    base = lower.rsplit('/', 1)[-1]
    result = []
    # Localization files are the most useful sources for menu translations.
    if ('localization/' in lower or 'localisation/' in lower or
        (re.search(r'(?:^|[_./-])(english|persian|farsi)(?:[_./-]|$)', lower)
         and not lower.endswith(('.vsnd_c', '.vtex_c')))):
        result.append('Localization / language files')
    # Text that may be baked into a UI texture rather than a translation token.
    if (lower.endswith(('.vtex_c', '.png', '.jpg', '.jpeg', '.psd')) and
        ('panorama/' in lower and any(x in lower for x in ('text_images/', 'main_menu/', '/menu/')))):
        result.append('UI and menu images')
    # Keep likely world signage separate from menus. These are only candidates.
    if (lower.endswith(('.vtex_c', '.vmat_c', '.png', '.jpg', '.jpeg', '.psd')) and
        any(re.search(r'(?:^|[/_.-])' + term + r'(?:[/_.-]|\d|$)', lower)
            for term in ('sign', 'signs', 'billboard', 'poster', 'advert', 'advertisement', 'decal', 'graffiti'))):
        result.append('Possible in-map signs / posters')
    if ('panorama/' in lower and lower.endswith(('.vxml_c', '.vjs_c', '.vcss_c', '.xml', '.js', '.css')) and
        any(x in lower for x in ('main_menu', 'mainmenu', 'settings', 'pause_menu'))):
        result.append('Menu layout / script candidates')
    return result


def chunk_name(directory, archive):
    if archive == INLINE_ARCHIVE:
        return directory.name + ' (stored in directory file)'
    prefix = directory.name[:-len('_dir.vpk')]
    return f'{prefix}_{archive:03d}.vpk'


def inspect(root):
    reports = []
    directories = sorted(root.glob('*_dir.vpk'), key=lambda p: p.name.lower())
    reports.append('Deadlock VPK inventory (filenames and offsets only; no game file contents)')
    reports.append(f'VPK directory files found: {len(directories)}')
    grouped = collections.defaultdict(list)
    errors = []
    for directory in directories:
        count = 0
        try:
            for virtual, archive, offset, size, preload in read_directory(directory):
                count += 1
                tags = categories(virtual)
                if not tags:
                    continue
                chunk = chunk_name(directory, archive)
                exists = archive == INLINE_ARCHIVE or (root / chunk).is_file()
                line = (f'{directory.name} | {chunk} | {virtual} | '
                        f'offset={offset} | bytes={size} | preload={preload} | '
                        f'archive={"present" if exists else "MISSING"}')
                for tag in tags:
                    grouped[tag].append(line)
            reports.append(f'  {directory.name}: {count} entries')
        except (OSError, ValueError, struct.error) as exc:
            errors.append(f'{directory.name}: {exc}')
            reports.append(f'  {directory.name}: ERROR (see below)')

    # Some Steam builds ship localization as loose files rather than VPK entries.
    loose = []
    for base in (root / 'resource' / 'localization', root / 'resource' / 'localisation'):
        if base.is_dir():
            try:
                loose.extend(p.relative_to(root).as_posix() for p in base.rglob('*') if p.is_file())
            except OSError as exc:
                errors.append(f'Loose localization files: {exc}')
    reports.append('\n=== Loose localization files ===')
    reports.append(f'Count: {len(loose)}')
    reports.extend(sorted(loose))
    for title in ('Localization / language files', 'UI and menu images',
                  'Possible in-map signs / posters', 'Menu layout / script candidates'):
        rows = grouped[title]
        reports.append(f'\n=== {title} ===')
        reports.append(f'Count: {len(rows)}')
        reports.extend(sorted(rows))
    if errors:
        reports.append('\n=== Errors ===')
        reports.extend(errors)
    if not directories:
        reports.append('\nNo *_dir.vpk files found. Run in the game/citadel directory or pass its path.')
    return '\n'.join(reports) + '\n', errors, bool(directories)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_dir', nargs='?', default='.', help='directory containing *_dir.vpk files (default: current directory)')
    parser.add_argument('--output', default='deadlock_vpk_report.txt', help='report file (default: ./deadlock_vpk_report.txt)')
    args = parser.parse_args()
    root = Path(args.game_dir).expanduser()
    if not root.is_dir():
        print(f'Game directory not found: {root}', file=sys.stderr)
        return 2
    report, errors, found = inspect(root)
    output = Path(args.output).expanduser()
    try:
        output.write_text(report, encoding='utf-8')
    except OSError as exc:
        print(f'Could not write report: {exc}', file=sys.stderr)
        return 2
    print(f'Report written to: {output.resolve()}')
    print('Send this report; it contains filenames and offsets, not game file contents.')
    if errors:
        print(f'Warning: {len(errors)} file(s) could not be inspected; see Errors in report.', file=sys.stderr)
    return 0 if found and not errors else 1


if __name__ == '__main__':
    sys.exit(main())
