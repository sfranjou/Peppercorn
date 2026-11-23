"""Owned zero-interval tap improvement, with host policy/readback and interval set."""
NAME='tap_safe_c'
REQUIRES=('host_layer_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/tap/tap_pedal.c',)
C_ENTRIES=('home_tap_safe','tap_host_get','tap_host_set')
HOOKED=(0x27ed0,)
CODE={}
DATA={}
HOOKS={}
def patches(c):return [(0x27ed0,f'j {c.labels["home_tap_safe"]:#x}','owned zero-interval guard; shared host interval policy')]
