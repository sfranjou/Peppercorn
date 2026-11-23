/* Direct pedal build of the compared application source. Existing UI input entries remain owned by ui_input_c. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define record_ring_init nds_app_16e14
#define record_ring_push nds_app_16e26
#define record_ring_pop nds_app_16e52
#define history_allocate nds_app_17414
#define history_push nds_app_17462
#define history_pop nds_app_174a8
#define component_record_signature nds_app_17212
#include "../../../firmware/reconstructed/nds/component_buffers.c"
