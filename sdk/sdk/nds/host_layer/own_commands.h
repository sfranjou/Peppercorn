#ifndef GP50_OWN_COMMANDS_H
#define GP50_OWN_COMMANDS_H
#include <stdint.h>
#include "../own/stock_io.h"
/* Our own host commands (own_commands.c; analysis/firmware/OWN_HOST_COMMANDS.md). */
#define ASSIGN_STATE 0x2001f3f0u       /* knob-assignment binding table (firmware/reconstructed/nds/assign_store.h) */
#define OWN_PRESET_IDS 0x200106d3u     /* active record + 0x26: 10 u32 model public IDs (unaligned) */
#define OWN_VERSION_TEXT 0x140f34u     /* version text in flash (scripts/ui_theme.py, 8 bytes of room) */
#define OWN_PROTOCOL 1u                /* `12 70` protocol version */
#define OWN_FEATURE_LOAD (1u << 0)     /* `12 50` load meter / `12 51` telemetry */
#define OWN_FEATURE_GPTC (1u << 1)     /* compact tone captures (GPTC records over stock `11 25`/`11 27`) */
#define OWN_FEATURE_GPTS (1u << 9)     /* two-curve tone captures (GPTC v2 records, same messages), 2026-11-21 */
#define OWN_FEATURE_TWO_CURVE_ONLY (1u << 13)   /* MOD160: both capture slots play GPTC v2 only; GPTC v1 records are refused */
#define OWN_FEATURE_KNOB_ASSIGN (1u << 2)   /* knob assignment + `12 71` / `11 71` dest 0-2 */
#define OWN_FEATURE_FOOTSWITCH_ASSIGN (1u << 3)   /* footswitch assignment, `11 71` dest 3-4 (not yet) */
#define OWN_FEATURE_USER_PROGRAMS (1u << 4)       /* user programs (GP5P) (not yet) */
#ifdef GP50_TAP_SAFE_HOST
#define OWN_FEATURE_TAP_SAFE (1u << 5)
#else
#define OWN_FEATURE_TAP_SAFE 0u
#endif
#ifndef OWN_FEATURES
#define OWN_FEATURES (OWN_FEATURE_LOAD | OWN_FEATURE_GPTC | OWN_FEATURE_KNOB_ASSIGN | OWN_FEATURE_TAP_SAFE)
#endif
#define OWN_IDENTITY_FRAME 23u         /* 12 70 proto version[16] features32 */
#define OWN_ASSIGN_FRAME 28u           /* 12 71 n + 3 x 8 (room for the frame of 3 + 8 n) */
#define OWN_INDEX_TELEMETRY 12u        /* read-table entries after the 12 stock ones */
#define OWN_INDEX_IDENTITY 13u
#define OWN_INDEX_ASSIGN 14u
uint32_t own_assign_frame(uint32_t f, const StockIo *io);
uint32_t own_identity(uint32_t ctx, const StockIo *io);
uint32_t own_assign_read(uint32_t ctx, const StockIo *io);
uint32_t own_assign_notify(const StockIo *io);
uint32_t own_assign_modified(uint32_t value, const StockIo *io);
uint32_t own_assign_set(uint32_t args, uint32_t args_length, const StockIo *io);
uint32_t own_get(uint32_t sel, uint32_t length, uint32_t ctx, const StockIo *io);
uint32_t own_set(uint32_t sel, uint32_t args, uint32_t args_length, uint32_t *status, const StockIo *io);
#endif
