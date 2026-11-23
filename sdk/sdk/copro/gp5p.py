"""GP5P: user coprocessor programs loaded through the SnapTone upload path (analysis/firmware/USER_PROGRAMS.md).

Host side: `validate(words)` (the same rules as the pedal's C validator sdk/effects/ns_capture_v5/gp5p_validate.h —
kept equal by sdk/test_gp5p.py) and `pack(...)` (2,696-byte record). Offline only.

Rules (v1): every word one of the forms the SDK assembler emits (all executed on the pedal); jumps only forward, inside
the program or to the exit `jump 0xe00`; the last word an unconditional jump; loops backward, properly nested, never
entered from outside, counter set from an immediate 1..0x7fff and not written inside the loop; skips of one word only;
indirect / block pointers traced to an immediate in the user cells, the window or scratch (program-memory loads: inside
the user code); block counts immediate; direct addresses in those ranges; static step bound = sum of word costs times
enclosing loop counts (block words cost their element count) <= the budget.
"""
import struct, zlib

USER_PC = 0x7ca                      # NS Capture v5: user code runs here (program memory, above our code)
USER_LO, USER_HI = 0x3a8, 0xf9c      # user data cells (our control cells are 0x398..0x3a7)
WINDOW, SCRATCH = (0x13, 0x53), (0x113, 0x193)
EXIT = 0xe00
MAX_WORDS = (2696 - 128) // 4        # 642 code + data words
MAX_CODE = 512                       # code words (the pedal validator's cache)
BUDGET = 60000                        # steps/block (~0.36 DSP at the measured ~6e-6 per step)
FLAG_SKIP = (0x9f0a3c01, 0x9f083c01)
BLOCK_PTR8 = {3, 7, 0xd}             # block modes whose r8 is a pointer (add, mul, dot); 4 / 8 use r8 as a scalar
ERRORS = ['ok', 'size', 'form', 'target', 'loop', 'counter', 'pointer', 'address', 'count', 'bound', 'end', 'crc', 'magic']


class Reject(ValueError):
    def __init__(self, code, pc, why): super().__init__(f'{code} at word {pc}: {why}'); self.code = code; self.pc = pc


def region(v, n):
    if USER_LO <= v < USER_HI: return 'user'
    if WINDOW[0] <= v < WINDOW[1]: return 'win'
    if SCRATCH[0] <= v < SCRATCH[1]: return 'scr'
    if USER_PC <= v < USER_PC + n: return 'prog'
    return None


def decode(w):
    """(kind, fields) for a whitelisted word, else None. kinds: li, chi, clo, addi, subi, neg, ld, st, ldi, sti, pld,
    mov, brev, fmul, fmac, fadd, fsub, iadd, ishr, shl, fskip, bskip, gskip, loop, jump, block."""
    op, a, b, mode, imm = w >> 28, w >> 24 & 15, w >> 20 & 15, w >> 16 & 15, w & 0xffff; d = imm & 15
    gen = lambda *r: all(x <= 13 for x in r)
    if op == 7:
        if b == 0 and mode == 6 and imm <= 0x7fff and gen(a): return 'li', dict(r=a, v=imm)
        if b == 0xc and mode == 6 and gen(a): return 'chi', dict(r=a, v=imm)
        if b == 8 and mode == 6 and gen(a): return 'clo', dict(r=a, v=imm)
        if b == 0 and mode in (0, 2) and gen(a): return ('addi' if mode == 0 else 'subi'), dict(r=a, v=imm)
        if b == 0xc and mode == 0xc and imm == 0x8000 and gen(a): return 'neg', dict(r=a)
    if op == 5 and b == 0 and mode in (0, 8) and imm < 0x1000 and gen(a): return ('ld' if mode == 0 else 'st'), dict(r=a, addr=imm)
    if op == 0xe and imm == 0 and gen(a, b):
        if mode in (2, 3) and not (mode == 3 and a == b): return 'ldi', dict(d=a, p=b, inc=mode == 3)
        if mode in (4, 5) and not (mode == 5 and a == b): return 'sti', dict(p=a, s=b, inc=mode == 5)
        if mode in (6, 7) and not (mode == 7 and a == b): return 'pld', dict(d=a, p=b, inc=mode == 7)
    if op == 0xf and mode == 4 and imm == 0 and gen(a, b): return 'mov', dict(d=a, s=b)
    if op == 0xf and mode == 0xc and b == 0 and imm >> 8 == 0 and (imm >> 4) >> 1 in (4, 6, 7) and gen(a, d): return 'brev', dict(d=d, s=a)
    if op == 8 and imm >> 4 == 0 and mode in (6, 0xa) and gen(a, b, d) and d not in (a, b): return ('fmul' if mode == 6 else 'fmac'), dict(d=d, a=a, b=b)
    if op == 0xc and imm >> 4 == 0 and mode in (0xe, 0xf) and gen(a, b, d) and d not in (a, b): return ('fadd' if mode == 0xe else 'fsub'), dict(d=d, a=a, b=b)
    if op == 0xc and imm >> 4 == 0 and mode == 0 and gen(a, b, d): return 'iadd', dict(d=d, a=a, b=b)
    if op == 0xc and imm >> 4 == 0x400 and mode == 7 and gen(a, b, d): return 'ishr', dict(d=d, a=a, b=b)
    if op == 0xd and b == 0 and mode == 2 and imm >> 12 == 0 and (imm >> 4) >> 1 <= 8 and gen(a, d): return 'shl', dict(d=d, s=a)
    if op == 9:
        if w in FLAG_SKIP: return 'fskip', {}
        if b == 0 and mode == 8 and imm == 1 and gen(a): return 'bskip', dict(r=a)
        if mode == 2 and imm == 1 and gen(a, b): return 'gskip', dict(a=a, b=b)
    if op == 0xa and b == 0 and mode == 4 and imm < 0x1000 and gen(a): return 'loop', dict(r=a, t=imm)
    if op == 0xa and a == 0 and b == 0 and mode == 8 and imm < 0x1000: return 'jump', dict(t=imm)
    if op == 2 and a == 0 and b == 0 and imm == 0 and mode in (0, 3, 4, 7, 8, 0xd): return 'block', dict(m=mode)
    return None


def _writes(kind, f):
    """Registers a word writes, with True for writes that keep a pointer's region (increments)."""
    if kind in ('li', 'chi', 'clo', 'neg', 'ld', 'mov', 'brev', 'shl'): return {f.get('r', f.get('d')): False}
    if kind in ('addi', 'subi'): return {f['r']: True}
    if kind in ('ldi', 'pld'): return {f['d']: False, **({f['p']: True} if f['inc'] else {})}
    if kind == 'sti': return {f['p']: True} if f['inc'] else {}
    if kind in ('fmul', 'fmac', 'fadd', 'fsub', 'iadd', 'ishr'): return {f['d']: False}
    if kind == 'loop': return {f['r']: False}
    if kind == 'block': return {9: True, 10: False, 11: f['m'] != 0xd, **({8: True} if f['m'] in BLOCK_PTR8 else {})}
    return {}


def validate(words, budget=BUDGET):
    """Return the static step bound; raise Reject(code, word index, reason)."""
    n = len(words)
    if not 2 <= n <= MAX_CODE: raise Reject('size', 0, f'{n} code words (2..{MAX_CODE})')
    dec = [decode(w) for w in words]
    for i, x in enumerate(dec):
        if x is None: raise Reject('form', i, f'{words[i]:#010x} is not an allowed form')
        if x[0] == 'clo' and not (i and dec[i - 1][0] == 'chi' and dec[i - 1][1]['r'] == x[1]['r']): raise Reject('form', i, 'const low half without its high half')
        if x[0] == 'fskip' and not (i and dec[i - 1][0] == 'fsub'): raise Reject('form', i, 'flag skip not right after fsub')
    if dec[-1][0] != 'jump': raise Reject('end', n - 1, 'last word must be an unconditional jump')
    loops = []
    for i, (k, f) in enumerate(dec):
        if k == 'jump':
            t = f['t']
            if t != EXIT and not (USER_PC + i < t < USER_PC + n): raise Reject('target', i, f'jump {t:#x}: forward inside the program or to 0xe00 only')
        if k in ('fskip', 'bskip', 'gskip') and i + 2 > n - 1: raise Reject('target', i, 'skip past the end')
        if k == 'loop':
            t = f['t'] - USER_PC
            if not 0 <= t <= i: raise Reject('loop', i, 'loop target must be backward inside the program')
            if len(loops) == 24: raise Reject('loop', i, 'more than 24 loops')
            loops.append((t, i, f['r']))
    for a in loops:                               # proper nesting
        for b in loops:
            if a is not b and a[0] < b[0] <= a[1] < b[1]: raise Reject('loop', b[1], 'loops overlap')
    def inside(j): return [L for L in loops if L[0] < j <= L[1]]
    for i, (k, f) in enumerate(dec):              # no entry into a loop body from outside
        tg = f['t'] - USER_PC if k == 'jump' and f['t'] != EXIT else i + 2 if k in ('fskip', 'bskip', 'gskip') else None
        if tg is not None and any(not (L[0] <= i <= L[1]) for L in inside(tg)): raise Reject('target', i, 'jump/skip into a loop body')
    body_writes = {L: {} for L in loops}          # reg -> True if every write keeps its region
    for L in loops:
        for j in range(L[0], L[1]):
            for r, keep in _writes(*dec[j]).items(): body_writes[L][r] = body_writes[L].get(r, True) and keep
        if L[2] in body_writes[L]: raise Reject('counter', L[1], f'loop counter r{L[2]} written inside the loop')
    state = [None] * 14                            # None | ('imm', v) | ('ptr', region)
    counts = {}; jump_targets = {dec[i][1]['t'] - USER_PC for i in range(n) if dec[i][0] == 'jump' and dec[i][1]['t'] != EXIT}
    def ptr_ok(r, kinds=('user', 'win', 'scr')):
        s = state[r]
        if s is None or s[0] not in ('imm', 'ptr'): return False
        reg = s[1] if s[0] == 'ptr' else region(s[1], n)
        return reg in kinds
    skip_save = None
    for i, (k, f) in enumerate(dec):
        if i in jump_targets: state = [None] * 14
        for L in loops:
            if L[0] == i:
                s = state[L[2]]
                if not (s and s[0] == 'imm' and 1 <= s[1] <= 0x7fff): raise Reject('counter', L[1], f'loop counter r{L[2]} not an immediate 1..0x7fff at entry')
                counts[L] = s[1]
                for r, keep in body_writes[L].items():
                    s2 = state[r]
                    if keep and s2 and (s2[0] == 'ptr' or (s2[0] == 'imm' and region(s2[1], n))): state[r] = ('ptr', s2[1] if s2[0] == 'ptr' else region(s2[1], n))
                    else: state[r] = None
        if k in ('ld', 'st') and region(f['addr'], 0) not in ('user', 'win', 'scr'): raise Reject('address', i, f'direct address {f["addr"]:#x}')
        if k == 'ldi' and not ptr_ok(f['p']): raise Reject('pointer', i, f'r{f["p"]} not traced to user/window/scratch')
        if k == 'sti' and not ptr_ok(f['p']): raise Reject('pointer', i, f'r{f["p"]} not traced to user/window/scratch')
        if k == 'pld' and not ptr_ok(f['p'], ('prog',)): raise Reject('pointer', i, f'r{f["p"]} not traced to the user code')
        if k == 'block':
            if not (ptr_ok(9) and (f['m'] == 0xd or ptr_ok(11)) and (f['m'] not in BLOCK_PTR8 or ptr_ok(8))): raise Reject('pointer', i, 'block pointers')
            s = state[10]
            if not (s and s[0] == 'imm' and 1 <= s[1] <= 0x7fff): raise Reject('count', i, 'block count r10 not an immediate 1..0x7fff')
            f['elements'] = s[1]
        before = list(state)
        if k == 'li': state[f['r']] = ('imm', f['v'])
        elif k == 'chi': state[f['r']] = ('hi', f['v'])
        elif k == 'clo': state[f['r']] = ('imm', state[f['r']][1] << 16 | f['v']) if state[f['r']] and state[f['r']][0] == 'hi' else None
        else:
            for r, keep in _writes(k, f).items():
                s = state[r]
                if keep and s and (s[0] == 'ptr' or (s[0] == 'imm' and region(s[1], n))): state[r] = ('ptr', s[1] if s[0] == 'ptr' else region(s[1], n))
                else: state[r] = None
            if k == 'block': state[10] = ('imm', 0)
        if skip_save is not None:                 # merge over a one-word skip: registers the skipped word wrote are unknown
            state = [s if s == skip_save[r] else None for r, s in enumerate(state)]; skip_save = None
        if k in ('fskip', 'bskip', 'gskip'): skip_save = list(state)
        if k == 'jump': state = [None] * 14
    bound = 0
    for i, (k, f) in enumerate(dec):
        mult = 1
        for L in loops:
            if L[0] <= i <= L[1]: mult *= counts[L]
        bound += mult * (1 + (f.get('elements', 0) if k == 'block' else 0))
    if bound > budget: raise Reject('bound', 0, f'static step bound {bound} > budget {budget}')
    return bound


KINDS = {'off': 0, 'linear': 1, 'exp': 2, 'db': 3}


def pack(code, data=(), data_base=0x3b0, zero=0, knobs=(), name=''):
    """2,696-byte GP5P record. code: words assembled at USER_PC; data: initial words at cell data_base, then `zero` zeroed
    cells; knobs: up to five (cell, kind, min, max) mapped from the pedal's Gain/VOL/Bass/Middle/Treble (0..100)."""
    code, data = list(code), list(data)
    bound = validate(code)
    if len(code) + len(data) > MAX_WORDS: raise Reject('size', 0, 'code + data too long')
    if not (USER_LO <= data_base and data_base + len(data) + zero <= USER_HI): raise Reject('address', 0, 'data outside the user cells')
    knobs = list(knobs) + [(0, 'off', 0.0, 0.0)] * (5 - len(knobs))
    if len(knobs) != 5: raise ValueError('at most five knobs')
    for c, k, lo, hi in knobs:
        if k == 'exp' and (lo <= 0 or hi <= 0): raise ValueError('exp knob needs positive bounds')
    body = struct.pack(f'<{len(code)}I', *code) + struct.pack(f'<{len(data)}I', *data)
    import math
    # exp knobs carry log2(max / min) so the pedal needs no logarithm (value = min * 2^(k * that))
    kn = b''.join(struct.pack('<HHfff', (c - USER_LO) if KINDS[k] else 0, KINDS[k], lo, hi, math.log2(hi / lo) if k == 'exp' else 0.0) for c, k, lo, hi in knobs)
    for c, k, lo, hi in knobs:
        if KINDS[k] and not USER_LO <= c < USER_HI: raise Reject('address', 0, f'knob cell {c:#x}')
        if k == 'exp' and (lo <= 0 or hi <= 0): raise ValueError('exp knob needs positive bounds')
    hdr_tail = struct.pack('<HHHHII', len(code), len(data), data_base - USER_LO, zero, bound, 0) + kn + name.encode('ascii')[:15].ljust(16, b'\0')
    crc = zlib.crc32(body) & 0xffffffff                   # CRC-32 of the code + data words
    rec = b'GP5P' + struct.pack('<III', 1, 0, crc) + hdr_tail + body
    assert len(rec) == 128 + len(body)
    return rec + bytes(2696 - len(rec))
