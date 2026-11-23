"""DST Capture (2026-11-08): DST-slot selector for a second GPTC capture. analysis/tone_capture/TWO_CAPTURES_20261108.md.

The audio of the selected capture runs inside the N->S capture program (the DST slot has 517 data words; a capture
needs ~1,400). This DST program only passes the window through. Its words 6..8 are a signature the N->S player reads
from program memory to know this effect is the loaded DST program (the stock loader rewrites the DST program on every
DST load, so the signature cannot go stale). The ARM half writes the enable cell and the slot number every block.
Words 0..5 and both exits are the stock DST frame word for word.
"""
CELLS = dict(ENABLE=0x193, SLOT=0x194)
NEXT_SLOT = 0x500
SIGNATURE = (0x4443, 0x5054)       # 'CD', 'TP' as two li immediates
ALLOWED_NON_X = []

SOURCE = [
    ('li', 0, 0),
    ('store', 0, 0x10),
    ('li', 5, CELLS['ENABLE']),
    ('load_ind', 6, 5),
    ('skip_if_bit0', 6),
    ('jump', 'bypass'),
    ('li', 13, SIGNATURE[0]),      # word 6: signature (harmless register write)
    ('li', 13, SIGNATURE[1]),      # word 7
    ('jump', NEXT_SLOT),           # word 8: active exit, window untouched
    'bypass:',
    ('jump', NEXT_SLOT),
]
