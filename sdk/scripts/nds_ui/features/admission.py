"""Admission warning / CPU % (MOD036, MOD037): predicted ARM load of the live
chain from the stock mData enable mask and effect ids (cost table admission_costs.py).
Home ARM page: one safe-side number "CPU NN%" = max(measured, estimate), '!' at WARN_PCT,
'?' when an id is unknown. Edit pages other than GR Comp: "CPU HIGH NN%" strip at WARN_PCT.
Fills the home_meter 'home_arm_text' and gr_meter 'edit_strip' hooks. Ported unchanged from
scripts/build_nds_cpu_pct_code.py (MOD037). Design: analysis/firmware/ADMISSION.md."""
import struct
from ..stock_api import API
from sdk.telemetry.nds import admission_costs as AC

NAME = 'admission'
REQUIRES = ('home_meter', 'gr_meter')
ORACLES = ('sdk/telemetry/nds/model_admission.py', 'sdk/telemetry/nds/model_cpu_pct.py', 'sdk/telemetry/nds/admission_costs.py')
DATA_INPUTS = AC.DATA_INPUTS
CASE_KINDS = ('refresh_cpu', 'editor_warn')
WARN_PCT = 95
ARM_RAW_FULL = 262244   # raw ARM proxy for ratio 1.0 (analysis/firmware/ADMISSION.md)


def hook_home_arm_text(c):
    s = c.s
    s.emit(f'movi a0,1\nbne s3,a0,@ui_set\njal @est_compute\nmov55 s6,a1\naddi a0,a0,9\nmovi a3,10\ndivr s4,a5,a0,a3\nbeqz s8,@cpu_text'); s.address('a3', ARM_RAW_FULL)
    s.emit('divr a0,a1,s7,a3\nslti ta,a0,10\nbeqz ta,@meas_big\nmovi a2,100\nmul a4,a1,a2\nadd a4,a4,a3\naddi a4,a4,-1\ndivr a5,a1,a4,a3\nmovi a2,100\nmul a0,a0,a2\nadd a0,a0,a5\nslti ta,a0,1000\nbnez ta,@meas_cmp'); s.label('meas_big'); s.emit('movi a0,999'); s.label('meas_cmp'); s.emit('slt ta,s4,a0\nbeqz ta,@cpu_text\nmov55 s4,a0')
    s.label('cpu_text'); s.emit('addi a2,sp,80')
    for i, ch in enumerate('CPU '): s.emit(f'movi a0,{ord(ch)}\nsbi a0,[a2 + {i}]')
    s.emit(f'addi a2,a2,4\nmov55 a0,s4\njal @fmt_pct\nmovi a0,37\nsbi a0,[a2 + 0]\naddi a2,a2,1\nslti ta,s4,{WARN_PCT}\nbnez ta,@ui_est_ok\nmovi a0,33\nsbi a0,[a2 + 0]\naddi a2,a2,1'); s.label('ui_est_ok'); s.emit('beqz s6,@ui_est_known\nmovi a0,63\nsbi a0,[a2 + 0]\naddi a2,a2,1'); s.label('ui_est_known'); s.emit('movi a0,0\nsbi a0,[a2 + 0]\naddi a1,sp,80')


def hook_edit_strip(c):
    s = c.s
    # MOD036 admission warning in the strip (not GR Comp, no assignment prompt).
    s.emit(f'lwi s5,[s0 + 0xe0]\nbeqz s5,@gr_done\njal @est_compute\nmov55 s7,a1\naddi a0,a0,9\nmovi a3,10\ndivr s6,a5,a0,a3\nslti ta,s6,{WARN_PCT}\nbnez ta,@warn_clear\nslli a0,s6,1\nor s4,a0,s7\nlwi a0,[s1 + 140]\nbeqz a0,@warn_show\nlwi a0,[s1 + 144]\nbeq a0,s4,@gr_done')
    s.label('warn_show'); s.emit('addi s3,sp,96')
    for i, ch in enumerate('CPU HIGH '): s.emit(f'movi a0,{ord(ch)}\nsbi a0,[s3 + {i}]')
    s.emit('addi a2,s3,9\nmov55 a0,s6\njal @fmt_pct\nmovi a0,37\nsbi a0,[a2 + 0]\naddi a2,a2,1\nbeqz s7,@warn_known\nmovi a0,63\nsbi a0,[a2 + 0]\naddi a2,a2,1'); s.label('warn_known')
    s.emit(f'movi a0,0\nsbi a0,[a2 + 0]\nmov55 a0,s5\nmovi a1,0\nmovi a2,0\njal {API.lv_obj_set_pos:#x}\nmov55 a0,s5\nmovi a1,160\nmovi a2,20\njal {API.lv_obj_set_size:#x}\nmov55 a0,s5\nmov55 a1,s3\njal {API.mod026_set_text:#x}\nmov55 a0,s5\nmovi a1,1\njal {API.strip_label_show:#x}\nmovi a0,1\nswi a0,[s1 + 140]\nswi s4,[s1 + 144]\nj @gr_done')
    s.label('warn_clear'); s.emit(f'lwi a0,[s1 + 140]\nbeqz a0,@gr_done\nmovi a0,0\nswi a0,[s1 + 140]\nswi a0,[s1 + 144]\nmov55 a0,s0\njal {API.mod026_restore_ctx:#x}')


def section_est_compute(c):
    s = c.s; tbl = AC.table()[0]
    # est_compute: a0 = predicted ARM thousandths, a1 = unknown-id flag. Leaf; saves s0..s3.
    s.label('est_compute'); s.emit('addi sp,sp,-16\nswi s0,[sp + 0]\nswi s1,[sp + 4]\nswi s2,[sp + 8]\nswi s3,[sp + 12]'); s.address('a5', API.mdata_enable_mask)
    s.emit(f'lbi s2,[a5 + 0]\nlbi a0,[a5 + 1]\nslli a0,a0,8\nor s2,s2,a0\nmovi s3,0\nmovi a4,{AC.BASE}')
    for g in AC.ARM_GROUPS:
        o = API.MDATA_IDS_OFFSET + 4 * g; s.emit(f'lbi s0,[a5 + {o}]')
        for k in (1, 2, 3): s.emit(f'lbi a0,[a5 + {o + k}]\nslli a0,a0,{8 * k}\nor s0,s0,a0')
        s.emit(f'srli a0,s2,{g}\nmovi a1,1\nand a0,a0,a1\nbnez a0,@est_on{g}')
        if g == 7: s.address('a1', AC.PING_PONG_ID); s.emit(f'bne s0,a1,@est_next{g}\naddi a4,a4,{dict(tbl[7])[AC.PING_PONG_ID]}')
        s.emit(f'j @est_next{g}'); s.label(f'est_on{g}'); c.addr('a2', f'cost{g}'); s.emit(f'movi a3,{len(tbl[g])}')
        s.label(f'est_loop{g}'); s.emit(f'beqz a3,@est_unknown{g}\nlwi a0,[a2 + 0]\nbeq a0,s0,@est_found{g}\naddi a2,a2,8\naddi a3,a3,-1\nj @est_loop{g}')
        s.label(f'est_found{g}'); s.emit(f'lwi a0,[a2 + 4]\nadd a4,a4,a0\nj @est_next{g}'); s.label(f'est_unknown{g}'); s.emit(f'addi a4,a4,{AC.UNKNOWN}\nmovi s3,1'); s.label(f'est_next{g}')
    s.emit('mov55 a0,a4\nmov55 a1,s3\nlwi s0,[sp + 0]\nlwi s1,[sp + 4]\nlwi s2,[sp + 8]\nlwi s3,[sp + 12]\naddi sp,sp,16\nret5 lp')


def section_fmt_pct(c):
    s = c.s
    # fmt_pct: a0 in 0..999 -> decimal without leading zeros at a2; a2 advanced. Clobbers a0,a1,a3,a4,a5.
    s.label('fmt_pct'); s.emit('movi a3,100\ndivr a4,a5,a0,a3\nmovi a3,10\ndivr a0,a1,a5,a3\nbeqz a4,@fp_t\naddi a4,a4,48\nsbi a4,[a2 + 0]\naddi a2,a2,1\nj @fp_tw'); s.label('fp_t'); s.emit('beqz a0,@fp_o'); s.label('fp_tw'); s.emit('addi a0,a0,48\nsbi a0,[a2 + 0]\naddi a2,a2,1'); s.label('fp_o'); s.emit('addi a1,a1,48\nsbi a1,[a2 + 0]\naddi a2,a2,1\nret5 lp')


def data_costs(c):
    for g, rows in AC.table()[0].items():
        c.data(f'cost{g}', b''.join(struct.pack('<II', i, cost) for i, cost in rows))


CODE = {'est_compute': section_est_compute, 'fmt_pct': section_fmt_pct}
DATA = {'costs': data_costs}
HOOKS = {'home_arm_text': hook_home_arm_text, 'edit_strip': hook_edit_strip}


def patches(c):
    return []


def layout_info():
    return dict(base=AC.BASE, warn_pct=WARN_PCT, unknown=AC.UNKNOWN, groups=list(AC.ARM_GROUPS),
                entries=sum(len(v) for v in AC.table()[0].values()))
