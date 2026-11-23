/* Direct pedal build of the compared application source. Existing UI input entries remain owned by ui_input_c. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define task_flash_ready nds_app_49a6c
#define task_channel_set nds_app_49d52
#define task_queue_read nds_app_49eb8
#define task_queue_available nds_app_49ed4
#define task_queue_write nds_app_49ee8
#define task_queue_space nds_app_49f02
#define task_service_release nds_app_4a094
#include "../../../firmware/reconstructed/nds/task_queue_adapters.c"
