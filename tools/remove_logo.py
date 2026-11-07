#!/usr/bin/env python3
"""Remove branding texture overrides from a standalone VPK v2 package.

The base game supplies these paths; removing overrides allows the game to use
its original artwork. All other entries, especially translations, are kept.
Usage: python3 tools/remove_logo.py [path/to/pak82_dir.vpk]
"""
import argparse
import hashlib
import os
import struct
import tempfile
import zlib
from collections import OrderedDict
from pathlib import Path

TARGETS = {
    'materials/overlays/signs_bodega01a_color_png_93bba988.vtex_c',
    'materials/overlays/signs_bodega01a_color_png_d5c7e675.vtex_c',
    'panorama/images/shop/catalog/catalog_shop_generic_bg2_psd.vtex_c',
}
ENTRY = struct.Struct('<IHHIIH')


def remove_overrides(path):
    raw = path.read_bytes()
    if len(raw) < 28:
        raise ValueError('File too short for a VPK v2 header')
    sig, version, tree_size, data_size, archive_md5_size, other_size, signature_size = struct.unpack_from('<7I', raw)
    if (sig, version, archive_md5_size, other_size, signature_size) != (0x55AA1234, 2, 0, 48, 0):
        raise ValueError('Only standalone unsigned VPK v2 archives without archive MD5 entries are supported')
    if len(raw) != 28 + tree_size + data_size + other_size:
        raise ValueError('Unexpected archive size')
    tree = raw[28:28 + tree_size]
    data = raw[28 + tree_size:28 + tree_size + data_size]
    if hashlib.md5(tree).digest() != raw[-48:-32] or hashlib.md5(b'').digest() != raw[-32:-16] or hashlib.md5(raw[:-16]).digest() != raw[-16:]:
        raise ValueError('VPK checksum mismatch')
    pos = 0
    groups = OrderedDict()
    removed = []
    new_data = bytearray()

    def cstring():
        nonlocal pos
        end = tree.find(b'\0', pos)
        if end < 0:
            raise ValueError('Unterminated VPK directory string')
        result = tree[pos:end].decode('utf-8')
        pos = end + 1
        return result

    while (ext := cstring()):
        while (folder := cstring()):
            while (name := cstring()):
                if pos + ENTRY.size > len(tree):
                    raise ValueError('Truncated directory entry')
                crc, preload, archive, offset, length, terminator = ENTRY.unpack_from(tree, pos)
                pos += ENTRY.size
                if archive != 0x7FFF or preload != 0 or terminator != 0xFFFF:
                    raise ValueError('Unsupported VPK entry')
                content = data[offset:offset + length]
                if len(content) != length or zlib.crc32(content) != crc:
                    raise ValueError('Corrupt VPK entry')
                virtual = ('' if folder == ' ' else folder + '/') + name + ('' if ext == ' ' else '.' + ext)
                if virtual in TARGETS:
                    removed.append(virtual)
                    continue
                entry = ENTRY.pack(crc, 0, archive, len(new_data), length, terminator)
                groups.setdefault(ext, OrderedDict()).setdefault(folder, []).append((name, entry))
                new_data.extend(content)
    if pos != len(tree):
        raise ValueError('Unexpected VPK tree bytes')
    if not removed:
        print('No branding overrides found; no changes made.')
        return
    new_tree = bytearray()
    def put(value):
        new_tree.extend(value.encode('utf-8') + b'\0')
    for ext, folders in groups.items():
        put(ext)
        for folder, entries in folders.items():
            put(folder)
            for name, entry in entries:
                put(name)
                new_tree.extend(entry)
            put('')
        put('')
    put('')
    header = struct.pack('<7I', sig, version, len(new_tree), len(new_data), 0, 48, 0)
    body = header + new_tree + new_data
    checksums = hashlib.md5(new_tree).digest() + hashlib.md5(b'').digest()
    output = body + checksums + hashlib.md5(body + checksums).digest()
    # Replace only once the complete new archive has been written successfully.
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.vpk-', delete=False) as temp:
            temp_name = temp.name
            temp.write(output)
            temp.flush()
            os.fsync(temp.fileno())
        os.chmod(temp_name, path.stat().st_mode & 0o777)
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            os.unlink(temp_name)
    print(f'Removed {len(removed)} texture overrides from {path}:')
    for name in removed:
        print('  ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vpk', nargs='?', type=Path, default=Path('data/pak82_dir.vpk'))
    args = parser.parse_args()
    remove_overrides(args.vpk)


if __name__ == '__main__':
    main()
