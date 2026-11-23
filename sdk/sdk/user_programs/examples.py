"""Example GP5P user programs (analysis/firmware/USER_PROGRAMS.md): SDK assembler source at gp5p.USER_PC, data cells in
the user range, knob maps. `build(name)` -> (code words, data words, data_base, zero, knobs)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sdk.copro import asm, gp5p
from sdk.copro.asm import biquad_block, fbits

D = 0x3b0                                    # data base: D+0 gain, D+1.. constants, D+16 biquad (9 cells)
GAIN = [('li', 0, 0x13), ('li', 1, 64), ('load', 2, D),
        'g:', ('load_ind', 3, 0), ('fmul', 4, 3, 2), ('store_inc', 0, 4), ('loop', 1, 'g')]

PROGRAMS = {
    # Volume: Gain knob -> D[0x3b0], -24..+12 dB.
    'gain': dict(src=GAIN + [('jump', 0xe00)], data=[fbits(1.0)], zero=0, knobs=[(D, 'db', -24.0, 12.0)]),
    # Low-pass biquad (coefficients as data, fixed 2 kHz) + gain.
    'lowpass': dict(src=[*biquad_block(0x13, D + 16, 'bq'), *GAIN, ('jump', 0xe00)], zero=4,
                    data=None, knobs=[(D, 'db', -24.0, 12.0)]),
    # Cubic soft clip with drive (Gain knob, x1..x30) and level (VOL knob).
    'softclip': dict(src=[('li', 0, 0x13), ('li', 1, 64), ('load', 2, D), ('load', 3, D + 1), ('load', 4, D + 2),
                          ('load', 5, D + 3), ('load', 6, D + 4), ('load', 7, D + 5),
                          'c:', ('load_ind', 8, 0), ('fmul', 9, 8, 2),
                          ('fsub', 10, 3, 9), ('run_next_if_negative',), ('mov', 9, 3),
                          ('fsub', 10, 9, 4), ('run_next_if_negative',), ('mov', 9, 4),
                          ('fmul', 10, 9, 9), ('fmul', 11, 10, 6), ('fsub', 12, 5, 11), ('fmul', 13, 9, 12), ('fmul', 10, 13, 7),
                          ('store_inc', 0, 10), ('loop', 1, 'c'), ('jump', 0xe00)],
                     data=[fbits(4.0), fbits(1.0), fbits(-1.0), fbits(1.5), fbits(0.5), fbits(0.5)], zero=0,
                     knobs=[(D, 'exp', 1.0, 30.0), (D + 5, 'db', -30.0, 6.0)]),
}


def lowpass_data(f=2000.0):
    import math
    w = 2 * math.pi * f / 44100; a = math.sin(w) / (2 * 0.7071); c = math.cos(w); a0 = 1 + a
    co = [(1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0, -2 * c / a0, (1 - a) / a0]
    return [fbits(1.0)] + [0] * 15 + [fbits(x) for x in co]


def build(name):
    p = PROGRAMS[name]
    code = asm.assemble(p['src'], gp5p.USER_PC)
    data = lowpass_data() if name == 'lowpass' else p['data']
    return code, data, D, p['zero'], p['knobs']
