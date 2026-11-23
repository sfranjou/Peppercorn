/* Pedal build of assign_percent from firmware/reconstructed/nds/assign_store.c, hard float (stock FPU, fs0..fs5 only);
 * the other functions of that source are renamed here and dropped by --gc-sections (they come from assign_store.c). */
#include "legacy_ui_module.h"
#define assign_crc32 assign_crc32_hf_unused
#define assign_u32 assign_u32_hf_unused
#define assign_preset_read assign_preset_read_hf_unused
#define assign_stage_copy assign_stage_copy_hf_unused
#define assign_commit assign_commit_hf_unused
#include "../own/assign_store.c"
