"""Compared window constructors; retains stock LVGL, device and storage services."""
NAME='ui_open_c'
REQUIRES=('legacy_ui_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
# Parent MOD055 theme immediate moves into the compared C browser body (0x56fb).
SUPERSEDED={0x1f6ce: 'browser border palette immediate retained by C constructor',
 **{a:'tuner MOD055 palette immediate retained by compared C constructor' for a in (0x269a0,0x26a68,0x26cf8,0x26d20,0x26dce)}}
C_HARD_FLOAT=True
# Restrict allocation to fs0..fs7; GCC's target register initialization overrides
# -ffixed-fs flags. Keeps this batch inside the established fs0..fs11 validator.
C_EXTRA_FLAGS=('-mconfig-fpu=0',)
C_SOURCES=('sdk/nds/ui_open/ui_tuner_open.c', 'sdk/nds/ui_open/ui_browser_open.c', 'sdk/nds/ui_open/ui_window1_open.c')
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(155998, 127534, 152262)
C_ENTRIES=tuple(f'nds_open_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_open_{a:05x}"]:#x}',f'compared window constructor {a:05x}')for a in HOOKED]
