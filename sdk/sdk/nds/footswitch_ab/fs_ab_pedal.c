/* A/B footswitch successor of sdk/capture_status/nds_pedal.c (host_layer_c source when footswitch_ab_c is enabled;
 * region E): one command/table owner with the capture commands unchanged, plus
 *   `12 74`                 -> 40-byte footswitch assignment frame (schema 1; sdk/footswitch_ab/host.c), or ACK status 1
 *   `11 74` + 18 bytes      -> set/clear destination 3/4, or explicit metadata recovery (destination 255, op 1); ACK 0/1
 *   `11 71`                 -> refused (status 1) while the current preset's assignment metadata is damaged (save barrier)
 * and capability bit 3 (footswitch assignment) in `12 70`. analysis/firmware/OWN_HOST_COMMANDS.md, web/gp50/footswitch_ab.mjs. */
#include "../host_layer/host_layer_module.h"
#include "host_layer_table.h"
#include "fs_ab_target.h"
#ifdef GP50_COMPONENTS
#include "../components/components_host.h"
#define OWN_COMPONENT_FEATURE (1u << 8)
#else
#define OWN_COMPONENT_FEATURE 0u
#endif
#ifdef GP50_FEATURE_STOCK_GR_METER
#define OWN_STOCK_GR_FEATURE (1u << 10)
#else
#define OWN_STOCK_GR_FEATURE 0u
#endif
#ifdef GP50_FEATURE_AUTO_WAH
#define OWN_EXP_AUTO_ENGAGE ((1u << 11) | (1u << 12))
#else
#define OWN_EXP_AUTO_ENGAGE 0u
#endif
#define GP50_CAPTURE_NATIVE_COMMANDS 1
#ifdef GP50_ASSIGNMENT_MENU
#define OWN_DRUM_FEATURE (1u << 7)
#else
#define OWN_DRUM_FEATURE 0u
#endif
#define OWN_FEATURES (OWN_FEATURE_LOAD | OWN_FEATURE_GPTC | OWN_FEATURE_KNOB_ASSIGN | OWN_FEATURE_TAP_SAFE | (1u << 6) | OWN_EXP_AUTO_ENGAGE \
                      | OWN_FEATURE_FOOTSWITCH_ASSIGN | OWN_DRUM_FEATURE | OWN_COMPONENT_FEATURE | OWN_FEATURE_GPTS | OWN_STOCK_GR_FEATURE | OWN_FEATURE_TWO_CURVE_ONLY)
#define own_get gp50_own_get_base
#define own_set gp50_own_set_base
#include "../host_layer/own_commands.c"
#undef own_get
#undef own_set
#define own_get gp50_capture_own_get
#include "../../capture_status/nds_commands.c"
#undef own_get

#if defined(GP50_ASSIGNMENT_MENU) && !defined(GP50_FEATURE_DRUM_CONTROL)   /* else the SDK feature drum_control owns 75 */
#include "../own/drum_host.c"
#endif
#define FS_AB_FRAME 40u

uint32_t own_get(uint32_t sel, uint32_t length, uint32_t ctx, const StockIo *io) {
    #ifdef GP50_COMPONENTS
    if(gp50_component_host_get(sel,length,ctx,io)) return 1;
    #endif
    #if defined(GP50_ASSIGNMENT_MENU) && !defined(GP50_FEATURE_DRUM_CONTROL)
    if(sel==0x75) return drum_host_get(length,ctx,io);
    #endif
    if (sel != 0x74) return gp50_capture_own_get(sel, length, ctx, io);
    if (length != 2) return 1;
    LOCAL_BUFFER(io, f, FS_AB_FRAME);
    uint32_t n = gp50_fs_ab_read_frame((uint8_t *)(uintptr_t)f);
    if (!n) { IO_W8(io, f, 0x14); IO_W8(io, f + 1, 0x08); IO_W8(io, f + 2, 1); n = 3; }   /* not readable now: refusal */
    STOCK_CALL(io, FRAME_SEND, f, n, ctx);
    return 1;
}

uint32_t own_set(uint32_t sel, uint32_t args, uint32_t args_length, uint32_t *status, const StockIo *io) {
    #ifdef GP50_COMPONENTS
    if(gp50_component_host_set(sel,args,args_length,status,io)) return 1;
    #endif
    #if defined(GP50_ASSIGNMENT_MENU) && !defined(GP50_FEATURE_DRUM_CONTROL)
    if(sel==0x75) return drum_host_set(args,args_length,status,io);
    #endif
    if (sel == 0x71 && gp50_fs_ab_metadata_fault()) { *status = 1; return 1; }
    if (sel != 0x74) return gp50_own_set_base(sel, args, args_length, status, io);
    uint8_t m[20];
    *status = 1;
    if (args_length != 18) return 1;
    m[0] = 0x11; m[1] = 0x74;
    for (uint32_t i = 0; i < 18; i++) m[2 + i] = IO_R8(io, args + i);
    *status = gp50_fs_ab_command(m, 20);
    return 1;
}

void host(void *host_ctx);
const uint32_t own_read_table[15] = {HOST_READ_TABLE_PARENT,
 (uint32_t)(uintptr_t)host, (uint32_t)(uintptr_t)own_identity,
 (uint32_t)(uintptr_t)own_assign_read};
