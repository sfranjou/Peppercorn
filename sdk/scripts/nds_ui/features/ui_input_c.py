"""Main-processor UI input in C (item 9 step 3, analysis/firmware/NDS_UI_INPUT.md, MOD053): knob nudge 0x4772c,
footswitch toggle 0x4586a, the effect-edit window 4 knob/encoder callbacks 0x1c376/0x1be7e and the encoder/key scan
(0x157c4, 0x157fc, 0x15bc2, 0x15cfc, 0x17e8a) run the readable sources compared with the original instructions
(firmware/reconstructed/nds/ui_knob.c, ui_footswitch.c, ui_effect_set.c, input_scan.c) through pedal builds in
sdk/nds/ui_input/ (direct loads/stores and stock calls). Each stock entry becomes `j nds_ui_XXXXX`; calls leaving the
modules go to the stock addresses, so other features' hooks there still apply. Stays stock: footswitch press 0x47452
(admission hook site 0x47456 inside). Proof: scripts/verify_nds_generic_image.py reruns the four studies on the built b."""
from ..stock_api import API

NAME = 'ui_input_c'
REQUIRES = ()
CONFLICTS = ()
ORACLES = ()
CASE_KINDS = ()
C_SOURCES = ('sdk/nds/ui_input/ui_knob.c', 'sdk/nds/ui_input/ui_footswitch.c', 'sdk/nds/ui_input/ui_effect_set.c', 'sdk/nds/ui_input/input_scan.c')
C_HARD_FLOAT = True   # knob_nudge computes in float (stock fs0 convention for the parameter getters/setter)
C_HARD_FLOAT_SOURCES = ('sdk/nds/ui_input/ui_knob.c',)   # the others are integer-only: soft-float (hard-float GCC spills integers to FPU registers)
HOOKED = tuple(int(e['address'], 16) for n, e in API.entries().items() if n.startswith('hook_ui_'))
C_ENTRIES = tuple(f'nds_ui_{a:05x}' for a in HOOKED)
CODE = {}
DATA = {}
HOOKS = {}


def patches(c):
    return [(a, f'j {c.labels[f"nds_ui_{a:05x}"]:#x}', f'stock entry {a:#x} -> C nds_ui_{a:05x}') for a in HOOKED]
