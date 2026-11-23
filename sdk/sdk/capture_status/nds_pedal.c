/* Capture-enabled successor of own_pedal.c; one command/table owner. */
#include "../nds/host_layer/host_layer_module.h"
#include "host_layer_table.h"
#include "nds_commands.c"
void host(void *host_ctx);
const uint32_t own_read_table[15] = {HOST_READ_TABLE_PARENT,
 (uint32_t)(uintptr_t)host, (uint32_t)(uintptr_t)own_identity,
 (uint32_t)(uintptr_t)own_assign_read};
