/* Pedal build of firmware/reconstructed/nds/host_parse.c (see host_layer_module.h), with what the parent's hooks inside
 * the replaced bodies did: the read table is ours (stock entries 0..11 from the parent image, 12 = telemetry `host`,
 * 13/14 = `12 70`/`12 71`; MOD055 pointed the sethi/ori pair 0x429ce/0x429d2 at telemetry's 13-entry copy) and the
 * parser routes `12 51` (MOD055 hook 0x4357a, length 2 -> entry 12) and our own commands (own_commands.c). */
#include "host_layer_module.h"
#include "../../../firmware/reconstructed/nds/host_parse.h"
#include "own_commands.h"
extern const uint32_t own_read_table[];
#undef GET_TABLE
#define GET_TABLE ((uint32_t)(uintptr_t)own_read_table)
#define HOST_OWN_SET(sel, args, args_length, status) own_set((sel), (args), (args_length), (status), io)
#define HOST_OWN_GET(sel, length, ctx) own_get((sel), (length), (ctx), io)
#include "../../../firmware/reconstructed/nds/host_parse.c"
