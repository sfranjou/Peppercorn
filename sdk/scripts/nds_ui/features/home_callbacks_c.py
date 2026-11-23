"""Compared home navigation, press/release and mode callbacks; preserves current theme."""
NAME='home_callbacks_c'
REQUIRES=('home_tick_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/home_callbacks/home_callbacks.c',)
C_HARD_FLOAT_SOURCES=C_SOURCES
SUPERSEDED={a:'MOD055 home press palette immediate retained by compared C' for a in (0x21bd6,0x21bf2,0x21c80)}
HOOKED=(136604, 136608, 136630, 136648, 136682, 136716, 136730, 136744, 140518, 136758, 138010, 138484, 138542, 138662, 138154)
C_ENTRIES=tuple(f'nds_hcb_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_hcb_{a:05x}"]:#x}',f'compared home callback {a:05x}')for a in HOOKED]
