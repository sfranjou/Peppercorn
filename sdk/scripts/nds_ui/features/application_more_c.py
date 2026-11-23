"""Further compared stock helpers; existing commands and behavior retained."""
NAME='application_more_c'
REQUIRES=('application_helpers_c','legacy_ui_c')
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
STUDIES=['link_list_allocation', 'link_list_access', 'flash_adapters', 'link_reports', 'power_config', 'flash_selection', 'input_pump', 'input_buttons']
ENTRIES={84644: 'link_list_allocate', 84882: 'link_list_find', 85228: 'link_list_weakest', 85888: 'link_list_copy', 299750: 'drum_queue_read', 299776: 'drum_queue_available', 299794: 'drum_queue_write', 299816: 'drum_queue_space', 300102: 'flash_bank_read', 300132: 'flash_bank_erase', 300164: 'flash_pair_read', 300192: 'flash_pair_erase', 300724: 'flash_catalog_read', 300766: 'flash_catalog_erase', 300804: 'flash_settings_erase', 300822: 'flash_settings_write', 300846: 'flash_table_read', 300880: 'flash_capture_read', 300946: 'flash_settings_read', 301022: 'flash_current_read', 301170: 'flash_identifier_read', 301192: 'flash_signature_copy', 85692: 'link_report_stage', 85300: 'link_discovery_record', 94002: 'power_config_init', 300452: 'flash_records_select', 301906: 'input_encoder_debounce', 302168: 'input_timer_dispatch', 97272: 'input_buttons_update'}
HOOKED=(84644, 84882, 85228, 85300, 85692, 85888, 94002, 97272, 299750, 299776, 299794, 299816, 300102, 300132, 300164, 300192, 300452, 300724, 300766, 300804, 300822, 300846, 300880, 300946, 301022, 301170, 301192, 301906, 302168)
C_SOURCES=('sdk/nds/application_more/link_list.c', 'sdk/nds/application_more/flash_adapters.c', 'sdk/nds/application_more/link_reports.c', 'sdk/nds/application_more/power_config.c', 'sdk/nds/application_more/flash_selection.c', 'sdk/nds/application_more/input_pump.c', 'sdk/nds/application_more/input_buttons.c')
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=("sdk/nds/application_more/link_list.c",)
C_ENTRIES=tuple(f"nds_more_{a:05x}"for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_more_{a:05x}"]:#x}',f'compared application C{a:05x}')for a in HOOKED]
