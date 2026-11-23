"""Home-page processing meter (MOD029 page, regenerated on the shared extended cache): ARM/DSP
text on the DRUM modes 1/2, ~2 Hz coalesced request. The ARM text itself is replaced by the
admission module through the 'home_arm_text' hook (CPU NN%); without it the raw ARM~x.xx text
is shown. Ported unchanged from scripts/build_nds_cpu_pct_code.py (MOD037)."""
from ..stock_api import API

NAME = 'home_meter'
REQUIRES = ('telemetry',)
ORACLES = ('sdk/telemetry/nds/model.py', 'sdk/telemetry/nds/model_gr.py')
CASE_KINDS = ('refresh_home', 'formats')
STATES = [('wait', '--'), ('error', 'ERR'), ('old', 'OLD'), ('hold', 'HOLD'), ('idle', 'IDLE')]


def section_refresh(c):
    s = c.s; STATE = c.STATE
    # New UI uses shared extended cache, only modeon coalesced request500rawticks.
    c.begin('refresh', 112); s.emit('mov55 s0,a0\nmovi s8,0'); s.address('a0', API.mod029_display_mode); s.emit('lwi s3,[a0 + 0]\nbeqz s3,@refresh_end'); s.address('s1', STATE); s.emit(f'jal {API.irq_guard_enter:#x}'); s.address('a0', API.tick_counter); s.emit('lwi s2,[a0 + 0]\nlwi a0,[s1 + 88]\nbeqz a0,@ui_request\nlwi a0,[s1 + 84]\nsub a0,s2,a0\nslti ta,a0,500\nbnez ta,@ui_snapshot'); s.label('ui_request'); s.emit('swi s2,[s1 + 84]\nmovi a0,1\nswi a0,[s1 + 88]\nswi a0,[s1 + 0]'); s.label('ui_snapshot')
    offs = [8, 12, 20, 36, 40, 48, 68]
    for off in offs: s.emit(f'lwi a0,[s1 + {off}]\nswi a0,[sp + {40 + offs.index(off) * 4}]')
    s.emit(f'jal {API.irq_guard_leave:#x}\nlwi a0,[sp + 40]\nbeqz a0,@ui_wait\nlwi a0,[sp + 44]\nbnez a0,@ui_error\nlwi a0,[sp + 48]\nsub a0,s2,a0\nslti ta,a0,1000\nbeqz ta,@ui_old\nlwi a0,[sp + 64]\nbnez a0,@ui_hold\nlwi a0,[sp + 52]\nmovi a1,1\nand a2,a0,a1\nbeqz a2,@ui_wait\nbeq s3,a1,@ui_arm\nmovi a1,4\nand a0,a0,a1\nbeqz a0,@ui_idle\nlwi a1,[sp + 60]\nj @ui_format'); s.label('ui_arm'); s.emit('movi a1,1\nand a0,a0,a1\nbeqz a0,@ui_wait\nlwi a1,[sp + 56]\nmov55 s7,a1\nmovi s8,1'); s.label('ui_format'); s.emit('mov55 a0,s3\naddi a2,sp,80\njal @raw_text\naddi a1,sp,80\nj @ui_draw')
    for state, word in STATES:
        s.label('ui_' + state); s.emit('movi a0,1\nbeq s3,a0,@ui_' + state + '_arm'); c.addr('a1', 'dsp_' + state); s.emit('j @ui_draw'); s.label('ui_' + state + '_arm'); c.addr('a1', 'arm_' + state); s.emit('j @ui_draw')
    s.label('ui_draw')
    # Hook contract: a1 = text, s3 = mode, s4..s8 free (s7 = ARM last raw, s8 = 1 if fresh ARM
    # sample), sp+80.. 32 B text buffer; must fall through to ui_set with a1 = text.
    c.hook('home_arm_text')
    s.label('ui_set'); s.emit(f'lwi a0,[s0 + 0x34]\njal {API.mod026_set_text:#x}'); s.label('refresh_end'); s.emit('movi a0,0'); c.end(112)


def section_raw_text(c):
    s = c.s
    # Exact integer truncation raw*100/262244 without overflow: quotient and remainder.
    s.label('raw_text'); s.emit('mov55 a5,a2\nmovi a3,1\nbeq a0,a3,@raw_arm'); c.addr('a0', 'dsp_prefix'); s.emit('j @raw_prefix'); s.label('raw_arm'); c.addr('a0', 'arm_prefix'); s.label('raw_prefix')
    for i in range(4): s.emit(f'lbi a3,[a0 + {i}]\nsbi a3,[a5 + {i}]')
    s.address('a3', 262244); s.emit('divr a0,a2,a1,a3\nslti ta,a0,10\nbeqz ta,@raw_high\nmovi a1,100\nmul a2,a2,a1\ndivr a1,a2,a2,a3\naddi a0,a0,48\nsbi a0,[a5 + 4]\nmovi a0,46\nsbi a0,[a5 + 5]\nmovi a0,10\ndivr a0,a2,a1,a0\naddi a0,a0,48\nsbi a0,[a5 + 6]\naddi a2,a2,48\nsbi a2,[a5 + 7]\nmovi a0,0\nsbi a0,[a5 + 8]\nret5 lp'); s.label('raw_high')
    for i, ch in enumerate('HIGH'): s.emit(f'movi a0,{ord(ch)}\nsbi a0,[a5 + {4 + i}]')
    s.emit('movi a0,0\nsbi a0,[a5 + 8]\nret5 lp')


def data_strings(c):
    for key, word in STATES + [('prefix', '~')]:
        for mode in ['arm', 'dsp']:
            c.data(mode + '_' + key, (mode.upper() + ('' if key == 'prefix' else ' ') + word).encode() + b'\0')


CODE = {'refresh': section_refresh, 'raw_text': section_raw_text}
DATA = {'strings': data_strings}


def patches(c):
    # Every MOD029 meter-refresh call (home tick, DRUM handler, MOD026 title restore) enters
    # the current cache: refresh2 when the MEM page router is present, else refresh.
    if 'legacy_ui_c' in c.enabled: return []   # MOD055+: the call sites are C (legacy_ui_c calls nds_refresh2 directly)
    target = c.labels.get('refresh2', c.labels['refresh'])
    return [(site, f'jal {target:#x}', 'MOD029 meter refresh call to regenerated meter') for site in API.mod029_meter_refresh_calls]
