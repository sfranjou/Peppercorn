"""Compared word-channel widget geometry/text adapters; exact-image checks required."""
NAME='widget_adapters_c'
REQUIRES=()
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/widget_adapters/ui_widget_core.c','sdk/nds/widget_adapters/ui_widget_layout.c')
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(159758, 159770, 159822, 159874, 159892, 159916, 159934, 159956, 159996, 160036, 160376, 160814, 160906, 161320, 161332, 161392, 161438, 161460, 161482, 161498, 161520, 161560, 161586, 161610, 160388, 160434, 160480, 160502, 160524, 160564, 160586, 160770)
C_ENTRIES=tuple(f'nds_wa_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_wa_{a:05x}"]:#x}',f'compared widget adapter {a:05x}')for a in HOOKED]
