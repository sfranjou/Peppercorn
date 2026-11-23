"""Legacy UI features in C (code room step 1, MOD055; analysis/firmware/NDS_CODE_ROOM.md, NDS_ASM_TO_C_INVENTORY.md):
the MOD026 editor knob assignment, MOD029 home bars / reset mode / GPAM store, MOD027 Wah auto and MOD028 title meter
handlers, formerly hand-written assembly in 0x16d000..0x16ffff, run the readable sources compared with that assembly
(firmware/reconstructed/nds/wah_auto.c, assign_store.c, assign_home.c, assign_editor.c, assign_map.c, meter_home.c)
through pedal builds in sdk/nds/legacy_ui/. With this feature the segment base moves down to 0x16d000 (the diagnostics
block 0x16c6c0..0x16cfff stays), which re-points every legacy reach:

- stock hook sites (declared hook_legacy_* in the stock-API map): window-4 open 0x1cc5c (`j` prologue-replay stub),
  editor table pair 0x1cc62/0x1cc66, home table pair 0x21e4a/0x21e4e, home tick 0x224f2, preset read 0x43fbc,
  sector staging copy 0x496ac, User_Msg poll 0x49c7e (found by scripts/nds_legacy_reach.py on the parent);
- C features: mod026_set_text / mod026_restore_ctx / mod026_editor_tick link to the C functions (LINK_ALIASES), the GR
  close tail enters the close stub here, and the MOD029 meter-refresh call sites are gone (the C calls nds_refresh2).

Stays assembly (prologue replays that enter stock functions mid-body): window-4 open/close, editor tick, home tick.
The two window message tables are C data (legacy_ui_tables.c) with the words copied from the parent.
Proof: scripts/verify_nds_generic_image.py --remap (legacy studies on parent b vs candidate b)."""
import struct
from ..stock_api import API

NAME = 'legacy_ui_c'
REQUIRES = ('gr_meter', 'home_meter', 'mem_page')
CONFLICTS = ()
ORACLES = ()
CASE_KINDS = ()
_D = 'sdk/nds/legacy_ui/'
C_SOURCES = tuple(_D + m + '.c' for m in ('wah_auto', 'assign_store', 'assign_percent', 'assign_home', 'assign_editor', 'assign_map', 'meter_home', 'legacy_ui_tables'))
def c_sources(cfg):
    return C_SOURCES + ((_D + 'assignment_menu.c',) if 'GP50_ASSIGNMENT_MENU=1' in (cfg or {}).get('c_defines', ()) else ())

C_HARD_FLOAT = True   # assign_percent computes in float; assign_bars reads float getters (fs0)
C_HARD_FLOAT_SOURCES = (_D + 'assign_percent.c', _D + 'assign_home.c')   # assign_store.c soft-float (no FPU spills in the flash path)
# MOD054 address of every legacy entry -> its replacement (C function, or asm stub label). Used for the window tables,
# the hook targets and the image proof's address remapping.
LEGACY = {
    0x16e000: 'legacy_w4_open', 0x16e01c: 'legacy_w4_close', 0x16e9ca: 'legacy_editor_tick_stock', 0x16ea12: 'legacy_home_tick_stock',
    0x16e034: 'assign_editor_hold', 0x16e06c: 'assign_editor_back', 0x16e0d8: 'assign_editor_drum', 0x16e1e2: 'assign_editor_encoder',
    0x16e302: 'assign_para', 0x16e360: 'assign_page', 0x16e39c: 'assign_restore', 0x16e3f4: 'assign_render_current',
    0x16e46c: 'assign_render', 0x16e52c: 'assign_set_text', 0x16e558: 'assign_publish', 0x16e630: 'assign_valid_map',
    0x16e6fe: 'assign_home_knob', 0x16e7b0: 'assign_home_refresh', 0x16e948: 'assign_editor_tick', 0x16e9d6: 'assign_home_tick',
    0x16ec00: 'assign_crc32', 0x16ec4a: 'assign_u32', 0x16ec74: 'assign_preset_read', 0x16eec4: 'assign_commit', 0x16ef06: 'assign_percent',
    0x16efa2: 'assign_title_restore', 0x16f900: 'assign_stage_copy', 0x16faac: 'assign_bars', 0x16fc3e: 'assign_reset_prompt',
    0x16fc80: 'assign_hold', 0x16fce4: 'assign_drum', 0x16fd48: 'assign_back', 0x16fdb4: 'assign_home_encoder', 0x16fe84: 'assign_tick',
    0x16f000: 'wah_name', 0x16f0e8: 'wah_poll', 0x16f122: 'wah_policy',
    0x16f400: 'meter_tick', 0x16f43c: 'meter_drum', 0x16f4a8: 'meter_back', 0x16f514: 'meter_restore',
    0x16ea20: 'legacy_editor_table', 0x16ff0c: 'legacy_home_table'}
ASM = ('legacy_w4_open', 'legacy_w4_close', 'legacy_editor_tick_stock', 'legacy_home_tick_stock')
C_ENTRIES = tuple(n for n in LEGACY.values() if n not in ASM)
LINK_ALIASES = {'mod026_set_text': 'assign_set_text', 'mod026_restore_ctx': 'assign_restore', 'mod026_editor_tick': 'assign_editor_tick'}
TABLES = (('EDITOR', 0x16ea20, 0x1cc62), ('HOME', 0x16ff0c, 0x21e4a))
EDITOR_ENTRIES, HOME_ENTRIES = 22, 26   # 0x16e016 movpi45 a1,#0x16 (stock 20); 0x21e46 movpi45 a1,#0x1a (stock 24)
OLD_SEGMENT = (0x16d000, 0x170000)
# Intended parent edits inside stock bodies (kept when those bodies run as stock): home table entry count 24 -> 26.
PARENT_EDITS = {0x21e46: (2, 'home constructor movpi45 a1,#0x1a: 26-entry legacy_home_table (stock 24)')}
# Bulk module holding each table constructor / window-4 entry (stock_in_place: those run as stock again).
TABLE_MODULE = {'EDITOR': 'ui_effect_lifecycle', 'HOME': 'ui_home_open'}


def _bulk_c(c, module):
    """True when application_bulk_c provides `module` as compiled C (not stock_in_place)."""
    from ..stock_in_place import bulk_stems
    return 'application_bulk_c' in c.enabled and module not in bulk_stems(c.cfg)


def enabled(cfg):
    return NAME in ((cfg or {}).get('features') or ())


def c_headers(cfg=None, parent_b=None):
    """legacy_ui_tables.h: the two window tables from the parent, legacy handler words replaced by the C symbols. The
    parent must still hold the MOD054 tables (its sethi/ori pairs point at them and the counts match)."""
    # MOD056+ (host_layer_c): the feature's "preset modified" calls (editor commit, home reset) also send the `12 71`
    # notification (own_assign_modified, sdk/nds/host_layer/own_commands.c).
    cfgh = {'legacy_ui_config.h': f'#ifndef LEGACY_UI_CONFIG_H\n#define LEGACY_UI_CONFIG_H\n#define LEGACY_ASSIGN_NOTIFY {int(host_layer(cfg))}\n#endif\n'}
    if parent_b is None: return cfgh
    b = parent_b; w16 = lambda a: int.from_bytes(b[a - 0x10000:a - 0x10000 + 2], 'big')
    relink = None
    if w16(0x21e46) == 0xfa2a and len(b) > 0x16e016 - 0x10000 and w16(0x16e016) != 0xfa26 and pinned_mod054() is not None:
        # Parent already runs this feature (MOD055+): the tables are C data in its segment. Rebuild them from MOD054's
        # words (pinned input) and require the parent's tables to agree word for word (stock words equal, legacy handler
        # words pointing into the parent's segment).
        relink = b; b = pinned_mod054()
    if w16(0x21e46) != 0xfa2a or w16(0x16e016) != 0xfa26: raise ValueError('parent window-table counts are not the MOD054 ones')
    out = ['/* GENERATED by scripts/nds_ui/features/legacy_ui_c.py from the parent image (window message tables). */',
           '#ifndef LEGACY_UI_TABLES_H', '#define LEGACY_UI_TABLES_H', f'#define LEGACY_EDITOR_ENTRIES {EDITOR_ENTRIES}', f'#define LEGACY_HOME_ENTRIES {HOME_ENTRIES}']
    for name, at, pair in TABLES:
        hi, lo = (int.from_bytes(b[p - 0x10000:p - 0x10000 + 4], 'big') for p in (pair, pair + 4))
        if (hi & 0xfffff) << 12 | lo & 0x7fff != at: raise ValueError(f'parent {name} table pair does not point at {at:#x}')
        n = EDITOR_ENTRIES if name == 'EDITOR' else HOME_ENTRIES
        words = struct.unpack(f'<{2 * n}I', b[at - 0x10000:at - 0x10000 + 8 * n]); items = []
        for i, w in enumerate(words):
            if i % 2 and OLD_SEGMENT[0] <= w < OLD_SEGMENT[1]:
                if w not in LEGACY: raise ValueError(f'{name} table handler {w:#x} has no C replacement')
                items.append(f'(uint32_t)(uintptr_t){LEGACY[w]}')
            elif i % 2 and 0x16c6c0 <= w < 0x176000: raise ValueError(f'{name} table word {w:#x} points into the NDS segment')
            else: items.append(f'{w:#010x}u')
        if relink is not None:
            ph, pl = (int.from_bytes(relink[p - 0x10000:p - 0x10000 + 4], 'big') for p in (pair, pair + 4)); pt = (ph & 0xfffff) << 12 | pl & 0x7fff
            pw = struct.unpack(f'<{2 * n}I', relink[pt - 0x10000:pt - 0x10000 + 8 * n])
            for i, (w, v) in enumerate(zip(words, pw)):
                legacy_word = i % 2 and OLD_SEGMENT[0] <= w < OLD_SEGMENT[1]
                if (legacy_word and not 0x16c6c0 <= v < 0x176000) or (not legacy_word and v != w): raise ValueError(f'parent {name} table word {i} ({v:#x}) disagrees with MOD054 ({w:#x})')
        if 'GP50_FEATURE_ASSIGNMENT=1' in (cfg or {}).get('c_defines', ()):
            # SDK assignment feature: every key/rotary entry offers the message to SDK features first, then the stock
            # handler the MOD026/029 code fell back to (analysis/firmware/SDK_SERVICES_PLAN.md, UI service design).
            screen = 'GP50_SCREEN_EDITOR' if name == 'EDITOR' else 'GP50_SCREEN_HOME'
            fallback = {0x16e06c: 'STOCK_CALL(&legacy_menu_io,0x1b9d8,ctx,event)', 0x16e1e2: 'STOCK_CALL(&legacy_menu_io,0x1c376,ctx,event)',
                        0x16e302: 'STOCK_CALL(&legacy_menu_io,0x1be7e,ctx,event)', 0x16e360: 'STOCK_CALL(&legacy_menu_io,0x1b912,ctx,event)',
                        0x16e034: '1', 0x16e0d8: '1', 0x16fce4: '1', 0x16fc80: '1',
                        0x16fd48: 'STOCK_CALL(&legacy_menu_io,0x2159c,ctx,event)'}
            wrappers = []
            for j in range(n):
                ev, target = words[2*j:2*j+2]
                if ev & 0xff not in (2, 3): continue   # host (6) entries and the tick stay as they are
                fn = f'gp50_ui_{name.lower()}_{j}'
                if target == 0x16fdb4:                 # home knobs: knob 1/2/3 stock handlers (MOD029 assign_home_knob)
                    knob = {0x103: 0x218a0, 0x203: 0x21a38, 0x303: 0x21860}.get(ev & 0xffff)
                    call = f'STOCK_CALL(&legacy_menu_io,{knob:#x},ctx,event)' if knob else '1'
                elif target in LEGACY: call = fallback[target]
                else: call = f'STOCK_CALL(&legacy_menu_io,{target:#x},ctx,event)'
                body = f'if (gp50_features_ui({screen},{ev:#x}u,ctx,event)) return 0; return {call};'
                wrappers.append(f'static uint32_t {fn}(uint32_t ctx,uint32_t event) {{ {body} }}')
                items[2*j+1] = f'(uint32_t)(uintptr_t){fn}'
            if name == 'EDITOR': out += ['#include "components/platform/gp50_features.h"', 'static const StockIo legacy_menu_io;']
            out += wrappers
        elif name == 'EDITOR' and 'GP50_ASSIGNMENT_MENU=1' in (cfg or {}).get('c_defines', ()):
            wrappers = []
            for j in range(n):
                ev, target = words[2*j:2*j+2]
                if ev == 0x2506: continue  # stock tick + assignment_tick in assign_map.c
                fn = f'legacy_editor_input_{j}'
                call = (f'{LEGACY[target]}(ctx' + (',&legacy_menu_io)' if target == 0x16e034 else ',event,&legacy_menu_io)') if target in LEGACY
                        else f'STOCK_CALL(&legacy_menu_io,{target:#x},ctx,event)')
                wrappers.append(f'static uint32_t {fn}(uint32_t ctx,uint32_t event) {{ '
                                f'if (assignment_input(ctx,event,&legacy_menu_io)) return 0; return {call}; }}')
                items[2*j+1] = f'(uint32_t)(uintptr_t){fn}'
            out += ['static const StockIo legacy_menu_io;', *wrappers]
        out.append(f'#define LEGACY_{name}_TABLE ' + ', '.join(items))
    return {'legacy_ui_tables.h': '\n'.join(out + ['#endif', '']), **cfgh}


MOD054 = ('work/custom_images/mod054_tone_capture/GP-50_V1.1.0_MOD054_ToneCapture.bin', 'c414132e2b16e46e7f31019c9bb044d70a7be10126402574c0e81268287ad124')


def pinned_mod054():
    """MOD054's region b (source of the window tables for parents that already run this feature), from the sha-pinned
    MOD054 container (the parent of MOD055)."""
    import hashlib
    from ..build import ROOT
    p = ROOT / MOD054[0]
    if not p.exists(): return None
    img = p.read_bytes()
    if hashlib.sha256(img).hexdigest() != MOD054[1]: raise ValueError('MOD054 image differs from the pinned one')
    from firmware_verify import decode
    regions, _ = decode(img); return {r: v for r, _, v in regions}['b']


def section_stubs(c):
    """The four prologue-replay stubs, as in MOD054 (0x16e000, 0x16e01c, 0x16e9ca, 0x16ea12). push25 also loads r8 (s2)
    with the address of the push25 itself; the stubs set s2 to the stock instruction's address so the rest of the stock
    body sees the same register state."""
    s = c.s
    s.label('legacy_w4_open')   # 0x1cc5c: assignment phase reset, then the stock window-4 open (22-entry editor table)
    s.address('a2', API.mod026_assign_state); s.emit('movi a3,0\nswi a3,[a2 + 0]'); s.emit('j @nds_bulk_1cc5c' if _bulk_c(c, 'ui_effect_lifecycle') else 'push25 s8,16\nmovi s2,0x1cc5c\nmovpi45 a1,0x16\nj 0x1cc60')
    s.label('legacy_w4_close')  # stock window-4 close 0x1d2bc (GR close tail ends here)
    s.address('a2', API.mod026_assign_state); s.emit('movi a3,0\nswi a3,[a2 + 0]'); s.emit('j @nds_bulk_1d2bc' if _bulk_c(c, 'ui_effect_lifecycle') else 'push25 s0,0\nlwi333 a0,[a0 + 0x1c]\nj 0x1d2c0')
    s.label('legacy_editor_tick_stock')   # stock window-4 tick 0x1d2c8 after its hook
    s.emit('j @nds_bulk_1d2c8' if _bulk_c(c, 'ui_effect_tick') else 'push25 s4,32\nmovi s2,0x1d2c8\nmov55 s0,a0\nj 0x1d2cc')
    s.label('legacy_home_tick_stock')     # stock home tick 0x224f2 after its hook
    from . import home_tick_c
    if 'home_tick_c' in c.cfg.get('features', ()) and not home_tick_c.stock(c.cfg):
        s.emit('j @home_tick_body_c')   # tail entry preserves outer assignment/meter calls
    else:
        s.emit('push25 s4,16\nmovi s2,0x224f0\nmov55 s0,a0\nj 0x224f6')


CODE = {'stubs': section_stubs}
DATA = {}
HOOKS = {}


def patches(c):
    L = c.labels
    out = [(API.hook_legacy_window4_open, f'j {L["legacy_w4_open"]:#x}', 'window-4 open: assignment reset + stock open (prologue replay)')]
    for name, at, pair in TABLES:
        if _bulk_c(c, TABLE_MODULE[name]): continue  # C builders reference relocated arrays directly
        t = L[LEGACY[at]]; key = name.lower()
        out += [(pair, f'sethi a0,{t >> 12:#x}', f'{key} window message table (hi)'), (pair + 4, f'ori a0,a0,{t & 4095:#x}', f'{key} window message table (lo)')]
    if 'GP50_FEATURE_ASSIGNMENT=1' in c.cfg.get('c_defines', ()):
        out += [(API.hook_legacy_home_tick, f'j {L["gp50_ui_home_tick"]:#x}', 'home tick: SDK screen context + stock home tick')]
    else:
        out += [(API.hook_legacy_home_tick, f'j {L["assign_tick"]:#x}', 'home tick: MOD029 assign_tick (C)')]
    if not host_layer(c.cfg):   # MOD056+: the bodies holding these two call sites are C (host_layer_c) and call these directly
        out += [(API.hook_legacy_preset_read, f'jal {L["assign_preset_read"]:#x}', 'preset read: GPAM bindings (C)'),
                (API.hook_legacy_stage_copy, f'jal {L["assign_stage_copy"]:#x}', 'sector staging copy: GPAM tail (C)')]
    if 'GP50_FEATURE_AUTO_WAH=1' in c.cfg.get('c_defines', ()):   # auto-wah is the SDK feature auto_wah: stock poll only
        out += [(API.hook_legacy_user_poll, 'jal 0x49b52', 'User_Msg poll: stock poll restored (auto-wah moved to the SDK)')]
    else:
        out += [(API.hook_legacy_user_poll, f'jal {L["wah_poll"]:#x}', 'User_Msg poll: Wah auto-engage (C)')]
    return out


def host_layer(cfg):
    return 'host_layer_c' in ((cfg or {}).get('features') or ())


def remap(labels):
    """MOD054 legacy address -> candidate address (for the image proof)."""
    return {a: labels[n] for a, n in LEGACY.items()}
