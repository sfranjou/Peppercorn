"""Compared window manager and common GUI routines; exact image review required."""
NAME='window_common_c'
REQUIRES=()
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/window_common/window_common.c',)
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(95608, 95704, 95794, 95904, 95910, 95988, 96066, 96072, 96134, 96158, 96170, 96246, 96322, 161968, 162028, 162088, 162128, 162152, 162532)
C_ENTRIES=tuple(f'nds_wc_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_wc_{a:05x}"]:#x}',f'compared window/common {a:05x}')for a in HOOKED]
