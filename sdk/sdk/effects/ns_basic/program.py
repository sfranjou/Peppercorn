"""NS Basic: own coprocessor program for the N->S slot (PC 0x500 -> jump 0xe00). Pure data.

In place on the left window D[0x13..]: two pre biquads, asymmetric cubic soft clipper
(x = in * DRIVE + BIAS, clamped to [-1, 1], y = x (1.5 - 0.5 x^2) - DC, times LEVEL), two post
biquads, a 128-tap FIR, then the Bass / Middle / Treble tone stack. Bypassed: `jump 0xe00`, window
untouched. Coefficients come from the slot's GP5N content record (ns_basic.c, ns_record.py).
Frame: sdk/copro/frame.py SLOTS[9]. Every word is an executed form.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro.asm import biquad_block, fir_long_block

FIR_TAPS = 128
CELLS = dict(ENABLE=0x398, DRIVE=0x399, BIAS=0x39a, ONE=0x39b, NONE=0x39c, C15=0x39d, C05=0x39e, LEVEL=0x39f, DC=0x3a0,
             PRE_A=0x3a8, PRE_B=0x3b1, POST_A=0x3ba, POST_B=0x3c3, BASS=0x3cc, MID=0x3d5, TREBLE=0x3de,
             TAPS=0x400, HIST=0x480)
assert CELLS['TAPS'] + FIR_TAPS <= CELLS['HIST'] and CELLS['HIST'] + FIR_TAPS + 63 <= 0xf9c
NEXT_SLOT = 0xe00
ALLOWED_NON_X = []

SOURCE = [
    ('li', 5, CELLS['ENABLE']), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
    *biquad_block(0x13, CELLS['PRE_A'], 'pre_a'),
    *biquad_block(0x13, CELLS['PRE_B'], 'pre_b'),
    ('li', 0, 0x13), ('li', 1, 0x40),
    ('load', 2, CELLS['DRIVE']), ('load', 3, CELLS['ONE']), ('load', 4, CELLS['NONE']),
    ('load', 5, CELLS['C15']), ('load', 6, CELLS['C05']), ('load', 7, CELLS['LEVEL']),
    ('load', 11, CELLS['BIAS']), ('load', 12, CELLS['DC']),
    'clip:',
    ('load_ind', 8, 0),
    ('fmul', 10, 8, 2),            # in * drive
    ('fadd', 9, 10, 11),           # x = in * drive + bias
    ('fsub', 10, 3, 9),            # 1 - x   negative when x > 1
    ('run_next_if_negative',),
    ('mov', 9, 3),
    ('fsub', 10, 9, 4),            # x + 1   negative when x < -1
    ('run_next_if_negative',),
    ('mov', 9, 4),
    ('fmul', 10, 9, 9),            # x^2
    ('fmul', 13, 10, 6),           # 0.5 x^2
    ('fsub', 10, 5, 13),           # 1.5 - 0.5 x^2
    ('fmul', 13, 9, 10),           # y
    ('fsub', 9, 13, 12),           # y - dc (dc = clipper output at the bias point)
    ('fmul', 10, 9, 7),            # * level
    ('store_inc', 0, 10),
    ('loop', 1, 'clip'),
    *biquad_block(0x13, CELLS['POST_A'], 'post_a'),
    *biquad_block(0x13, CELLS['POST_B'], 'post_b'),
    *fir_long_block(0x13, CELLS['TAPS'], CELLS['HIST'], FIR_TAPS, 'fir'),
    *biquad_block(0x13, CELLS['BASS'], 'bass'),
    *biquad_block(0x13, CELLS['MID'], 'mid'),
    *biquad_block(0x13, CELLS['TREBLE'], 'treble'),
    ('jump', NEXT_SLOT),           # active exit
    'bypass:',
    ('jump', NEXT_SLOT),           # bypass exit
]
