"""Wide: own EQ-slot program, complementary-tilt stereo widener. Pure data.

Mono in (D[0x13..]) -> both output windows by block copy, then one biquad in place on each:
left = high-shelf tilt (BQ_L cells), right = low-shelf tilt (BQ_R cells); designs from the ARM
(sdk/effects/wide/wide.c). Bypassed: stock EQ bypass (copy to both outputs). Biquad block:
sdk/copro/asm.py biquad_block (float32, products rounded then added - measured on hardware).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro.asm import biquad_block

CELLS = dict(ENABLE=0xf9c, BQ_L=0xfa1, BQ_R=0xfaa)     # 9 cells each: b0 b1 b2 a1 a2 x1 x2 y1 y2
ALLOWED_NON_X = []

SOURCE = [
    ('li', 5, CELLS['ENABLE']), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
    ('li', 9, 0x13), ('li', 10, 0x40), ('li', 11, 0x93), ('block', 'copy'),
    ('li', 9, 0x13), ('li', 10, 0x40), ('li', 11, 0xd3), ('block', 'copy'),
    *biquad_block(0x93, CELLS['BQ_L'], 'left'),
    *biquad_block(0xd3, CELLS['BQ_R'], 'right'),
    ('end',),
    'bypass:',
    ('li', 9, 0x13), ('li', 10, 0x40), ('li', 11, 0x93), ('block', 'copy'),
    ('li', 9, 0x13), ('li', 10, 0x40), ('li', 11, 0xd3), ('block', 'copy'),
    ('end',),
]
