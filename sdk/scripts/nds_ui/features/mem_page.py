"""MEM home page (MOD033, DRUM mode 3): up to three resident-lease entries from the cached
lease block ("MEM PRE18K", denied "PRE!D"). refresh2 routes every meter refresh: mode 3 here,
others to the home meter. Ported unchanged from scripts/build_nds_cpu_pct_code.py (MOD037)."""
from ..stock_api import API

NAME = 'mem_page'
REQUIRES = ('telemetry', 'home_meter')
ORACLES = ('sdk/telemetry/nds/model_lease.py',)
CASE_KINDS = ('refresh_mem',)


def section_refresh2(c):
    s = c.s
    # All accepted meter refresh call sites now enter here; mode 3 is the MEM page.
    s.label('refresh2'); s.address('a1', API.mod029_display_mode); s.emit('lwi a1,[a1 + 0]\nmovi a2,3\nbeq a1,a2,@mem_refresh\nj @refresh')


def section_mem_refresh(c):
    s = c.s
    c.begin('mem_refresh', 144); s.emit('mov55 s0,a0'); s.address('s1', c.STATE); s.emit(f'jal {API.irq_guard_enter:#x}'); s.address('a0', API.tick_counter); s.emit('lwi s2,[a0 + 0]\nlwi a0,[s1 + 88]\nbeqz a0,@mem_request\nlwi a0,[s1 + 84]\nsub a0,s2,a0\nslti ta,a0,500\nbnez ta,@mem_snapshot'); s.label('mem_request'); s.emit('swi s2,[s1 + 84]\nmovi a0,1\nswi a0,[s1 + 88]\nswi a0,[s1 + 0]'); s.label('mem_snapshot')
    for i in range(10): s.emit(f'lwi a0,[s1 + {96 + 4 * i}]\nswi a0,[sp + {40 + 4 * i}]')
    for i, off in enumerate([8, 12, 20]): s.emit(f'lwi a0,[s1 + {off}]\nswi a0,[sp + {80 + 4 * i}]')
    s.emit(f'jal {API.irq_guard_leave:#x}\nlwi a0,[sp + 80]\nbeqz a0,@mem_wait\nlwi a0,[sp + 84]\nbnez a0,@mem_error\nlwi a0,[sp + 88]\nsub a0,s2,a0\nslti ta,a0,1000\nbeqz ta,@mem_old\nlwi a0,[sp + 76]\nbeqz a0,@mem_wait\nlbi a0,[sp + 40]\nbeqz a0,@mem_none')
    # Build "MEM" + up to three " <ABR><kib>K" (granted) or " <ABR>!<reason>" (denied) entries.
    s.emit('addi s3,sp,92\nmovi a0,77\nsbi a0,[s3 + 0]\nmovi a0,69\nsbi a0,[s3 + 1]\nmovi a0,77\nsbi a0,[s3 + 2]\naddi s3,s3,3\nmovi s4,0\nmovi s5,0')
    s.label('mem_loop'); s.emit('slti ta,s4,11\nbeqz ta,@mem_tail\nslti ta,s5,3\nbeqz ta,@mem_tail\nslli a0,s4,1\nadd a0,sp,a0\nlbi s6,[a0 + 48]\nlbi s7,[a0 + 49]\nsrli a1,s6,4\nmovi a2,2\nbeq a1,a2,@mem_entry\nmovi a2,3\nbeq a1,a2,@mem_entry\nj @mem_next')
    s.label('mem_entry'); s.emit('movi a0,32\nsbi a0,[s3 + 0]\naddi s3,s3,1\nmovi a0,3\nmul a0,s4,a0'); c.addr('a2', 'abbr'); s.emit('add a2,a2,a0\nmovi a3,0')
    s.label('mem_abbr'); s.emit('slti ta,a3,3\nbeqz ta,@mem_abbr_done\nadd a0,a2,a3\nlbi a0,[a0 + 0]\nmovi a4,32\nbeq a0,a4,@mem_abbr_skip\nsbi a0,[s3 + 0]\naddi s3,s3,1'); s.label('mem_abbr_skip'); s.emit('addi a3,a3,1\nj @mem_abbr'); s.label('mem_abbr_done')
    s.emit('srli a1,s6,4\nmovi a2,3\nbeq a1,a2,@mem_denied\nmovi a2,100\ndivr a0,a1,s7,a2\nbeqz a0,@mem_tens\naddi a0,a0,48\nsbi a0,[s3 + 0]\naddi s3,s3,1\nmovi a2,10\ndivr a0,a1,a1,a2\naddi a0,a0,48\nsbi a0,[s3 + 0]\naddi s3,s3,1\nj @mem_units')
    s.label('mem_tens'); s.emit('movi a2,10\ndivr a0,a1,s7,a2\nbeqz a0,@mem_units\naddi a0,a0,48\nsbi a0,[s3 + 0]\naddi s3,s3,1')
    s.label('mem_units'); s.emit('movi a2,10\ndivr a0,a1,s7,a2\naddi a1,a1,48\nsbi a1,[s3 + 0]\nmovi a0,75\nsbi a0,[s3 + 1]\naddi s3,s3,2\nj @mem_counted')
    s.label('mem_denied'); s.emit('movi a0,33\nsbi a0,[s3 + 0]\nmovi a1,15\nand a1,s6,a1\nslti ta,a1,5\nbnez ta,@mem_reason_ok\nmovi a1,0'); s.label('mem_reason_ok'); c.addr('a2', 'reasons'); s.emit('add a2,a2,a1\nlbi a0,[a2 + 0]\nsbi a0,[s3 + 1]\naddi s3,s3,2')
    s.label('mem_counted'); s.emit('addi s5,s5,1'); s.label('mem_next'); s.emit('addi s4,s4,1\nj @mem_loop')
    s.label('mem_tail'); s.emit('bnez s5,@mem_end\nmovi a0,32\nsbi a0,[s3 + 0]\nmovi a0,48\nsbi a0,[s3 + 1]\nmovi a0,75\nsbi a0,[s3 + 2]\naddi s3,s3,3'); s.label('mem_end'); s.emit('movi a0,0\nsbi a0,[s3 + 0]\naddi a1,sp,92\nj @mem_draw')
    for state in ('wait', 'error', 'old', 'none'): s.label('mem_' + state); c.addr('a1', 'mem_' + state + '_text'); s.emit('j @mem_draw')
    s.label('mem_draw'); s.emit(f'lwi a0,[s0 + 0x34]\njal {API.mod026_set_text:#x}\nmovi a0,0'); c.end(144)


def data_strings(c):
    for key, text in [('mem_wait_text', 'MEM --'), ('mem_error_text', 'MEM ERR'), ('mem_old_text', 'MEM OLD'), ('mem_none_text', 'MEM NONE')]:
        c.data(key, text.encode() + b'\0')


def data_tables(c):
    # Group abbreviations (3 chars, space padded) and denial reason letters; not terminated.
    c.data('abbr', b'NR PREDSTAMPCABEQ MODDLYRVBNS AUX')
    c.data('reasons', b'?DFXI')


CODE = {'refresh2': section_refresh2, 'mem_refresh': section_mem_refresh}
DATA = {'strings': data_strings, 'tables': data_tables}


def patches(c):
    return []
