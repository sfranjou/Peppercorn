"""A/B parameter footswitches (toggle between two chosen values). Components:
sdk/footswitch_ab (policy, host 11/12 74, schema-2 GPAM metadata, persistence, stock adapter), built for the pedal through
sdk/nds/footswitch_ab. Code and rodata go to region E (cfg region_e_code). Wiring (cfg c_defines GP50_FS_AB=1): host_layer_c
swaps in sdk/nds/footswitch_ab/fs_ab_preset_record.c and fs_ab_pedal.c, application_bulk's press calls gp50_fs_ab_press,
capture_status_c's startup bridge calls gp50_fs_ab_reset and the segment state grows to 272 bytes."""
NAME = 'footswitch_ab_c'
REQUIRES = ('host_layer_c', 'capture_status_c', 'application_bulk_c')   # record chain + commands, startup bridge, press path
CONFLICTS = ()
ORACLES = ()
CASE_KINDS = ()
C_SOURCES = ('sdk/nds/footswitch_ab/fs_ab_footswitch_ab.c', 'sdk/nds/footswitch_ab/fs_ab_host.c', 'sdk/nds/footswitch_ab/fs_ab_metadata.c', 'sdk/nds/footswitch_ab/fs_ab_persistence.c', 'sdk/nds/footswitch_ab/fs_ab_endpoint.c', 'sdk/nds/footswitch_ab/fs_ab_stock_adapter.c', 'sdk/nds/footswitch_ab/fs_ab_target.c', 'sdk/nds/footswitch_ab/fs_ab_ui.c', 'sdk/nds/footswitch_ab/fs_ab_value.c')
C_HARD_FLOAT = True
C_HARD_FLOAT_SOURCES = ('sdk/nds/footswitch_ab/fs_ab_endpoint.c', 'sdk/nds/footswitch_ab/fs_ab_stock_adapter.c', 'sdk/nds/footswitch_ab/fs_ab_value.c')
C_ENTRIES = ('gp50_fs_ab_reset', 'gp50_fs_ab_preset_read', 'gp50_fs_ab_active_replaced', 'gp50_fs_ab_stage_record',
             'gp50_fs_ab_press', 'gp50_fs_ab_metadata_fault', 'gp50_fs_ab_home', 'gp50_fs_ab_reset_press', 'gp50_fs_ab_editor_foot', 'gp50_fs_ab_read_frame', 'gp50_fs_ab_command',
             'gp50_fs_ab_host_read', 'gp50_fs_ab_host_set', 'gp50_fs_ab_host_recover', 'gp50_fs_ab_load', 'gp50_fs_ab_save',
             'gp50_fs_ab_stage', 'gp50_fs_ab_stock_press')
CODE = {}
DATA = {}
HOOKS = {}


def c_entries(cfg):
    return C_ENTRIES + (('gp50_fs_ab_led_mode',)
                        if 'GP50_FEATURE_FOOTSWITCH_AB=1' in (cfg or {}).get('c_defines', ()) else ())


def patches(c):
    from ..stock_in_place import bulk_stems
    if ('GP50_FEATURE_FOOTSWITCH_AB=1' not in c.cfg.get('c_defines', ()) or
            'ui_footswitch' not in bulk_stems(c.cfg)):
        return []
    # These reads supply the stock LED renderer in Stomp mode. The public
    # stock accessor at 0x4748a remains an unmodified read of switch config.
    sites = [(0x47474, '49fff249', 'press')]
    if 'userdata_apply' in bulk_stems(c.cfg):
        sites += [(0x4728c, '49fff33d', 'preset apply A'), (0x472a2, '49fff332', 'preset apply B'),
                  (0x474c8, '49fff21f', 'mode entry A'), (0x474d0, '49fff21b', 'mode entry B'),
                  (0x47534, '49fff1e9', 'refresh A'), (0x4753c, '49fff1e5', 'refresh B')]
    for site, raw, why in sites:
        offset = site - 0x10000
        if c.parent_b[offset:offset + 4] != bytes.fromhex(raw):
            raise ValueError(f'stock footswitch LED mode call preimage differs: {site:#x}')
    return [(site, f'jal {c.labels["gp50_fs_ab_led_mode"]:#x}', f'Stomp {why}: render A/B endpoint')
            for site, _, why in sites]
