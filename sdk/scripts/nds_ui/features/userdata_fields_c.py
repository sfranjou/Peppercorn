"""Compared UserData float boundaries and initialized field notifications."""
NAME='userdata_fields_c'
REQUIRES=('userdata_events_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/userdata_fields/userdata_fields.c',)
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(288014, 288032, 288070, 288094, 288120, 288142, 288164, 288186, 288212, 288238, 288266, 289764, 289772, 289818, 289850, 289858, 289866, 289912, 289954, 290600, 290608, 290992, 291000, 291262, 291800, 291866, 292384, 293546, 293554, 293562, 294556, 294682)
C_ENTRIES=tuple(f'nds_udf_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_udf_{a:05x}"]:#x}',f'compared UserData field/float {a:05x}')for a in HOOKED]
