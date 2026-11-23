"""Compared stock home timer body below the retained legacy wrappers."""
NAME='home_tick_c'
REQUIRES=('legacy_ui_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/home_tick/home_tick.c',)
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=C_SOURCES
# The public entry retains the assignment/meter redirect; its original body is now dead.
HOOKED=(0x224f2,)
C_ENTRIES=('home_tick_body_c',)
CODE={}
DATA={}
HOOKS={}
def stock(cfg):
 """stock_in_place: the home tick body runs as stock (legacy_ui_c's tick stub replays its prologue)."""
 cfg=cfg or {}
 return NAME in cfg.get('stock_in_place_features',()) and 'ui_home_tick' in cfg.get('stock_in_place_by_feature',{}).get(NAME,())
def c_sources(cfg=None):return () if stock(cfg) else C_SOURCES
def c_entries(cfg=None):return () if stock(cfg) else C_ENTRIES
def patches(c):return []
