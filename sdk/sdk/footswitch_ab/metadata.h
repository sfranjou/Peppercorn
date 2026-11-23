#ifndef GP50_ASSIGNMENT_METADATA_H
#define GP50_ASSIGNMENT_METADATA_H
#include <stddef.h>
#include "footswitch_ab.h"

/* Standalone GPAM codec. This does not extend any installed flash hook.
 * Caller must perform catalog/range admission before publishing decoded maps.
 * All offsets are within the tail at slot+512, never within stock's 426 bytes. */
enum { GP50_GPAM_V1_BYTES=64, GP50_GPAM_V2_BYTES=64,
       GP50_GPAM_STOCK_BYTES=426 };
typedef struct {
    uint8_t valid, group, parameter, reserved;
    uint32_t model;
} gp50_gpam_knob;
typedef struct {
    gp50_gpam_knob knob[3];
    gp50_fs_ab_binding foot[2];
    uint8_t blocked_mask;
} gp50_gpam_maps;
uint32_t gp50_gpam_crc(const uint8_t *, size_t);
/* Return schema 1/2 on success, zero on refusal; output untouched on refusal.
 * Schema1 migrates the three knob maps and initializes both foot maps empty.
 * Unknown schemas, noncanonical fields and stock-record mismatch are refused. */
int gp50_gpam_decode(const uint8_t *tail, size_t tail_bytes,
                     const uint8_t *stock, size_t stock_bytes,
                     gp50_gpam_maps *output);
/* Canonical schema2 only; capacity >=64. Leaves output unchanged on refusal.
 * Caller owns staging, sector boundaries, preset ownership and serialization. */
int gp50_gpam_encode(uint8_t *tail, size_t capacity,
                     const uint8_t *stock, size_t stock_bytes,
                     const gp50_gpam_maps *maps);
#endif
