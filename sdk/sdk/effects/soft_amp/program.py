"""Soft Amp: own coprocessor program for the AMP slot (PC 0x500 -> jump 0xb00). Pure data.

In place on the left window D[0x13..]: x = in * GAIN, clamped to [-1, 1], then the smooth cubic
y = x (1.5 - 0.5 x^2) (slope 1.5 at 0, flat at +-1), times LEVEL; then a tone shelf with the
biquad block (TONE cells). Bypassed: `jump 0xb00`, window untouched (stock AMP bypass).
Frame: sdk/copro/frame.py SLOTS[3]. Every word is an executed form.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro.asm import biquad_block

CELLS = dict(ENABLE=0x398, GAIN=0x399, ONE=0x39a, NONE=0x39b, C15=0x39c, C05=0x39d, LEVEL=0x39e, TONE=0x3a0)
NEXT_SLOT = 0xb00
ALLOWED_NON_X = []

SOURCE = [
    ('li', 5, CELLS['ENABLE']), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
    ('li', 0, 0x13), ('li', 1, 0x40),
    ('load', 2, CELLS['GAIN']), ('load', 3, CELLS['ONE']), ('load', 4, CELLS['NONE']),
    ('load', 5, CELLS['C15']), ('load', 6, CELLS['C05']), ('load', 7, CELLS['LEVEL']),
    'clip:',
    ('load_ind', 8, 0),
    ('fmul', 9, 8, 2),             # x = in * gain
    ('fsub', 10, 3, 9),            # 1 - x   negative when x > 1
    ('run_next_if_negative',),
    ('mov', 9, 3),
    ('fsub', 10, 9, 4),            # x + 1   negative when x < -1
    ('run_next_if_negative',),
    ('mov', 9, 4),
    ('fmul', 10, 9, 9),            # x^2
    ('fmul', 11, 10, 6),           # 0.5 x^2
    ('fsub', 12, 5, 11),           # 1.5 - 0.5 x^2
    ('fmul', 13, 9, 12),           # y
    ('fmul', 10, 13, 7),           # y * level
    ('store_inc', 0, 10),
    ('loop', 1, 'clip'),
    *biquad_block(0x13, CELLS['TONE'], 'tone'),
    ('jump', NEXT_SLOT),           # active exit
    'bypass:',
    ('jump', NEXT_SLOT),           # bypass exit
]
