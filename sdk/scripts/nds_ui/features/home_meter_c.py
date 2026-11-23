"""Home-page processing meter in C (sdk/nds/ui/home_meter.c): fourth C port, behaviour identical
to the asm `home_meter` (PROVIDES='home_meter', same refresh + format oracle cases). The C
functions keep the asm names `refresh` and `raw_text`, so the MEM-page router, the MOD029 call
sites (patches) and the harness are unchanged."""
from . import home_meter as asm_home
from ..stock_api import API

NAME = 'home_meter_c'
PROVIDES = 'home_meter'
CONFLICTS = ('home_meter', 'admission')
REQUIRES = ('telemetry',)
ORACLES = asm_home.ORACLES
CASE_KINDS = asm_home.CASE_KINDS
C_SOURCES = ('sdk/nds/ui/home_meter.c',)
C_ENTRIES = ('refresh', 'raw_text')
HOME_POLL_TICKS = 500


def c_headers(cfg=None, parent_b=None):
    state = int(cfg['segment']['state'], 16) if cfg else 0x2001f4a0
    return {'home_meter_table.h': f'#ifndef HOME_METER_TABLE_H\n#define HOME_METER_TABLE_H\n#define NDS_UI_STATE {state:#x}u\n#define HOME_POLL_TICKS {HOME_POLL_TICKS}\n#define HOME_RAW_FULL 262244u\n#endif\n'}


CODE = {}
DATA = {}
HOOKS = {}


def patches(c):
    return asm_home.patches(c)
