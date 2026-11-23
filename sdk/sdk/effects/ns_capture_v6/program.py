"""NS Capture v6 = v5 (stock VTSI SnapTones, GP5N, GP5P user programs; unchanged) + GPTC compact tone-capture records
(analysis/tone_capture/FIRMWARE_INTEGRATION_GUIDE.md, analysis/firmware/TONE_CAPTURE_INTEGRATION.md).

Program memory (one group-9 secondary blob, copied again by the stock loader on every reload, before init):
  0x500 ..        v5 program + one GMODE test (the v5 words themselves are unchanged apart from addresses)
  GPTC_PC ..      the exact compact kernel of sdk/effects/tone_compact_063/program.py, labels prefixed 'g_', cells moved
                  (below), its twiddles/spectra at the same PCs as 063 (TW 0xb58, SPEC 0xbf8)
  0x7ca ..        v5 modes: ARM init writes twiddles + spectra (VTSI / GP5N) or the GP5P user code here. That overwrites
                  the GPTC code, which is mode-exclusive: the next reload restores it before the next init (DSP reload
                  transaction, analysis/firmware/ARM_RELOAD_SCHEDULER_MODEL.md: pending 2 = load, then init).
Cells: ENABLE 0x398 shared; v5 cells as v5; GMODE 0x3e7 (unused by v5); the compact cells start at 0x3e8 in GPTC mode
(they overlap v5 data cells, which GPTC mode does not use; init writes the mode's own cells)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import importlib.util
from sdk.copro import asm

_spec = importlib.util.spec_from_file_location('ns_v5_program', Path(__file__).resolve().parents[1] / 'ns_capture_v5/program.py')
V5 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V5)
_spec = importlib.util.spec_from_file_location('tc063_program', Path(__file__).resolve().parents[1] / 'tone_compact_063/program.py')
TC = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(TC)

GMODE = 0x3e7
GPTC_BASE = 0x3e8
# Compact cells: same order and sizes as 063, ENABLE kept at the group flag cell, the rest from GPTC_BASE.
G = {'ENABLE': TC.C['ENABLE']}
_cursor = GPTC_BASE
for _name, _size in TC.SIZES.items():
    if _name == 'ENABLE': continue
    G[_name] = _cursor; _cursor += _size
GPTC_DATA_END = _cursor
assert GPTC_DATA_END <= 0xf9c and GMODE not in G.values()
# v5 control cells the dispatch reads must not be compact cells
assert all(not (V5.C[k] in G.values()) for k in ('UMODE', 'ENABLE') if k != 'ENABLE')
assert V5.C['UMODE'] < GPTC_BASE and GMODE not in V5.C.values()


def gptc_source():
    """063 kernel with this module's cell map, labels prefixed 'g_' (loop/jump/call targets)."""
    saved = dict(TC.C); TC.C.clear(); TC.C.update(G)
    try: src = TC.source(True)[0]
    finally: TC.C.clear(); TC.C.update(saved)
    labels = {x[:-1] for x in src if isinstance(x, str)}
    out = []
    for x in src:
        if isinstance(x, str): out.append('g_' + x); continue
        m, *o = x
        if m == 'loop' and isinstance(o[1], str): x = (m, o[0], 'g_' + o[1])
        elif m in ('jump', 'call') and isinstance(o[0], str): x = (m, 'g_' + o[0])
        out.append(x)
    used = {o for x in out if isinstance(x, tuple) and x[0] in ('loop', 'jump', 'call') for o in x[1:] if isinstance(o, str)}
    assert used <= {'g_' + l for l in labels}, used - {'g_' + l for l in labels}
    return out


# v5 head with one more test: GMODE bit 0 -> the compact kernel (after the user-mode test, before MODE).
_head = V5.SOURCE[:8]
assert _head[4:8] == [('load', 6, V5.C['UMODE']), ('skip_if_bit0', 6), ('jump', 'not_user'), ('jump', V5.USER_PC)]
SOURCE = [*_head, 'not_user:', ('load', 6, GMODE), ('skip_if_bit0', 6), ('jump', 'not_gptc'), ('jump', 'g_gptc'), 'not_gptc:',
          *V5.SOURCE[9:], 'g_gptc:', *gptc_source()]
assert V5.SOURCE[8] == 'not_user:'

CELLS = dict(V5.C, GMODE=GMODE, **{'G_' + k: v for k, v in G.items() if k != 'ENABLE'})
C = V5.C
PARTS_MAX = V5.PARTS_MAX
SPEC_PC, TW_PC, USER_PC = V5.SPEC_PC, V5.TW_PC, V5.USER_PC
GPTC_TW_PC, GPTC_SPEC_PC = TC.TW, TC.SPEC
_words = asm.assemble(SOURCE, 0x500)
_pc = 0x500
for _x in SOURCE[:SOURCE.index('g_gptc:')]:
    if not isinstance(_x, str): _pc += len(asm._encode(_x, None, _pc))   # word count only (labels not needed)
GPTC_PC = _pc
# USER_PC is an exit (jump into GP5P user code), never a target inside the GPTC kernel (frame.scan treats it as an exit).
assert not [x for x in SOURCE[SOURCE.index('g_gptc:'):] if isinstance(x, tuple) and x[0] in ('jump', 'loop', 'call') and x[-1] == USER_PC]
CODE_END = 0x500 + len(_words)
assert GPTC_PC <= USER_PC, 'v5 code (protected) must end below the region the ARM rewrites'
assert CODE_END <= GPTC_TW_PC, 'GPTC code must end below its twiddle table'
PROGRAM_DATA_PC = USER_PC            # lowest PC the ARM writes (v5 modes); GPTC writes from GPTC_TW_PC
MODE_CODE_PC = GPTC_PC               # code from here up is mode-exclusive (restored by the loader on every reload)
NEXT_SLOT = V5.NEXT_SLOT
ALLOWED_NON_X = []
ALLOW_CALLS = True
MODE_EXCLUSIVE_CELLS = True        # v5 cells and the G_ cells overlap: one map per record format
EXTERNAL_TARGETS = (USER_PC,)
