/* Shared prelude of the pedal builds of the legacy UI features (code room step 1, MOD055; analysis/firmware/NDS_CODE_ROOM.md,
 * NDS_ASM_TO_C_INVENTORY.md): MOD026 editor assignment, MOD029 home bars / reset mode / GPAM store, MOD027 Wah auto,
 * MOD028 title meter. The compared sources (firmware/reconstructed/nds, written against stock_io.h) are compiled with plain
 * loads/stores and direct calls (GP50_CATALOG_DIRECT). The readable sources call the routines that were still assembly in
 * MOD054 by their MOD054 address; here those constants resolve at compile time to the C functions (or to the four
 * prologue-replay stubs, asm labels of the feature legacy_ui_c), so the sources stay byte-for-byte the compared ones.
 * Every entry is noinline: stock code, the window tables and the image proof (scripts/verify_nds_generic_image.py
 * --remap) reach each one as a real function at its own address. */
#ifndef GP50_LEGACY_UI_MODULE_H
#define GP50_LEGACY_UI_MODULE_H
#define GP50_CATALOG_DIRECT 1
/* No switch jump tables: GCC places them inside .text, which the C disassembly round-trip gate (tier a) refuses. */
#pragma GCC optimize("no-jump-tables")
#include "../own/stock_io.h"
#include "../own/wah_auto.h"
#include "../own/assign_store.h"
#include "../own/assign_editor.h"
#include "../own/assign_home.h"
#include "../own/assign_map.h"
#include "../own/meter_home.h"
#ifdef GP50_ASSIGNMENT_MENU
#include "../own/assignment_menu.h"
#endif
#define NOINLINE __attribute__((noinline))
NOINLINE void wah_name(uint32_t group, uint32_t parameter, uint32_t buffer, uint32_t length, const StockIo *io);
NOINLINE uint32_t wah_poll(const StockIo *io);
NOINLINE void wah_policy(const StockIo *io);
NOINLINE uint32_t assign_crc32(uint32_t address, uint32_t length, const StockIo *io);
NOINLINE uint32_t assign_u32(uint32_t address, const StockIo *io);
NOINLINE uint32_t assign_preset_read(uint32_t buffer, uint32_t slot, uint32_t length, const StockIo *io);
NOINLINE uint32_t assign_stage_copy(uint32_t destination, uint32_t source, uint32_t length, const StockIo *io);
NOINLINE uint32_t assign_commit(uint32_t context, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_percent(uint32_t minimum, uint32_t maximum, uint32_t current);
NOINLINE uint32_t assign_set_text(uint32_t label, uint32_t text, const StockIo *io);
NOINLINE uint32_t assign_restore(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_render(uint32_t ctx, uint32_t prompt, const StockIo *io);
NOINLINE uint32_t assign_render_current(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_editor_hold(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_editor_back(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_editor_drum(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_editor_encoder(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_para(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_page(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_title_restore(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_reset_prompt(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_bars(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_hold(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_drum(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_back(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_home_encoder(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_tick(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_publish(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_valid_map(uint32_t knob, const StockIo *io);
NOINLINE uint32_t assign_home_knob(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_home_refresh(uint32_t ctx, const StockIo *io);
NOINLINE uint32_t assign_editor_tick(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t assign_home_tick(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t meter_tick(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t meter_drum(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t meter_back(uint32_t ctx, uint32_t event, const StockIo *io);
NOINLINE uint32_t meter_restore(uint32_t ctx, const StockIo *io);
/* Prologue-replay stubs (asm sections of scripts/nds_ui/features/legacy_ui_c.py): enter the stock window ticks mid-body. */
uint32_t legacy_editor_tick_stock(uint32_t ctx, uint32_t event);   /* MOD054 0x16e9ca -> stock 0x1d2cc */
uint32_t legacy_home_tick_stock(uint32_t ctx, uint32_t event);     /* MOD054 0x16ea12 -> stock 0x224f6 */
/* A non-constant target (METER_REFRESH = nds_refresh2, which returns int) is passed through an empty asm so GCC does
 * not reject the call through the unprototyped word-calling type; the call itself is the same jral. */
static inline uintptr_t gp50_target(uintptr_t a) { __asm__("" : "+r"(a)); return a; }
/* MOD056+ (legacy_ui_config.h, generated by legacy_ui_c.py): the "preset modified" call 0x43d52 of the assignment
 * (editor commit, home reset) goes through own_assign_modified, which makes the same call and then sends the `12 71`
 * change notification (sdk/nds/host_layer/own_commands.c). */
#include "legacy_ui_config.h"
#if LEGACY_ASSIGN_NOTIFY
uint32_t own_assign_modified(uint32_t value, const StockIo *io);
#define GP50_ASSIGN_MODIFIED(a) ((a) == 0x43d52u ? (uintptr_t)own_assign_modified : (uintptr_t)(a))
#else
#define GP50_ASSIGN_MODIFIED(a) ((uintptr_t)(a))
#endif
/* MOD054 address of a routine that was still assembly -> its replacement (folded at compile time; any other address is
 * called as is). */
#define GP50_LEGACY(a) (__builtin_constant_p(a) ? ( \
    (a) == 0x16e558u ? (uintptr_t)assign_publish : (a) == 0x16e52cu ? (uintptr_t)assign_set_text : \
    (a) == 0x16e630u ? (uintptr_t)assign_valid_map : (a) == 0x16e6feu ? (uintptr_t)assign_home_knob : \
    (a) == 0x16f400u ? (uintptr_t)meter_tick : (a) == 0x16f43cu ? (uintptr_t)meter_drum : \
    (a) == 0x16f4a8u ? (uintptr_t)meter_back : (a) == 0x16f514u ? (uintptr_t)meter_restore : \
    (a) == 0x16e9cau ? (uintptr_t)legacy_editor_tick_stock : (a) == 0x16ea12u ? (uintptr_t)legacy_home_tick_stock : \
    GP50_ASSIGN_MODIFIED(a)) : gp50_target((uintptr_t)(a)))
/* Float result bits (assign_bars' three getters): moved to a core register right after the call, so no FPU register is
 * live across the next call (GCC would otherwise keep them in fs12+, which the builder refuses). */
static inline uint32_t gp50_call_rf2(uint32_t address, uint32_t a0, uint32_t a1) {
    union { float f; uint32_t u; } x = {.f = ((float (*)(uint32_t, uint32_t))(uintptr_t)address)(a0, a1)};
    uint32_t u = x.u; __asm__("" : "+r"(u)); return u;
}
#undef STOCK_CALL_RF2
#define STOCK_CALL_RF2(io, address, a0, a1) ((void)(io), gp50_call_rf2((address), (a0), (a1)))
#undef STOCK_CALL
#define STOCK_CALL(io, address, ...) ((void)(io), ((stock_fn_t)GP50_LEGACY(address))(__VA_ARGS__))
#endif
