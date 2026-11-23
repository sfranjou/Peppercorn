#ifndef GP50_CAPTURE_CAB_H
#define GP50_CAPTURE_CAB_H
#include <stdint.h>
/* Init-time selected-CAB adapter. The caller owns the same foreground/no-writer
 * transaction as capture lookup, and supplies a 2048-byte private destination.
 * The storage callback must validate live geometry and extent BEFORE copying;
 * it must copy, not lend a mapped-flash pointer. No retained flash references.
 * Disabled CAB is an identity filter. An enabled but unreadable CAB is an error,
 * never silently treated as identity. Stock VTSI does not call this adapter. */
#define GP50_CAPTURE_IR_BYTES 2048u
#define GP50_CAPTURE_IR_COUNT 41u
#define GP50_CAPTURE_CAB_CONFIG_BYTES 0x2e2u
typedef int (*gp50_capture_ir_copy)(void *,uint32_t,uint8_t *,uint32_t);
typedef struct {
 const uint8_t *ir;
 uint32_t bytes;
 uint8_t enabled,ordinal;
} gp50_capture_cab;
static inline int gp50_capture_cab_prepare(gp50_capture_cab *cab,
 const volatile uint8_t *cfg,uint32_t cfg_bytes,uint8_t *storage,
 uint32_t capacity,gp50_capture_ir_copy copy,void *context) {
 *cab=(gp50_capture_cab){0};
 if(!cfg || cfg_bytes<GP50_CAPTURE_CAB_CONFIG_BYTES)return 0;
 /* Exact group-4 ABI: init 0x6584 selects config+0x175; the audio dispatcher
  * uses the working enable mask at +0x188, not the public model-ID array. */
 cab->enabled=(uint8_t)((cfg[0x188]>>4)&1u);
 cab->ordinal=cfg[0x175];
 if(!cab->enabled)return 1;
 if(cab->ordinal>=GP50_CAPTURE_IR_COUNT || !storage ||
    capacity!=GP50_CAPTURE_IR_BYTES || !copy)return 0;
 if(!copy(context,cab->ordinal,storage,capacity))return 0;
 cab->ir=storage;cab->bytes=capacity;return 1;
}
/* A light control reload copies enable bits without re-running init. Ask the
 * foreground scheduler for its normal muted full reload on a topology change.
 * This does no FFT/copy in the audio callback. Preserve tuner/startup requests.
 * Caller serializes the pending-byte read/modify/write with the scheduler.
 * A failed init should not call this: otherwise it could create a reload loop. */
static inline int gp50_capture_cab_request_reload(const gp50_capture_cab *cab,
 volatile uint8_t *cfg,uint32_t cfg_bytes) {
 if(!cfg || cfg_bytes<GP50_CAPTURE_CAB_CONFIG_BYTES)return 0;
 uint8_t enabled=(uint8_t)((cfg[0x188]>>4)&1u);
 if(enabled==cab->enabled && (!enabled || cfg[0x175]==cab->ordinal))return 0;
 if(cfg[0x2e1]>1u)return 0;
 cfg[0x2e1]=2u;return 1;
}
#endif
