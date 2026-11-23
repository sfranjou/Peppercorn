/* Pedal build of firmware/reconstructed/nds/assign_store.c (see legacy_ui_module.h), soft-float: everything except
 * assign_percent, which comes from assign_percent.c (hard float). This copy of it is renamed and left unreferenced, so
 * --gc-sections drops it; GCC would otherwise spill integers to FPU registers in the flash-path functions. */
#include "legacy_ui_module.h"
#define assign_percent assign_percent_soft_unused
#include "../own/assign_store.c"
