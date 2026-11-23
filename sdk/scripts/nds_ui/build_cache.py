"""Local, content-checked build acceleration. NDS_UI_NO_CACHE=1 forces the original path.

Cache entries are hints: missing/corrupt receipts or artifacts cause regeneration. They never
replace firmware gates or review. Keys include tool binaries and build implementation bytes.
"""
import hashlib
import json
import os
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def key(*parts):
    return digest(json.dumps(parts, sort_keys=True, default=str).encode())


def implementation(root, gcc_bin):
    paths = sorted(p for p in (root / 'scripts/nds_ui').rglob('*.py') if 'tests' not in p.parts)
    paths += sorted(gcc_bin.glob('nds32le-elf-*'))
    paths += sorted((gcc_bin.parent / 'libexec').rglob('cc1'))
    return key([(str(p.relative_to(root)), digest(p.read_bytes())) for p in paths if p.is_file()])


def load(path, expected):
    if os.environ.get('NDS_UI_NO_CACHE') == '1':
        return None
    try:
        entry = json.loads(path.read_text())
        if digest(json.dumps(entry['value'], sort_keys=True).encode()) != entry['value_sha256']:
            return None
        if entry['key'] != expected:
            return None
        for name, sha in entry['artifacts'].items():
            if digest((path.parent / name).read_bytes()) != sha:
                return None
        return entry['value']
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def save(path, expected, value, artifacts=()):
    entry = dict(key=expected, value=value, value_sha256=digest(json.dumps(value, sort_keys=True).encode()),
                 artifacts={p.name: digest(p.read_bytes()) for p in artifacts})
    # The caller holds the image lock. Replace only a complete receipt.
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(entry, sort_keys=True) + '\n')
    temporary.replace(path)
