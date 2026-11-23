"""Home value C body, double-helper/variadic-stack composition checked; candidate image proof required."""
NAME='home_value_c'
REQUIRES=('legacy_ui_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/home_value/home_value.c',)
HOOKED=(0x21ac2,)
C_ENTRIES=('nds_home_value_21ac2',)
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=C_SOURCES
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(0x21ac2,f'j {c.labels["nds_home_value_21ac2"]:#x}','compared home value body')]
