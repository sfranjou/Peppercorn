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


def patches(c):
    return []
