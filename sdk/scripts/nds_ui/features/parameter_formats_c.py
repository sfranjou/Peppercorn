"""Compared parameter text adapters and conditional formats, explicit incoming fs0 adapters; image proof required."""
NAME='parameter_formats_c'
REQUIRES=('catalog_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/parameter_formats/parameter_format_adapters.c','sdk/nds/parameter_formats/parameter_format_branches.c')
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(102448, 102464, 102480, 102534, 102588, 102604, 102620, 102636, 102652, 102668, 102720, 102752, 102768, 102784, 102800, 102816, 102870, 102886, 102902, 102958, 103014, 103030, 103046, 103062, 103078, 103094, 103110, 103126, 103142, 103158, 103174, 103190, 103206, 103222, 103238, 103254, 103270, 103286, 103302, 103318, 103334, 103350, 103402, 103434, 103466, 103482, 103538, 103618, 103634, 103650, 103666, 103682, 103698, 103714, 103766, 103782, 103830, 103846, 103862, 103878, 103894, 103948, 103964, 103992, 104034, 104038)
C_ENTRIES=tuple(f'nds_pfmt_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_pfmt_{a:05x}"]:#x}',f'compared parameter text table {a:05x}')for a in HOOKED]
