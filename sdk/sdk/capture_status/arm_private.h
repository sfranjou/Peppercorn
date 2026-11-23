#ifndef GP50_CAPTURE_ARM_PRIVATE_H
#define GP50_CAPTURE_ARM_PRIVATE_H
#include "arm_overlay.h"
/* Caller holds the same no-writer/PRIMASK transaction across preflight,
 * allocation and complete byte copy. Allocation failure is a normal rejection.
 * Allocator has no internal locking; target callers keep it under that guard.
 * No claim about flash idle follows from this helper. */
typedef void *(*gp50_capture_alloc)(uint32_t);
typedef void (*gp50_capture_free)(void *);
void gp50_capture_private_prepare(gp50_capture_arm *,
 gp50_capture_overlay_context *,uint32_t address,gp50_capture_alloc);
void gp50_capture_private_release(gp50_capture_overlay_context *,gp50_capture_free);
#endif
