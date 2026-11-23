#ifndef GP50_CAPTURE_ARM_OVERLAY_H
#define GP50_CAPTURE_ARM_OVERLAY_H
#include "arm_producer.h"
/* Successor-only resident/overlay boundary. The eventual linker must bind
 * gp50_capture_overlay_call to the reviewed resident gate. Never ship this
 * overlay against a stock/MOD087 resident. No default address or lazy init. */
enum { GP50_CAPTURE_PREPARE=1, GP50_CAPTURE_COMPLETE=2,
 GP50_CAPTURE_PROCESS=3, GP50_CAPTURE_COPY_IR=4, GP50_CAPTURE_COPY_RECORD=5 };
/* COPY_RECORD (2026-11-08 capture pair): extent in = user slot 0..29 (stored slot 50 + n), record = private
 * 2696-byte destination in the N->S overlay slot; extent out = 2696 when copied, else 0. */
#define GP50_CAPTURE_RECORD_BYTES 2696u
typedef struct {
 uintptr_t record, owned;
 uint32_t generation, extent, error;
 uint8_t kind, state, run, bypassed;
} gp50_capture_overlay_context;
/* Gate serializes snapshot access and proves stable content for init. It is
 * forbidden to call the resident operation with an unbound/translated pointer
 * on target. Native tests explicitly translate a known descriptor address. */
void gp50_capture_overlay_call(uint32_t event,gp50_capture_overlay_context *);
void gp50_capture_arm_overlay(gp50_capture_arm *,uint32_t event,
 gp50_capture_overlay_context *,uint32_t bound_address);
#endif
