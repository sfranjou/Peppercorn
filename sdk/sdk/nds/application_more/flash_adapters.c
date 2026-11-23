/* Direct build of compared source; normal entry ABI only. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_queue_read nds_more_492e6
#define drum_queue_available nds_more_49300
#define drum_queue_write nds_more_49312
#define drum_queue_space nds_more_49328
#define flash_bank_read nds_more_49446
#define flash_bank_erase nds_more_49464
#define flash_pair_read nds_more_49484
#define flash_pair_erase nds_more_494a0
#define flash_catalog_read nds_more_496b4
#define flash_catalog_erase nds_more_496de
#define flash_settings_erase nds_more_49704
#define flash_settings_write nds_more_49716
#define flash_table_read nds_more_4972e
#define flash_capture_read nds_more_49750
#define flash_settings_read nds_more_49792
#define flash_current_read nds_more_497de
#define flash_identifier_read nds_more_49872
#define flash_signature_copy nds_more_49888
#include "../../../firmware/reconstructed/nds/flash_adapters.c"
