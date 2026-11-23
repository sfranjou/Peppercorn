"""Compared looper mode/tuner draw bodies; retained host behavior and theme."""
NAME='ui_render_c'
REQUIRES=('legacy_ui_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/ui_render/ui_looper_mode.c','sdk/nds/ui_render/ui_tuner_draw.c')
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(0x1fc78,0x25ab0)
C_ENTRIES=tuple(f'nds_render_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_render_{a:05x}"]:#x}',f'compared display rendering {a:05x}')for a in HOOKED]
