"""GR Comp edit-page meter (MOD035 drawn meter, MOD037 square ends): window-4 tick wrapper that
chains the MOD026 editor tick, then builds/updates an LVGL container in the 160x20 strip
(bar 0..20 dB at 0.1 dB, ticks at 5/10/15 dB, fixed value label) while PRE shows GR Comp.
Other edit pages fall to the 'edit_strip' hook (admission warning). Window-4 close drops the
container pointer. Ported unchanged from scripts/build_nds_cpu_pct_code.py (MOD037).

Appearance knobs are module constants so a cosmetic change is a one-line edit here."""
from ..stock_api import API

NAME = 'gr_meter'
REQUIRES = ('telemetry',)
ORACLES = ('sdk/telemetry/nds/model_gr.py', 'sdk/telemetry/nds/model_gr_meter.py')
CASE_KINDS = ('editor',)
GR_ORDINAL = 15      # GR Comp appended to PRE after MOD033's entries
STRIP_W, STRIP_H = 160, 20
BAR = dict(w=96, h=8, x=24, y=5, max=200, radius=0)   # radius 0 = square ends (MOD037)
TICKS_X, TICK_Y, TICK_W, TICK_H = (48, 72, 96), 14, 1, 4
VALUE_X, VALUE_Y = 124, 2
# Feature strips (GP50_FEATURE_GR_METER): label and value on one line at the top, full-width bar below.
# The strip font is fixed-width (scripts/render_gr_strip.py draws this layout with the stock fonts).
STRIP_FONT, CHAR_W = 1, 6
FEATURE_BAR = dict(w=152, h=6, x=4, y=12, max=200, radius=0)
LABEL_X, TEXT_Y, VALUE_RIGHT = 4, 0, 156
POLL_TICKS = 100     # ~10 Hz request interval while shown


def section_editor_tick(c):
    s = c.s; STATE = c.STATE
    c.begin('gr_editor_tick', 176); s.emit(f'mov55 s0,a0\nmov55 s8,a1\nmov55 a0,s0\nmov55 a1,s8\njal {API.mod026_editor_tick:#x}'); s.address('s1', STATE); s.address('a0', API.mod026_assign_state)
    s.emit(f'lwi a0,[a0 + 0]\nbnez a0,@gr_hide\nlbi a0,[s0 + 0x90]\nslti ta,a0,10\nbeqz ta,@gr_not\nadd a0,s0,a0\nlbi s6,[a0 + 0x80]\nmovi a1,1\nbne s6,a1,@gr_not\nmov55 a0,s6\njal {API.effect_ordinal:#x}\nmovi a1,{GR_ORDINAL}\nbne a0,a1,@gr_not\nlwi s5,[s0 + 0xe0]\nbeqz s5,@gr_done\nmovi a0,0\nswi a0,[s1 + 140]\nswi a0,[s1 + 144]\nlwi s3,[s1 + 136]\nbnez s3,@gr_have')
    s.emit(f'mov55 a0,s5\nmovi a1,0\nmovi a2,0\njal {API.lv_obj_set_pos:#x}\nmov55 a0,s5\nmovi a1,{STRIP_W}\nmovi a2,{STRIP_H}\njal {API.lv_obj_set_size:#x}\nmov55 a0,s5'); c.addr('a1', 'gr_title'); s.emit(f'jal {API.mod026_set_text:#x}\nmov55 a0,s5\nmovi a1,1\njal {API.strip_label_show:#x}')
    s.emit(f'mov55 a0,s5\njal {API.lv_obj_create:#x}\nmov55 s3,a0\nmov55 a0,s3\nmovi a1,0\nsethi a2,0xff\naddi a2,a2,0xfff\njal {API.lv_obj_remove_style:#x}\nmov55 a0,s3\nmovi a1,{STRIP_W}\nmovi a2,{STRIP_H}\njal {API.lv_obj_set_size:#x}\nmov55 a0,s3\nmovi a1,0\nmovi a2,0\njal {API.lv_obj_set_pos:#x}')
    s.emit(f'mov55 a0,s3\njal {API.lv_bar_create:#x}\nmov55 s4,a0\nmov55 a0,s4\nmovi a1,{BAR["w"]}\nmovi a2,{BAR["h"]}\njal {API.lv_obj_set_size:#x}\nmov55 a0,s4\nmovi a1,{BAR["x"]}\nmovi a2,{BAR["y"]}\njal {API.lv_obj_set_pos:#x}\nmov55 a0,s4\nmovi a1,0\nmovi a2,{BAR["max"]}\njal {API.lv_bar_set_range:#x}'
           f'\nmov55 a0,s4\nmovi a1,{BAR["radius"]}\nmovi a2,0\njal {API.lv_obj_set_style_radius:#x}\nmov55 a0,s4\nmovi a1,{BAR["radius"]}\nsethi a2,{API.LV_PART_INDICATOR >> 12:#x}\njal {API.lv_obj_set_style_radius:#x}')
    for x in TICKS_X: s.emit(f'mov55 a0,s3\njal {API.lv_obj_create:#x}\nmov55 s6,a0\nmov55 a0,s6\nmovi a1,0\nsethi a2,0xff\naddi a2,a2,0xfff\njal {API.lv_obj_remove_style:#x}\nmov55 a0,s6\nmovi a1,{TICK_W}\nmovi a2,{TICK_H}\njal {API.lv_obj_set_size:#x}\nmov55 a0,s6\nmovi a1,{x}\nmovi a2,{TICK_Y}\njal {API.lv_obj_set_pos:#x}\nmov55 a0,s6\nmovi a1,0xffff\nmovi a2,0\njal {API.lv_obj_set_style_bg_color:#x}\nmov55 a0,s6\nmovi a1,255\nmovi a2,0\njal {API.lv_obj_set_style_bg_opa:#x}')
    s.emit(f'mov55 a0,s3\njal {API.lv_label_create:#x}\nmov55 s7,a0\nmov55 a0,s7\nmovi a1,{VALUE_X}\nmovi a2,{VALUE_Y}\njal {API.lv_obj_set_pos:#x}\nswi s3,[s1 + 136]\nmovi a0,1\nswi a0,[s1 + 92]')
    s.label('gr_have'); s.emit(f'mov55 a0,s3\nmovi a1,0\njal {API.lv_obj_get_child:#x}\nmov55 s4,a0\nmov55 a0,s3\nmovi a1,4\njal {API.lv_obj_get_child:#x}\nmov55 s7,a0\njal {API.irq_guard_enter:#x}'); s.address('a0', API.tick_counter)
    s.emit(f'lwi s2,[a0 + 0]\nlwi a0,[s1 + 88]\nbeqz a0,@gr_request\nlwi a0,[s1 + 84]\nsub a0,s2,a0\nslti ta,a0,{POLL_TICKS}\nbnez ta,@gr_snapshot'); s.label('gr_request'); s.emit('swi s2,[s1 + 84]\nmovi a0,1\nswi a0,[s1 + 88]\nswi a0,[s1 + 0]'); s.label('gr_snapshot')
    for i in range(10): s.emit(f'lwi a0,[s1 + {96 + 4 * i}]\nswi a0,[sp + {40 + 4 * i}]')
    for i, off in enumerate([8, 12, 20]): s.emit(f'lwi a0,[s1 + {off}]\nswi a0,[sp + {80 + 4 * i}]')
    s.emit(f'jal {API.irq_guard_leave:#x}\nmovi s6,0\nlwi a0,[sp + 80]\nbeqz a0,@gr_wait\nlwi a0,[sp + 84]\nbnez a0,@gr_error\nlwi a0,[sp + 88]\nsub a0,s2,a0\nslti ta,a0,1000\nbeqz ta,@gr_old\nlwi a0,[sp + 76]\nbeqz a0,@gr_wait\nlbi a0,[sp + 40]\nbeqz a0,@gr_none\nlbi a0,[sp + 72]\nslti ta,a0,11\nbeqz ta,@gr_none\nlbi a0,[sp + 73]\nmovi a1,1\nand a1,a0,a1\nbeqz a1,@gr_none\nmovi a1,2\nand a1,a0,a1\nbeqz a1,@gr_off')
    s.emit('lhi s6,[sp + 70]\nsethi a1,0x1\nori a1,a1,0x770\nslt ta,a1,s6\nbeqz ta,@gr_clamped\nmov55 s6,a1'); s.label('gr_clamped')
    s.emit('addi a1,s6,5\nmovi a2,10\ndivr s6,a3,a1,a2\naddi a5,sp,96\nmovi a2,10\ndivr a4,a3,s6,a2\nmovi a2,10\ndivr a0,a1,a4,a2\nbeqz a0,@gr_units\naddi a0,a0,48\nsbi a0,[a5 + 0]\naddi a5,a5,1'); s.label('gr_units')
    s.emit('addi a1,a1,48\nsbi a1,[a5 + 0]\nmovi a0,46\nsbi a0,[a5 + 1]\naddi a3,a3,48\nsbi a3,[a5 + 2]\nmovi a0,0\nsbi a0,[a5 + 3]\naddi a1,sp,96\nj @gr_set')
    for st in ('wait', 'error', 'old', 'none', 'off'): s.label('gr_' + st); c.addr('a1', 'gr_' + st + '_s'); s.emit('j @gr_set')
    s.label('gr_set'); s.emit(f'mov55 s5,a1\nslti ta,s6,{BAR["max"] + 1}\nbnez ta,@gr_val_ok\nmovi s6,{BAR["max"]}'); s.label('gr_val_ok'); s.emit(f'mov55 a0,s4\nmov55 a1,s6\nmovi a2,0\njal {API.lv_bar_set_value:#x}\nmov55 a0,s7\nmov55 a1,s5\njal {API.lv_label_set_text:#x}\nj @gr_done')
    s.label('gr_hide'); s.emit(f'movi a0,0\nswi a0,[s1 + 140]\nswi a0,[s1 + 144]\nlwi s3,[s1 + 136]\nbeqz s3,@gr_done\nmov55 a0,s3\njal {API.lv_obj_del:#x}\nmovi a0,0\nswi a0,[s1 + 136]\nswi a0,[s1 + 92]\nj @gr_done')
    s.label('gr_not'); s.emit(f'lwi a0,[s1 + 92]\nbeqz a0,@warn\nlwi s3,[s1 + 136]\nbeqz s3,@gr_not_restore\nmov55 a0,s3\njal {API.lv_obj_del:#x}'); s.label('gr_not_restore'); s.emit(f'movi a0,0\nswi a0,[s1 + 136]\nswi a0,[s1 + 92]\nmov55 a0,s0\njal {API.mod026_restore_ctx:#x}')
    # Hook contract (falls through from gr_not): s0 = edit ctx, s1 = STATE, frame 176 B with
    # sp+96.. free text buffer; state +140/+144 belong to the hook; must end at @gr_done.
    s.label('warn'); c.hook('edit_strip')
    s.label('gr_done'); s.emit('movi a0,0'); c.end(176)


def section_close(c):
    s = c.s
    # Window 4 close: the screen deletes our container with it; drop the pointer, then MOD026 close.
    s.label('gr_close'); s.address('a2', c.STATE); s.emit(f'movi a3,0\nswi a3,[a2 + 92]\nswi a3,[a2 + 136]\nswi a3,[a2 + 140]\nswi a3,[a2 + 144]\nj ' + ('@legacy_w4_close' if 'legacy_ui_c' in c.enabled else f'{API.mod026_window4_close:#x}'))   # MOD055+: close stub in C segment


def data_strings(c):
    for key, text in [('gr_title', 'GR'), ('gr_wait_s', '--'), ('gr_error_s', 'ERR'), ('gr_old_s', 'OLD'), ('gr_none_s', 'NONE'), ('gr_off_s', 'OFF')]:
        c.data(key, text.encode() + b'\0')


CODE = {'editor_tick': section_editor_tick, 'close': section_close}
DATA = {'strings': data_strings}


def patches(c):
    L = c.labels
    return [(API.hook_window4_tick, f'j {L["gr_editor_tick"]:#x}', 'window 4 tick: GR wrapper, then MOD026 editor tick'),
            (API.hook_window4_close, f'j {L["gr_close"]:#x}', 'window 4 close: drop meter pointer, then MOD026 close')]
