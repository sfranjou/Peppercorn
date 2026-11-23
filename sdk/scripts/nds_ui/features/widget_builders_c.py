"""Compared object/label/six-bar widget builders; exact image review required."""
NAME='widget_builders_c'
REQUIRES=()
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/widget_builders/widget_builders.c',)
C_HARD_FLOAT_SOURCES=C_SOURCES
SUPERSEDED={160654:'MOD055 widget palette retained by compared C'}
HOOKED=(160628, 160838, 161650, 161798)
C_ENTRIES=tuple(f'nds_wb_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_wb_{a:05x}"]:#x}',f'compared widget builder {a:05x}')for a in HOOKED]
