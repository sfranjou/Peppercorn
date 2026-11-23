"""Explicit offline-only expanded-E policy; no device/updater operations.

The 0x3f000 payload limit accounts for Suite's two-byte prefix and boot's
extra-sector erase rounding. Target acceptance/flash-gap ownership remain
qualification requirements, not consequences of this arithmetic policy.
"""
import struct

BASE = 0x190000
STOCK_LENGTH = 0x2d000
EXPANDED_LENGTH = 0x3f000
GROWTH_RANGE = (BASE + STOCK_LENGTH, BASE + EXPANDED_LENGTH)
SETTINGS = 0x1d0000


def enabled(cfg):
    value = (cfg or {}).get('expanded_e')
    if value is None:
        return False
    if value != 'offline_0x3f000' or not cfg.get('component_only'):
        raise ValueError('expanded E requires explicit offline component draft policy')
    return True


def pcm_ranges(raw):
    """Stock PCM table's reachable extents, not a claim of valid sample contents.

    Stock init 0x17a16 converts durations into 128-byte mixer blocks. An erased
    table is accepted only for synthetic placement fixtures; stock has count 4.
    Unknown populated table layouts fail closed rather than claiming free flash.
    """
    table = 0x1b8000 - BASE
    if len(raw) < table + 4:
        raise ValueError('E prefix lacks PCM ownership table')
    count = struct.unpack_from('<I', raw, table)[0]
    if count == 0xffffffff:
        if raw[table:] != b'\xff' * (len(raw)-table):
            raise ValueError('unknown PCM ownership table')
        return []
    if count > 4:
        raise ValueError('unknown PCM ownership table count')
    rows = []
    for i in range(count):
        offset = struct.unpack_from('<I', raw, table+4*(i+1))[0]
        duration = struct.unpack_from('<I', raw, table+4*(count+i+1))[0]
        start = BASE + table + offset
        end = start + (((duration & 65535)*44) >> 6)*128
        if start >= 0x100000000 or end >= 0x100000000:
            raise ValueError('PCM ownership extent overflows')
        rows.append((start,end))
    return rows


def extend(cfg, raw):
    if not enabled(cfg):
        return raw
    if len(raw) != STOCK_LENGTH:
        raise ValueError('expanded E must derive from the exact stock-length E prefix')
    erase_length = ((EXPANDED_LENGTH + 2) & ~0xfff) + 0x1000
    if BASE + erase_length != SETTINGS or erase_length > 0x50000:
        raise ValueError('expanded E erase boundary')
    conflicts = [(lo,hi) for lo,hi in pcm_ranges(raw) if lo < SETTINGS and hi > BASE+STOCK_LENGTH and lo < hi]
    if conflicts:
        raise ValueError('expanded E conflicts with stock PCM reads: ' + ', '.join(f'{lo:#x}..{hi:#x}' for lo,hi in conflicts))
    return raw + b'\xff' * (EXPANDED_LENGTH - len(raw))
