"""FIR Lowpass: own DST-slot program, 32-tap FIR via the dot block word, then a level scale.
In place on D[0x13..]; stock DST frame (words 0..5, both exits `jump 0x500`). Pure data.
The dot word's accumulation order is unmeasured on hardware (see sdk/copro/asm.py fir_block)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from sdk.copro.asm import fir_block

N = 32
CELLS = dict(ENABLE=0x193, LEVEL=0x194, TAPS=0x1a0, HIST=0x1c0)       # hist: N + 63 cells up to 0x21e
NEXT_SLOT = 0x500
ALLOWED_NON_X = []

SOURCE = [
    ('li', 0, 0), ('store', 0, 0x10),                                  # stock DST words 0..1
    ('li', 5, CELLS['ENABLE']), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
    *fir_block(0x13, CELLS['TAPS'], CELLS['HIST'], N, 'fir'),
    ('load', 8, CELLS['LEVEL']), ('li', 9, 0x13), ('li', 10, 0x40), ('li', 11, 0x13), ('block', 'scale'),
    ('jump', NEXT_SLOT),
    'bypass:',
    ('jump', NEXT_SLOT),
]
