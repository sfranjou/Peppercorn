"""Host layer in C on the pedal (MOD056; analysis/firmware/NDS_CODE_ROOM.md section 8.2, OWN_HOST_COMMANDS.md): the host
receive/reply/parse/handler/settings path, the preset serialisation and store, the assignment refresh and the factory
reset run the readable sources compared with the original instructions (firmware/reconstructed/nds: host_reply.c,
host_receive.c, host_parse.c, host_handlers.c, host_settings.c, preset_tlv.c, preset_record.c, assign_refresh.c,
factory_reset.c) through pedal builds in sdk/nds/host_layer/. Each stock entry becomes `j nds_host_<address>`; calls
between the modules keep the stock addresses.

Hooks of the parent inside the replaced bodies are reproduced in the C (compile-time remap, as legacy_ui_module.h):
- 0x4357a (telemetry `12 51` read route, in the parser 0x43374) and 0x429ce/0x429d2 (telemetry's read table, in the
  read dispatcher 0x429b4): host_parse's HOST_OWN_GET hook routes `12 51` (length 2) to read-table entry 12 and our
  own_read_table (parent's 12 stock words + telemetry `host` + `12 70`/`12 71`) is the table; telemetry_c drops the two
  hooks, its read_route stub and its read-table copy for configs with this feature;
- 0x43fbc (MOD029 slot read in the stored-preset read 0x43fa6) and 0x496ac (MOD029 staging copy in 0x4965a):
  preset_record's PRESET_READ_SLOT / STAGE_COPY are assign_preset_read / assign_stage_copy; legacy_ui_c drops the hooks.
Own commands (new behaviour, model-tested by scripts/test_nds_own_commands.py): `12 70` identity, `12 71` / `11 71`
knob assignments and the `12 71` change notification (legacy_ui_c's "preset modified" calls go through
own_assign_modified for configs with this feature). Stays stock: link_receive 0x46a0a (the telemetry/MOD030 receive
hook 0x46ab6 inside it continues in the kept assembly at 0x46aba/0x46b7a; ported with the diagnostics block). Admission
hook sites 0x473f6/0x475de/0x47456 are in functions that stay stock and are still called by their stock addresses.
Proof: scripts/verify_nds_generic_image.py (host studies, parent vs candidate), scripts/verify_nds_host_reply_image.py."""
import struct
from ..stock_api import API

NAME = 'host_layer_c'
REQUIRES = ('telemetry', 'legacy_ui_c')
CONFLICTS = ()
ORACLES = ()
CASE_KINDS = ()
_D = 'sdk/nds/host_layer/'
C_SOURCES = tuple(_D + m + '.c' for m in ('host_reply', 'host_receive', 'host_parse', 'host_handlers', 'host_settings', 'preset_tlv',
                                          'preset_record', 'assign_refresh', 'factory_reset', 'own_pedal'))
C_HARD_FLOAT = True   # float arguments/results in fs0 (stock convention): handlers `11 13`, settings, assignment refresh, reset
C_HARD_FLOAT_SOURCES = tuple(_D + m + '.c' for m in ('host_handlers', 'host_settings', 'assign_refresh', 'factory_reset'))
# Redirected stock entry -> readable name in the compared source (study FUNCTIONS / host reply ENTRIES).
ENTRIES = {
    0x1540a: 'frame_crc8', 0x4085c: 'frame_pack', 0x432a2: 'frame_transport', 0x40942: 'frame_send', 0x15a1e: 'reply_queue', 0x15b18: 'reply_flush',
    0x4089c: 'rx_decode', 0x408de: 'rx_crc', 0x408e8: 'rx_ack', 0x4385c: 'rx_usb_release', 0x43876: 'rx_usb_reset', 0x438a6: 'rx_usb_append',
    0x438f0: 'rx_usb_receive', 0x43820: 'rx_usb_init', 0x435dc: 'rx_bt_release', 0x43612: 'rx_bt_reset', 0x4364a: 'rx_bt_append',
    0x43724: 'rx_bt_receive', 0x436d4: 'rx_bt_init',
    0x43374: 'host_parse', 0x429a0: 'host_set_dispatch', 0x429b4: 'host_get_dispatch',
    0x40a6e: 'host_names', 0x40ad8: 'host_cab_bank', 0x40b40: 'host_ns_bank', 0x40ba8: 'host_static_reply', 0x41394: 'host_dirty_reply',
    0x413be: 'host_word_1a', 0x418f0: 'host_word_1b', 0x41918: 'host_snaptone_selector', 0x41dae: 'host_select_preset', 0x41dd2: 'host_set_44',
    0x41e68: 'host_set_4d', 0x41eb8: 'host_enable', 0x41edc: 'host_copy_preset', 0x41f16: 'host_set_3f', 0x41f20: 'host_set_31',
    0x41f2a: 'host_set_5a', 0x424fc: 'host_set_level', 0x4250a: 'host_current_preset', 0x425de: 'host_cab_bank_write',
    0x425f4: 'host_ns_bank_write', 0x4260a: 'host_ns_parts', 0x426f6: 'host_cab_rename', 0x42740: 'host_ns_rename', 0x4278a: 'host_cab_delete',
    0x427ae: 'host_ns_delete', 0x429e6: 'host_rename_preset', 0x42a26: 'host_store_named', 0x42fd8: 'host_load_preset',
    0x419f6: 'host_setting_11', 0x42820: 'host_setting_42', 0x414b2: 'host_settings_dump',
    0x42180: 'tlv_header', 0x421ce: 'tlv_format', 0x4220a: 'tlv_global', 0x42328: 'tlv_order', 0x42350: 'tlv_models', 0x42394: 'tlv_parameters',
    0x423ba: 'tlv_chain', 0x42422: 'tlv_tail', 0x42488: 'host_active_preset', 0x42532: 'host_stored_preset', 0x42a98: 'host_write_preset',
    0x43fa6: 'preset_read_stored', 0x45f9c: 'preset_migrate', 0x442f2: 'preset_load_factory', 0x47648: 'preset_apply', 0x4468a: 'preset_save',
    0x49772: 'flash_store_request', 0x4965a: 'flash_stage_sector',
    0x47d68: 'assign_refresh', 0x47c22: 'assign_set', 0x4787e: 'factory_reset_step'}
# host_reply routines that take the ReplyServices table: the compared function keeps an hr_ name, a wrapper with the
# stock arguments is the entry (sdk/nds/host_layer/host_reply.c).
WRAPPED = {0x432a2, 0x40942, 0x15a1e, 0x15b18}
# Entries returning a value in a0 (caller register contract, scripts/nds_catalog_caller_abi.py): void C functions here
# are the TLV builders and preset_default_record (not an entry).
VOID = {0x42180, 0x421ce, 0x4220a, 0x42328, 0x42350, 0x42394, 0x423ba, 0x42422}
HOOKED = tuple(sorted(ENTRIES))
# Reconstructed module defining each entry (stock_in_place pairing; entries are aliases, see c_headers). Generated
# 2026-11-03 from the definitions of ENTRIES names in firmware/reconstructed/nds; WRAPPED entries live in host_reply.c.
ENTRY_MODULES = {
    0x1540a: 'host_reply', 0x15a1e: 'host_reply', 0x15b18: 'host_reply', 0x4085c: 'host_reply', 0x4089c: 'host_receive',
    0x408de: 'host_receive', 0x408e8: 'host_receive', 0x40942: 'host_reply', 0x40a6e: 'host_handlers', 0x40ad8: 'host_handlers',
    0x40b40: 'host_handlers', 0x40ba8: 'host_handlers', 0x41394: 'host_handlers', 0x413be: 'host_handlers', 0x414b2: 'host_settings',
    0x418f0: 'host_handlers', 0x41918: 'host_handlers', 0x419f6: 'host_settings', 0x41dae: 'host_handlers', 0x41dd2: 'host_handlers',
    0x41e68: 'host_handlers', 0x41eb8: 'host_handlers', 0x41edc: 'host_handlers', 0x41f16: 'host_handlers', 0x41f20: 'host_handlers',
    0x41f2a: 'host_handlers', 0x42180: 'preset_tlv', 0x421ce: 'preset_tlv', 0x4220a: 'preset_tlv', 0x42328: 'preset_tlv',
    0x42350: 'preset_tlv', 0x42394: 'preset_tlv', 0x423ba: 'preset_tlv', 0x42422: 'preset_tlv', 0x42488: 'preset_tlv',
    0x424fc: 'host_handlers', 0x4250a: 'host_handlers', 0x42532: 'preset_tlv', 0x425de: 'host_handlers', 0x425f4: 'host_handlers',
    0x4260a: 'host_handlers', 0x426f6: 'host_handlers', 0x42740: 'host_handlers', 0x4278a: 'host_handlers', 0x427ae: 'host_handlers',
    0x42820: 'host_settings', 0x429a0: 'host_parse', 0x429b4: 'host_parse', 0x429e6: 'host_handlers', 0x42a26: 'host_handlers',
    0x42a98: 'preset_tlv', 0x42fd8: 'host_handlers', 0x432a2: 'host_reply', 0x43374: 'host_parse', 0x435dc: 'host_receive',
    0x43612: 'host_receive', 0x4364a: 'host_receive', 0x436d4: 'host_receive', 0x43724: 'host_receive', 0x43820: 'host_receive',
    0x4385c: 'host_receive', 0x43876: 'host_receive', 0x438a6: 'host_receive', 0x438f0: 'host_receive', 0x43fa6: 'preset_record',
    0x442f2: 'preset_record', 0x4468a: 'preset_record', 0x45f9c: 'preset_record', 0x47648: 'preset_record', 0x4787e: 'factory_reset',
    0x47c22: 'assign_refresh', 0x47d68: 'assign_refresh', 0x4965a: 'preset_record', 0x49772: 'preset_record'}
C_ENTRIES = tuple(f'nds_host_{a:05x}' for a in HOOKED) + ('own_read_table', 'own_assign_modified')
# Hooks of other features inside the bodies replaced here (dropped by those features for configs with this one).
SUPERSEDED = {0x4357a: 'telemetry_c read route (12 51)', 0x429ce: 'telemetry_c read table (hi)', 0x429d2: 'telemetry_c read table (lo)',
              0x43fbc: 'legacy_ui_c GPAM preset read', 0x496ac: 'legacy_ui_c GPAM staging copy'}


def enabled(cfg):
    return NAME in ((cfg or {}).get('features') or ())


def c_headers(cfg=None, parent_b=None):
    names = ['/* GENERATED by scripts/nds_ui/features/host_layer_c.py: redirected stock entry -> C symbol. */',
             '#ifndef HOST_LAYER_ENTRIES_H', '#define HOST_LAYER_ENTRIES_H']
    if 'tap_safe_c' in ((cfg or {}).get('features') or ()):
        names.append('#define GP50_TAP_SAFE_HOST 1')
    for a in HOOKED:
        names.append(f'#define {ENTRIES[a]} {"hr_" + ENTRIES[a] if a in WRAPPED else f"nds_host_{a:05x}"}   /* {a:#x} */')
    out = {'host_layer_entries.h': '\n'.join(names + ['#endif', ''])}
    if parent_b is not None:
        off = API.host_read_table - 0x10000; words = struct.unpack('<12I', parent_b[off:off + 48])
        # MOD056+ with diagnostics_c: a word into the old diagnostics block (MOD002 `12 50` = 0x16c954) becomes its C symbol.
        from . import diagnostics_c as D
        diag = D.LEGACY if D.enabled(cfg) else {}
        for w in words:
            if D.BLOCK[0] <= w < D.BLOCK[1] and w not in diag and D.enabled(cfg): raise ValueError(f'parent read-table word {w:#x} in the diagnostics block has no replacement')
        decl = ''.join(f'uint32_t {diag[w]}();\n' for w in sorted(set(words)) if w in diag)
        out['host_layer_table.h'] = ('/* GENERATED by scripts/nds_ui/features/host_layer_c.py (stock read table words from the parent image). */\n'
                                     '#ifndef HOST_LAYER_TABLE_H\n#define HOST_LAYER_TABLE_H\n' + decl + '#define HOST_READ_TABLE_PARENT '
                                     + ', '.join(f'(uint32_t)(uintptr_t){diag[w]}' if w in diag else f'{w:#010x}u' for w in words) + '\n#endif\n')
    else:
        out['host_layer_table.h'] = '#ifndef HOST_LAYER_TABLE_H\n#define HOST_LAYER_TABLE_H\n#define HOST_READ_TABLE_PARENT ' + ', '.join(['0u'] * 12) + '\n#endif\n'
    return out


PARSE_SOURCE = 'sdk/nds/host_layer/own_parse_entry.c'


def _parse_stock(cfg):
    """host_parse runs as stock (stock_in_place): own commands go through the own_parse_entry wrapper."""
    cfg = cfg or {}   # read the lists directly: the generic rule calls c_sources(), which calls this
    keep = cfg.get('stock_in_place_by_feature', {}).get(NAME, cfg.get('stock_in_place', ()))
    return NAME in cfg.get('stock_in_place_features', ()) and 'host_parse' in keep


def parse_stock(c):
    if not _parse_stock(c.cfg): return
    c.s.label('parse_stock_43374'); c.s.emit('push25 s2,8\nmov55 s1,a1\nj 0x43378')   # exact displaced stock prologue


def preset_stock(c):
    if not _preset_stock(c.cfg): return
    c.s.label('preset_stock_442f2'); c.s.emit('push25 s4,0\nmov55 s3,a0\nj 0x442f6')   # exact displaced stock prologue


def c_entries(cfg=None):
    return C_ENTRIES + (('gp50_host_parse',) if _parse_stock(cfg) else ())


PRESET_OWN = 'sdk/nds/footswitch_ab/fs_ab_preset_own.c'
# preset_record with stock_in_place: these entries stay ours (fs_ab_preset_own.c); read/migrate/apply revert to stock.
STOCK_IN_PLACE_KEEP = (0x442f2, 0x4468a, 0x49772, 0x4965a)


def _preset_stock(cfg):
    cfg = cfg or {}
    keep = cfg.get('stock_in_place_by_feature', {}).get(NAME, cfg.get('stock_in_place', ()))
    return NAME in cfg.get('stock_in_place_features', ()) and 'preset_record' in keep and 'footswitch_ab_c' in (cfg.get('features') or ())


def restore_inside(cfg=None):
    """Parent hooks inside reverted bodies restored to stock: the MOD055 `12 51` route (own_get handles it first)."""
    return {0x4357a} if _parse_stock(cfg) else set()


def stock_in_place_patches(c):
    out = [(0x43fbc, f'jal {c.labels["gp50_fs_ab_preset_read"]:#x}', 'stored-preset read: A/B footswitch / knob tail decode')] if _preset_stock(c.cfg) else []
    if not _parse_stock(c.cfg): return out
    t = c.labels['own_read_table']
    return out + [(0x43374, f'j {c.labels["gp50_host_parse"]:#x}', 'host parser entry: own commands, then the stock parser'),
            (0x429ce, f'sethi a0,{t >> 12:#x}', 'stock get dispatch: own_read_table (hi)'),
            (0x429d2, f'ori a0,a0,{t & 4095:#x}', 'stock get dispatch: own_read_table (lo)')]


CODE = {'parse_stock': parse_stock, 'preset_stock': preset_stock}
DATA = {}
HOOKS = {}


def patches(c):
    return [(a, f'j {c.labels[f"nds_host_{a:05x}"]:#x}', f'stock entry {a:#x} -> C nds_host_{a:05x} ({ENTRIES[a]})') for a in HOOKED]


def c_sources(cfg=None):
    """Paired capture successor selects one owner; default sources stay unchanged."""
    features = (cfg or {}).get("features") or ()
    if "capture_status_c" not in features:
        return C_SOURCES + ((PARSE_SOURCE,) if _parse_stock(cfg) else ())
    swap = {'sdk/nds/host_layer/own_pedal.c': 'sdk/capture_status/nds_pedal.c'}
    if "footswitch_ab_c" in features:   # A/B footswitches: successor record chain and command owner (region E)
        swap = {'sdk/nds/host_layer/own_pedal.c': 'sdk/nds/footswitch_ab/fs_ab_pedal.c',
                'sdk/nds/host_layer/preset_record.c': 'sdk/nds/footswitch_ab/fs_ab_preset_record.c'}
    out = tuple(swap.get(src, src) for src in C_SOURCES)
    return out + ((PARSE_SOURCE,) if _parse_stock(cfg) else ()) + ((PRESET_OWN,) if _preset_stock(cfg) else ())
