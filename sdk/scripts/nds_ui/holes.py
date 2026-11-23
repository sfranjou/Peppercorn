"""Code room step 2 (analysis/firmware/NDS_CODE_ROOM.md section 3; first image MOD056): dead stock bodies behind the
stock entries an image redirects to our C, as room for compiled C (cfg "code_holes").

A redirected stock function keeps a 4-byte `j` at its entry; the rest of its body (Ghidra function index, the body range
holding the entry) is a hole [align4(entry + 4), body end + 1) if nothing other than the entry `j` can reach it:
  (a) no branch/jump in the stock listing from outside that body range targets (entry, body end] — a target in
      (entry, entry + 4) would even break the redirect itself and is a build error;
  (b) no sethi/ori constant outside the body equals an address in (entry, body end];
  (c) no 4-aligned data word of region b outside every function body (tables, pointers) equals an EVEN address in
      (entry, body end] (NDS32 instructions are 2-byte aligned: an odd word cannot be a code address), unless the word is
      listed in INSPECTED with the reason it is not a pointer into that body;
  (d) no undiscovered code reaches it: every halfword-aligned 32-bit j/jal encoding outside the function bodies of the
      stock listing that targets the body (raw scan of the gaps, conservative);
  (e) no hook the image declares lies inside it (hooks of the parent inside a replaced body must be dropped by the
      features: the C replacing the body reproduces them);
  (f) at least MIN bytes.
The image proof (scripts/verify_nds_code_holes.py) re-checks the built image independently: no instruction outside our
code reaches into a hole, and every reach from our code lands on a symbol of the C placed there."""
import bisect, json, re
from functools import lru_cache
from .build import ROOT
from .compat import load_stock_facts

MIN = 64
# Matches of (c)/(d) inspected by hand (2026-10-23, NDS_CODE_ROOM.md section 8.2): site -> (value, reason). Only an exact
# (site, value) listed here is released; anything else found keeps its hole closed. Evidence for the data words: none of
# the 32 neighbouring words is a function entry (a pointer table would hold entries) and the values follow the pattern of
# the surrounding non-pointer data; two sites are instruction bytes inside listed code read as a word.
_TABLE = 'byte/glyph descriptor table: no neighbouring word (+-16) is a function entry; value pattern of the table'
INSPECTED = {
    0x143d64: (0x40900, _TABLE), 0x145000: (0x40912, 'arithmetic byte table (00010306, 00018408, 0002050a, ...); no neighbour is a function entry'),
    0xaa670: (0x418c0, 'instruction bytes inside listed code (not a data word)'), 0x1346a8: (0x42c1a, _TABLE),
    0x134440: (0x43738, _TABLE), 0x134498: (0x43726, _TABLE), 0x1344c8: (0x43726, _TABLE), 0x1344d8: (0x43726, _TABLE),
    0x33d2c: (0x44138, 'instruction bytes inside listed code (not a data word)'), 0x166038: (0x46000, 'bitmap data; no neighbour is a function entry'),
    0x157566: (0x19952, 'raw scan: a descending 16-bit table (f818 f7dd f7a2 ...) read at a halfword offset, not code'),
    # Exact MOD079 releases; byte windows and disassembly: analysis/firmware/MOD079_HOLE_REVIEW_20261026.md.
    0x1353c: (0x22166, 'NDS32 instruction bytes in undiscovered code; decoded window saved under mod079_hole_review'),
    0x68fa4: (0x2074e, 'NDS32 instruction bytes in undiscovered code; decoded window saved under mod079_hole_review'),
    0x9e1cc: (0x20280, 'NDS32 instruction bytes in undiscovered code; decoded window saved under mod079_hole_review'),
    0x9e354: (0x20280, 'NDS32 instruction bytes in undiscovered code; decoded window saved under mod079_hole_review'),
    0xd1c80: (0x20354, 'NDS32 instruction bytes in undiscovered code; decoded window saved under mod079_hole_review'),
    0xd5d8c: (0x20202, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5dbc: (0x20302, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5dec: (0x20402, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5e14: (0x20502, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5e3c: (0x20602, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5f5c: (0x20202, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5f8c: (0x20302, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5fbc: (0x20402, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd5fec: (0x20502, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0xd601c: (0x20602, 'packed descriptor ordinal/type bytes between repeated 0x228b6/0x22a5c pointers'),
    0x144de8: (0x20a28, 'arithmetic byte table, successive offsets and high-bit byte pattern; not pointers'),
    0x144ff0: (0x2050a, 'arithmetic byte table, successive offsets and high-bit byte pattern; not pointers'),
    0x164a7c: (0x203fe, 'bitmap halfwords in a repeated glyph block, not a pointer field'),
    0x16529c: (0x20202, 'packed byte grid beside zero/ffffffff padding, not a pointer array'),
    0x166554: (0x22002, 'first packed descriptor word: sequential ID 0x20xx plus type/flags; pointers are the following two words'),
    0x1665d8: (0x2200e, 'first packed descriptor word: sequential ID 0x20xx plus type/flags; pointers are the following two words'),
    0x1665f0: (0x22010, 'first packed descriptor word: sequential ID 0x20xx plus type/flags; pointers are the following two words'),
    0x166650: (0x22018, 'first packed descriptor word: sequential ID 0x20xx plus type/flags; pointers are the following two words'),
    0x166680: (0x2201c, 'first packed descriptor word: sequential ID 0x20xx plus type/flags; pointers are the following two words'),
    0x16671c: (0x2202a, 'first packed descriptor word: sequential ID 0x20xx plus type/flags; pointers are the following two words'),

    # Additional MOD079 exact false references; evidence in MOD079_HOLE_REVIEW_20261026.md.
    0x156de6: (0x271d2, 'ascending signed 16-bit waveform samples, halfword-shifted raw jump coincidence'),
    0x15a2a0: (0x17a88, 'descending signed 16-bit waveform samples, halfword-shifted raw jump coincidence'),
    0x127c78: (0x22c00, 'GIF89a frame block terminator and image descriptor bytes'),
    0x67edc: (0x44b6a, 'NDS32 FPU instruction bytes in undiscovered code; saved disassembly'),
    0xd1a90: (0x16358, 'NDS32 instruction bytes in undiscovered code; saved disassembly'),
    0x11f0c: (0x43200, 'NDS32 instruction bytes in undiscovered code; saved disassembly'),
    0xd59d4: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd5b18: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd5c00: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd5c70: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd5d44: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd5edc: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd60bc: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd6274: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd6284: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd63ac: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd69a4: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0xd6a58: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),
    0x12dac0: (0x48002, 'packed message tag 0x00048002 between callback words; type 0x8002 and index4'),

}


@lru_cache(maxsize=1)
def stock():
    """(instructions [(address, size, mnemonic, operands)], references [(site, kind, target)], bodies {entry: [(lo, hi)]},
    sorted code ranges) of stock V1.1.0 region b."""
    ins = []
    for line in (ROOT / 'firmware/decompiled/nds_main/listing.asm').read_text().splitlines():
        m = re.match(r'ram:([0-9a-f]{8}) ([0-9a-f]+) (\S+)\s*(.*)$', line)
        if m: ins.append((int(m.group(1), 16), len(m.group(2)) // 2, m.group(3), m.group(4)))
    refs = []; hi = {}
    for at, sz, mn, ops in ins:
        if mn == 'sethi':
            m = re.match(r'(\w+),0x([0-9a-f]+)$', ops)
            if m: hi[m.group(1)] = int(m.group(2), 16) << 12
            continue
        if mn == 'ori':
            m = re.match(r'(\w+),(\w+),0x([0-9a-f]+)$', ops)
            if m and m.group(2) in hi: refs.append((at, 'const', hi[m.group(2)] | int(m.group(3), 16)))
            continue
        if mn.startswith(('j', 'b')) and mn not in ('bset', 'bclr', 'btgl', 'btst', 'bitc', 'bitci', 'bmski33'):
            for t in re.findall(r'0x([0-9a-f]{8})', ops): refs.append((at, mn, int(t, 16)))
    idx = json.loads((ROOT / 'firmware/decompiled/nds_main/index.json').read_text())
    bodies = {int(f['entry'].split(':')[1], 16): [(int(r['start'].split(':')[1], 16), int(r['end_inclusive'].split(':')[1], 16)) for r in f['body_ranges']]
              for f in idx['functions']}
    code = sorted(r for rs in bodies.values() for r in rs)
    return ins, refs, bodies, code


@lru_cache(maxsize=1)
def stock_facts():
    """Pinned build facts; no decompiler-tree reads or instruction text."""
    return load_stock_facts(ROOT)


def in_code(a, code):
    i = bisect.bisect_right(code, (a, 1 << 40)) - 1
    return i >= 0 and code[i][0] <= a <= code[i][1]


def analyse(entries, b, base, hook_sites, min_size=MIN):
    """Rows per redirected entry: hole range, usable bytes and the reasons when closed. `b` is the image's region b (data
    words are read from it below `base`), `hook_sites` the addresses of every hook the image declares (with lengths)."""
    _, refs, bodies, code = stock_facts()
    words = [(o + 0x10000, int.from_bytes(b[o:o + 4], 'little')) for o in range(0, min(len(b), base - 0x10000) - 3, 4) if not in_code(o + 0x10000, code)]
    # (d) raw j/jal encodings in the gaps between discovered functions (big-endian 32-bit instruction words)
    raw = []
    for o in range(0, min(len(b), base - 0x10000) - 3, 2):
        if b[o] >> 1 != 0x24 or in_code(o + 0x10000, code): continue
        w = int.from_bytes(b[o:o + 4], 'big'); d = w & 0xffffff; d -= (1 << 24) if d >> 23 else 0
        raw.append((o + 0x10000, (o + 0x10000 + 2 * d) & 0xffffffff))
    rows = []
    for e in sorted(entries):
        body = next((r for r in bodies.get(e, []) if r[0] <= e <= r[1]), None)
        if not body: rows.append(dict(entry=hex(e), usable=0, reason='no function body in the index')); continue
        lo, end = (e + 4 + 3) & ~3, body[1] + 1
        outside = lambda at: not (body[0] <= at <= body[1])
        broken = [f'{k} at {at:#x} -> {t:#x}' for at, k, t in refs if e < t < e + 4 and outside(at)]
        if broken: raise ValueError(f'redirected entry {e:#x}: stock code enters inside the 4-byte j ({broken[:3]})')
        inside = lambda a: e < a < end
        why = [f'{k} at {at:#x} -> {t:#x}' for at, k, t in refs if inside(t) and outside(at)]
        why += [f'data word at {a:#x} = {v:#x}' for a, v in words if inside(v) and not v & 1 and INSPECTED.get(a, (None,))[0] != v]
        why += [f'raw j/jal at {a:#x} -> {t:#x} (undiscovered code?)' for a, t in raw if inside(t) and INSPECTED.get(a, (None,))[0] != t]
        why += [f'hook {a:#x}' for a, n in hook_sites if a < end and a + n > e + 4]
        size = max(0, end - lo); row = dict(entry=hex(e), body=[hex(body[0]), hex(body[1])], hole=[hex(lo), hex(end)], size=size)
        released = [f'data word at {a:#x} = {v:#x}: {INSPECTED[a][1]}' for a, v in words if inside(v) and not v & 1 and INSPECTED.get(a, (None,))[0] == v]
        released += [f'raw j/jal at {a:#x} -> {t:#x}: {INSPECTED[a][1]}' for a, t in raw if inside(t) and INSPECTED.get(a, (None,))[0] == t]
        if released: row['inspected'] = released
        if why: rows.append(dict(row, usable=0, reason='; '.join(why[:4]) + (f' (+{len(why) - 4})' if len(why) > 4 else ''))); continue
        rows.append(dict(row, usable=size if size >= min_size else 0, reason='dead' if size >= min_size else f'dead but < {min_size} B'))
    return rows


def holes(rows):
    """Usable holes [(lo, hi, entry)] sorted by address."""
    return sorted((int(r['hole'][0], 16), int(r['hole'][1], 16), int(r['entry'], 16)) for r in rows if r['usable'])
