"""Compared integer-channel settings, preset-order and expression control."""
NAME='data_control_c'
REQUIRES=()
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/data_control/data_settings.c','sdk/nds/data_control/data_expression.c')
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(277854, 277870, 277886, 277898, 278070, 278096, 278112, 278352, 286364, 281106, 285718, 285824, 286042, 286180)
C_ENTRIES=tuple(f'nds_dc_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_dc_{a:05x}"]:#x}',f'compared Data control {a:05x}')for a in HOOKED]
