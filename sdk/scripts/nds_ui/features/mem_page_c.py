"""MEM home page in C (sdk/nds/ui/mem_page.c): third C port, behaviour identical to the asm
`mem_page` (PROVIDES='mem_page', same refresh oracle cases). nds_refresh2 replaces the asm
router; home_meter's asm `refresh` is linked by name."""
from . import mem_page as asm_mem

NAME = 'mem_page_c'
PROVIDES = 'mem_page'
CONFLICTS = ('mem_page',)
REQUIRES = ('telemetry', 'home_meter')
ORACLES = asm_mem.ORACLES
CASE_KINDS = asm_mem.CASE_KINDS
C_SOURCES = ('sdk/nds/ui/mem_page.c',)
C_ENTRIES = ('nds_refresh2',)
LABEL_ALIASES = {'refresh2': 'nds_refresh2', 'mem_refresh': 'nds_mem_refresh'}
MEM_POLL_TICKS = 500


def c_headers(cfg=None, parent_b=None):
    state = int(cfg['segment']['state'], 16) if cfg else 0x2001f4a0
    return {'mem_page_table.h': f'#ifndef MEM_PAGE_TABLE_H\n#define MEM_PAGE_TABLE_H\n#define NDS_UI_STATE {state:#x}u\n#define MEM_POLL_TICKS {MEM_POLL_TICKS}\n#define MEM_WITH_REFUSAL {int(bool((cfg or {}).get("refusal_home")))}\n#endif\n'}


CODE = {}
DATA = {}
HOOKS = {}


def patches(c):
    return []
