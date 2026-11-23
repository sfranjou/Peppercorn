"""NS Capture v2 (13 partitions = 832 taps, compact FFT): own N->S program (PC 0x500 -> jump 0xe00) with a long post filter. Pure data.

In place on D[0x13..0x52]: pre biquads A, B -> asymmetric cubic clipper (DRIVE, BIAS, DC, LEVEL) -> post biquads
A, B -> partitioned FFT convolution (up to PARTS * 64 taps, sdk/copro/fft.py; FFT as a one-level subroutine) ->
Bass / Middle / Treble. Bypassed: `jump 0xe00`, window untouched. Program memory above the code holds the
twiddle table (TW_PC) and the filter spectra (SPEC_PC), both written by the ARM init (ns_capture.c).
Frame: sdk/copro/frame.py SLOTS[9] with ALLOW_CALLS. Every word is an executed form.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro.asm import biquad_block
from sdk.copro import fft

PARTS = 13
CELLS = dict(ENABLE=0x398, DRIVE=0x399, BIAS=0x39a, ONE=0x39b, NONE=0x39c, C15=0x39d, C05=0x39e, LEVEL=0x39f, DC=0x3a0,
             STATE=0x3a1, ZERO=0x3a2,
             PRE_A=0x3a8, PRE_B=0x3b1, POST_A=0x3ba, POST_B=0x3c3, BASS=0x3cc, MID=0x3d5, TREBLE=0x3de,
             FFTC=0x3e8, HIST=0x3f0, ACC=0x430, BUF=0x4b8, FDL=0x5c0)   # FFTC: 6 compact-FFT stage cells
assert CELLS['HIST'] + 64 <= CELLS['ACC'] and CELLS['ACC'] + 130 <= CELLS['BUF'] and CELLS['BUF'] + 256 <= CELLS['FDL']
assert CELLS['FDL'] + PARTS * 130 <= 0xf9c
SPEC_PC = 0xe00 - PARTS * 130
TW_PC = SPEC_PC - 160
PROGRAM_DATA_PC = TW_PC
NEXT_SLOT = 0xe00
ALLOWED_NON_X = []
ALLOW_CALLS = True
C = CELLS

SOURCE = [
    ('li', 5, C['ENABLE']), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
    *biquad_block(0x13, C['PRE_A'], 'pre_a'),
    *biquad_block(0x13, C['PRE_B'], 'pre_b'),
    ('li', 0, 0x13), ('li', 1, 0x40),
    ('load', 2, C['DRIVE']), ('load', 3, C['ONE']), ('load', 4, C['NONE']),
    ('load', 5, C['C15']), ('load', 6, C['C05']), ('load', 7, C['LEVEL']),
    ('load', 11, C['BIAS']), ('load', 12, C['DC']),
    'clip:',
    ('load_ind', 8, 0),
    ('fmul', 10, 8, 2), ('fadd', 9, 10, 11),        # x = in * drive + bias
    ('fsub', 10, 3, 9), ('run_next_if_negative',), ('mov', 9, 3),
    ('fsub', 10, 9, 4), ('run_next_if_negative',), ('mov', 9, 4),
    ('fmul', 10, 9, 9), ('fmul', 13, 10, 6), ('fsub', 10, 5, 13), ('fmul', 13, 9, 10),   # y = x (1.5 - 0.5 x^2)
    ('fsub', 9, 13, 12), ('fmul', 10, 9, 7),         # (y - dc) * level
    ('store_inc', 0, 10),
    ('loop', 1, 'clip'),
    *biquad_block(0x13, C['POST_A'], 'post_a'),
    *biquad_block(0x13, C['POST_B'], 'post_b'),
    *fft.convolver(0x13, C['BUF'], C['HIST'], C['FDL'], C['ACC'], C['STATE'], SPEC_PC, TW_PC, PARTS, C['ZERO'], 'conv', fft_label='fft'),
    *biquad_block(0x13, C['BASS'], 'bass'),
    *biquad_block(0x13, C['MID'], 'mid'),
    *biquad_block(0x13, C['TREBLE'], 'treble'),
    ('jump', NEXT_SLOT),           # active exit
    'bypass:',
    ('jump', NEXT_SLOT),           # bypass exit
    *fft.fft128_subroutine(C['BUF'], TW_PC, 'fft', cells=C['FFTC']),
]
