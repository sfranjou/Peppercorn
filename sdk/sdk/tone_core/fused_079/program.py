"""Current compact kernel with a full native IR512 tail, offline integration.

Same nonlinear stages, branch gating, decimator and tone controls as 063.
Separate module instance keeps the shipped 063 generator and ABI untouched.
The resident integration must load this program exclusively for GPTC mode.
"""
import importlib.util
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro import asm

path = Path(__file__).resolve().parents[2] / 'effects/tone_compact_063/program.py'
spec = importlib.util.spec_from_file_location('compact_fused_079_private', path)
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)
kernel.PARTS = 12
kernel.SPEC = kernel.EXIT - 130 * kernel.PARTS
kernel.TW = kernel.SPEC - 160
kernel.SIZES['FDL'] = 130 * kernel.PARTS
# 2026-11-08 (MOD145): fast FFT (bit-identical output) and the twiddle table in data cells (TW, appended after the
# existing cells so no other cell moves). Frees program words 0x748..0x7e7. analysis/tone_capture/FAST_FFT_081.md.
kernel.FAST_FFT = True
kernel.TW_IN_DATA = True
kernel.SIZES['TW'] = 160
# 2026-11-08 (next candidate, after MOD145): convolver fast_mac, bit-identical output, -1,152 steps/block.
kernel.FAST_MAC = True
# NL coefficients 1, 2 pre-negated by the ARM init; zero-size marker cell tells the C side (copro_cells.h).
kernel.NL_PRENEG = True
kernel.SIZES['NL_PRENEG'] = 0
# 2026-11-08 (after MOD146): run-time partition count. The ARM sets PARTS 4 / SPAN 520 without an IR (the null-IR
# fusion leaves partitions 4..11 exactly zero, so the output is unchanged except zero signs) and 12 / 1560 with one.
# Cells appended last so no other cell moves. analysis/tone_capture/TWO_CAPTURES_20261108.md.
kernel.RUNTIME_PARTS = True
kernel.SIZES['PARTS'] = 1
kernel.SIZES['SPAN'] = 1
# 2026-11-21 two-curve only: both slots run the GPTC v2 spline front. The GPTC v1
# nonlinearity, its coefficients, the parallel branch and the SPLINE flag go; KN (knots) and LPF are shared by both slots.
kernel.SPLINE_ONLY = True
for name in ('NL0', 'NL1', 'FLOOR', 'BRANCH_GAIN', 'PREV1', 'BRANCH_WINDOW', 'PARALLEL', 'NL_PRENEG'):
    kernel.SIZES.pop(name, None)
kernel.C.clear()
cursor = 0x398
for name, size in kernel.SIZES.items():
    kernel.C[name] = cursor
    cursor += size
assert cursor <= 0xf9c
# 2026-11-08 capture pair mode (analysis/tone_capture/TWO_CAPTURES_20261108.md). Two cells appended after SPAN:
# SPEC = program address of this capture's spectra (0x7e8, or PAIR_SPEC in pair mode), PAIR bit 0 = run the second
# capture first. The second capture is a private instance of the same 063 kernel with 4 static partitions; its body
# and NL subroutines sit after every single-capture instruction (all >= 0x7e8, overwritten by the 12-partition IR
# spectra, which is fine: PAIR is 0 then). It shares this capture's scratch (BUF, ACC, BRANCH_WINDOW, FFTC, the
# 256 new OS words), constants, twiddles and the FFT subroutine, and keeps its own state in the FDL words above 520
# (unused with 4 partitions) and the cells above DATA_END. The OS history (39 words) is swapped around its body.
kernel.SPEC_FROM_CELL = True
for name in ('SPEC', 'PAIR', 'MAIN_OFF'):
    kernel.SIZES[name] = 1; kernel.C[name] = cursor; cursor += 1
# Two-curve cells: KN 33 fixed knots (shared by both slots), AB 128 segment coefficients (per slot).
for name, size in (('KN', 33), ('AB', 128)):
    kernel.SIZES[name] = size; kernel.C[name] = cursor; cursor += size
MAIN_END = cursor
SHARED = ('ENABLE', 'ZERO', 'ONE', 'INV1024', 'THIRD', 'TWOTHIRD', 'CUTOFF_SQUARED', 'OS', 'BUF',
          'ACC', 'FFTC', 'TW', 'PARTS', 'SPAN', 'SPEC', 'PAIR', 'MAIN_OFF', 'KN', 'LPF')
_spec2 = importlib.util.spec_from_file_location('compact_pair_second_private', path)
second = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(second)
second.FAST_FFT = second.TW_IN_DATA = second.FAST_MAC = second.SPLINE_ONLY = True
second.PARTS = 4
P2_SIZES = {k: v for k, v in kernel.SIZES.items() if k not in SHARED}   # second slot: own AB, H1, PRE, SECOND ...
P2_SIZES['FDL'] = 4 * 130; P2_SIZES['OSH'] = 39; P2_SIZES['SAVE'] = 39
P2_REGIONS = [[kernel.C['FDL'] + 520, kernel.C['FDL'] + 1560], [MAIN_END, 0xf9c]]
P2 = {}
for name, size in sorted(P2_SIZES.items(), key=lambda kv: -kv[1]):       # first fit, largest first
    region = next(r for r in P2_REGIONS if r[1] - r[0] >= size)
    P2[name] = region[0]; region[0] += size
second.C.clear(); second.C.update({k: kernel.C[k] for k in SHARED}); second.C.update(P2)


def _renamed(items, prefix):
    defined = {i[:-1] for i in items if isinstance(i, str)}
    return [prefix + i if isinstance(i, str) else tuple(prefix + x if isinstance(x, str) and x in defined else x for x in i)
            for i in items]


def _copy(src, n, dst):
    return [('li', 9, src), ('li', 10, n), ('li', 11, dst), ('block', 'copy')]


def _pair_code(spec2):
    second.SPEC = spec2
    os_ = kernel.C['OS']
    code = ['pair_code:', *_copy(os_, 39, P2['SAVE']), *_copy(P2['OSH'], 39, os_), *second.body(False),
            *_copy(os_, 39, P2['OSH']), *_copy(P2['SAVE'], 39, os_), ('jump', 'pair_done'), *second.spline_sub()]
    return _renamed(code[:1], '') + _renamed(code[1:], 'p2_')


# MAIN_OFF bit 0 (pre-only mode: a DST capture with no main capture): after the second capture, exit without the main.
kernel.PRE_BODY = [('load', 6, kernel.C['PAIR']), ('skip_if_bit0', 6), ('jump', 'pair_done'), ('jump', 'pair_code'),
                   'pair_done:', ('load', 6, kernel.C['MAIN_OFF']), ('skip_if_bit0', 6), ('jump', 'main_on'),
                   ('jump', kernel.EXIT), 'main_on:']
kernel.CODE_LIMIT = kernel.EXIT - 2 * 520
kernel.EXTRA_SUBS = _pair_code(0)
_, _words = kernel.source(False)
PAIR_SPEC = kernel.BASE + len(_words)            # this capture's 4 spectra in pair mode, then the second's
P2_SPEC = PAIR_SPEC + 520
kernel.EXTRA_SUBS = _pair_code(P2_SPEC)
cursor = MAIN_END
CELLS = kernel.C
SOURCE, WORDS = kernel.source(False)
assert len(WORDS) == len(_words) and P2_SPEC + 520 <= kernel.EXIT
_tail = SOURCE[SOURCE.index('pair_code:'):]
SINGLE_END = kernel.BASE + len(WORDS) - len(asm.assemble(_tail + ['pair_done:', 'fft:'], 0))
assert SINGLE_END <= kernel.SPEC, 'single-capture code must stay below the 12-partition spectra'
# Generated header constants (copro_cells.h): second-capture cells and the pair program addresses.
CELLS = {**kernel.C, **{'P2_' + k: v for k, v in P2.items()}, 'PMADDR_PAIR_SPEC': PAIR_SPEC, 'PMADDR_P2_SPEC': P2_SPEC,
         'PMADDR_SINGLE_SPEC': kernel.SPEC}
BASE, EXIT, TW, SPEC, PARTS = kernel.BASE, kernel.EXIT, kernel.TW, kernel.SPEC, kernel.PARTS
SIZES, DATA_END = kernel.SIZES, max(r[0] for r in P2_REGIONS)
PROGRAM_DATA_PC = SPEC  # twiddles are data cells now; only the spectra live in program memory
ALLOW_CALLS = True
ALLOWED_NON_X = []
