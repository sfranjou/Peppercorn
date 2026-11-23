"""NS Capture v5 = v4 + USER PROGRAMS (GP5P records, analysis/firmware/USER_PROGRAMS.md): UMODE cell bit 0 -> jump to the
validated user code at USER_PC (it exits with `jump 0xe00`). Otherwise as v3/v4 (GP5N / VTSI). Pure data.

NS Capture v3 text:

MODE cell bit 0 (set by the ARM init from the record): 0 = GP5N chain (as v2: pre biquads, cubic clipper, post
biquads), 1 = VTSI chain written from scratch to the structure of the stock SnapTone (analysis/firmware/NS_SLOT.md,
reference scripts/tone_capture/vtsi_render.py): gain ramp -> biquad A -> 128-tap FIR (direct) -> x4 linear
interpolation -> exp-based asymmetric clipper -> own 40-tap Kaiser low-pass, keep 1 of 4 -> biquad B. Both continue in
a common tail: partitioned FFT convolution (PARTS cell: GP5N up to 11 partitions = 704 taps, VTSI 8 = FIR512) ->
Bass / Middle / Treble biquads -> VLEVEL. Frame: SLOTS[9], ALLOW_CALLS (FFT and clipper are one-level subroutines).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro.asm import biquad_block, fir_long_block
from sdk.copro import fft

PARTS_MAX = 11
CELLS = dict(ENABLE=0x398, DRIVE=0x399, BIAS=0x39a, ONE=0x39b, NONE=0x39c, C15=0x39d, C05=0x39e, LEVEL=0x39f, DC=0x3a0,
             STATE=0x3a1, ZERO=0x3a2, MODE=0x3a3, PARTS=0x3a4, SPAN=0x3a5, VLEVEL=0x3a6, UMODE=0x3a7,
             PRE_A=0x3a8, PRE_B=0x3b1, POST_A=0x3ba, POST_B=0x3c3, BASS=0x3cc, MID=0x3d5, TREBLE=0x3de,
             FFTC=0x3e8, HIST=0x3f0, ACC=0x430, BUF=0x4b8, FDL=0x5c0,
             # VTSI chain
             GCUR=0xb60, GTGT=0xb61, RAMPK=0xb62, PREV=0xb63, THIRD=0xb64, TWOTHIRD=0xb65, NEGP3=0xb66, P1=0xb67,
             NEGP2=0xb68, P4=0xb69, ZMIN=0xb6a, INV1024=0xb6b,
             BQA=0xb70, BQB=0xb79, T128=0xb90, H128=0xc10, LPF=0xcd0, OS=0xd00)
C = CELLS
assert C['FDL'] + PARTS_MAX * 130 <= C['GCUR']
assert C['H128'] + 128 + 63 <= C['LPF'] and C['LPF'] + 40 <= C['OS'] and C['OS'] + 39 + 256 <= 0xf9c
SPEC_PC = 0xe00 - PARTS_MAX * 130
TW_PC = SPEC_PC - 160
PROGRAM_DATA_PC = TW_PC
NEXT_SLOT = 0xe00
ALLOWED_NON_X = []
ALLOW_CALLS = True
USER_PC = TW_PC                      # user code region (FFT tables are unused in user mode)
EXTERNAL_TARGETS = (USER_PC,)
from sdk.copro import gp5p as _gp5p
assert USER_PC == _gp5p.USER_PC and C['UMODE'] < _gp5p.USER_LO

GP5N = [
    *biquad_block(0x13, C['PRE_A'], 'pre_a'),
    *biquad_block(0x13, C['PRE_B'], 'pre_b'),
    ('li', 0, 0x13), ('li', 1, 0x40),
    ('load', 2, C['DRIVE']), ('load', 3, C['ONE']), ('load', 4, C['NONE']),
    ('load', 5, C['C15']), ('load', 6, C['C05']), ('load', 7, C['LEVEL']),
    ('load', 11, C['BIAS']), ('load', 12, C['DC']),
    'clip:',
    ('load_ind', 8, 0),
    ('fmul', 10, 8, 2), ('fadd', 9, 10, 11),
    ('fsub', 10, 3, 9), ('run_next_if_negative',), ('mov', 9, 3),
    ('fsub', 10, 9, 4), ('run_next_if_negative',), ('mov', 9, 4),
    ('fmul', 10, 9, 9), ('fmul', 13, 10, 6), ('fsub', 10, 5, 13), ('fmul', 13, 9, 10),
    ('fsub', 9, 13, 12), ('fmul', 10, 9, 7),
    ('store_inc', 0, 10),
    ('loop', 1, 'clip'),
    *biquad_block(0x13, C['POST_A'], 'post_a'),
    *biquad_block(0x13, C['POST_B'], 'post_b'),
]

VTSI = [
    # gain ramp: cur += (tgt - cur) / 4410, then x *= cur (renderer: g_n = tgt + (g0 - tgt) r^(n+1))
    ('li', 0, 0x13), ('li', 1, 0x40), ('load', 2, C['GCUR']), ('load', 3, C['GTGT']), ('load', 4, C['RAMPK']),
    'gr:',
    ('fsub', 5, 3, 2), ('fmul', 6, 5, 4), ('fadd', 7, 2, 6), ('mov', 2, 7),
    ('load_ind', 8, 0), ('fmul', 9, 8, 2), ('store_inc', 0, 9),
    ('loop', 1, 'gr'),
    ('store', 2, C['GCUR']),
    *biquad_block(0x13, C['BQA'], 'bqa'),
    *fir_long_block(0x13, C['T128'], C['H128'], 128, 'f128'),
    # x4 interpolation + clipper into OS[39 + 4n + i]
    ('li', 0, 0x13), ('li', 1, 0x40), ('li', 2, C['OS'] + 39),
    'os:',
    ('load', 3, C['PREV']), ('load_inc', 4, 0), ('store', 4, C['PREV']),
    ('fsub', 5, 4, 3),                                   # d = x - prev
    ('mov', 8, 3), ('call', 'nlclip'), ('store_inc', 2, 9),                         # prev
    ('load', 6, C['THIRD']), ('fmul', 7, 5, 6), ('fadd', 8, 3, 7), ('call', 'nlclip'), ('store_inc', 2, 9),
    ('load', 6, C['TWOTHIRD']), ('fmul', 7, 5, 6), ('fadd', 8, 3, 7), ('call', 'nlclip'), ('store_inc', 2, 9),
    ('mov', 8, 4), ('call', 'nlclip'), ('store_inc', 2, 9),                         # x
    ('loop', 1, 'os'),
    # low-pass + decimation: window[n] = dot(reversed LPF taps, OS[4n + 3 .. 4n + 42])
    ('li', 0, 0x13), ('li', 1, 0x40), ('li', 2, C['OS'] + 3),
    'dec:',
    ('li', 8, C['LPF']), ('mov', 9, 2), ('li', 10, 40), ('block', 'dot'),
    ('store_inc', 0, 11), ('addi', 2, 4),
    ('loop', 1, 'dec'),
    ('li', 9, C['OS'] + 256), ('li', 10, 39), ('li', 11, C['OS']), ('block', 'copy'),   # keep 39 history points
    *biquad_block(0x13, C['BQB'], 'bqb'),
]

def tail(fast_mac=False):
    """Common tail; fast_mac=True (2026-11-08, used by ns_capture_v7 only) = convolver fast_mac with the run-time
    partition count, output identical except zero signs. The default keeps this program (and TAIL) unchanged."""
    return [
    *fft.convolver(0x13, C['BUF'], C['HIST'], C['FDL'], C['ACC'], C['STATE'], SPEC_PC, TW_PC, ('cells', C['PARTS'], C['SPAN']), C['ZERO'], 'conv', fft_label='fft', fast_mac=fast_mac),
    *biquad_block(0x13, C['BASS'], 'bass'),
    *biquad_block(0x13, C['MID'], 'mid'),
    *biquad_block(0x13, C['TREBLE'], 'treble'),
    ('li', 0, 0x13), ('li', 1, 0x40), ('load', 2, C['VLEVEL']),
    'lv:', ('load_ind', 3, 0), ('fmul', 4, 3, 2), ('store_inc', 0, 4), ('loop', 1, 'lv'),
    ]


TAIL = tail()

# Clipper subroutine: r8 = u -> r9 = A (1 - E(K u)), E(z) = (1 + max(z, -2047) / 1024)^1024 by ten squarings;
# u >= 0: A = p1, K = -p3; u < 0: A = -p2, K = p4. Uses r6, r7, r9..r13; keeps r0..r5, r8.
NLCLIP = [
    'nlclip:',
    ('load', 10, C['P1']), ('load', 11, C['NEGP3']), ('load', 12, C['ZERO']),
    ('load', 6, C['NEGP2']), ('load', 7, C['P4']),
    ('fsub', 13, 8, 12), ('run_next_if_negative',), ('mov', 10, 6),
    ('fsub', 13, 8, 12), ('run_next_if_negative',), ('mov', 11, 7),
    ('fmul', 9, 11, 8),                                  # z = K u
    ('load', 6, C['ZMIN']), ('fsub', 13, 9, 6), ('run_next_if_negative',), ('mov', 9, 6),
    ('load', 6, C['INV1024']), ('load', 7, C['ONE']),
    ('fmul', 13, 9, 6), ('fadd', 12, 7, 13),             # e = 1 + z / 1024
    ('fmul', 13, 12, 12), ('fmul', 12, 13, 13), ('fmul', 13, 12, 12), ('fmul', 12, 13, 13), ('fmul', 13, 12, 12),
    ('fmul', 12, 13, 13), ('fmul', 13, 12, 12), ('fmul', 12, 13, 13), ('fmul', 13, 12, 12), ('fmul', 12, 13, 13),
    ('fsub', 13, 7, 12), ('fmul', 9, 10, 13),            # A (1 - e)
    ('ret',),
]

SOURCE = [
    ('li', 5, C['ENABLE']), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
    ('load', 6, C['UMODE']), ('skip_if_bit0', 6), ('jump', 'not_user'), ('jump', USER_PC),
    'not_user:',
    ('load', 6, C['MODE']), ('skip_if_bit0', 6), ('jump', 'gp5n'),
    *VTSI, ('jump', 'tail'),
    'gp5n:', *GP5N,
    'tail:', *TAIL,
    ('jump', NEXT_SLOT),           # active exit
    'bypass:',
    ('jump', NEXT_SLOT),           # bypass exit
    *fft.fft128_subroutine(C['BUF'], TW_PC, 'fft', cells=C['FFTC']),
    *NLCLIP,
]
