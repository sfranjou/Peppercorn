#ifndef GP50_NDS_ASSIGN_STORE_H
#define GP50_NDS_ASSIGN_STORE_H
#include <stdint.h>
#include "stock_io.h"
/* Knob-assignment persistence (MOD029, assembly work/ui_assignment_v3; design
 * analysis/firmware/ASSIGNMENT_PERSISTENCE_AND_UX.md): three bindings per preset in a 64-byte "GPAM" v1 tail at preset
 * slot + 0x200, guarded by the CRC-32 of the exact 426-byte stock record. Ported to C (NDS_ASM_TO_C_INVENTORY.md). */
#define ASSIGN_STATE 0x2001f3f0u     /* +0 phase ... +32/+48/+64: live bindings {valid, group, parameter, ordinal}; +80 owner preset */
#define ASSIGN_META 0x2001f480u      /* +8 reset mode, +12 root, +16 preset, +24 mapped mask, +28 root seen */
#define ACTIVE_RECORD 0x200106adu    /* the active preset buffer (426-byte stock record) */
#define PRESET_IDS 0x200106d3u       /* active record + 0x26: 10 u32 model public IDs (unaligned) */
#define GPAM_MAGIC 0x4d415047u       /* "GPAM" */
#define GPAM_VERSION 0x00400001u     /* schema 1, 64 bytes */
uint32_t assign_crc32(uint32_t address, uint32_t length, const StockIo *io);   /* 0x16ec00: IEEE CRC-32 */
uint32_t assign_u32(uint32_t address, const StockIo *io);                      /* 0x16ec4a: unaligned little-endian word */
/* 0x16ec74, replaces `jal 0x4972e` at 0x43fbc: read the preset slot; for the active buffer, publish the slot's validated
 * bindings (or none). Returns the stock read result. */
uint32_t assign_preset_read(uint32_t buffer, uint32_t slot, uint32_t length, const StockIo *io);
/* 0x16f900, replaces the memcpy at 0x496ac in stock sector staging: copy, then (426-byte active record) write the tail. */
uint32_t assign_stage_copy(uint32_t destination, uint32_t source, uint32_t length, const StockIo *io);
uint32_t assign_commit(uint32_t context, uint32_t event, const StockIo *io);   /* 0x16eec4: v2 commit + dirty flag */
uint32_t assign_percent(uint32_t minimum, uint32_t maximum, uint32_t current); /* 0x16ef06: float bits -> bar 0..100 */
#endif
