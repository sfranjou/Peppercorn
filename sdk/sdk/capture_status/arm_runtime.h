#ifndef GP50_CAPTURE_ARM_RUNTIME_H
#define GP50_CAPTURE_ARM_RUNTIME_H
#include "arm_overlay.h"
/* Foreground ARM integration. Snapshot/state access is serialized by the target
 * PRIMASK wrapper; record reads retain the synchronous lookup/init ownership.
 * Link handler returns 0 for other schemas, 1 for owned (even malformed) schema3.
 * It never emits a reply for a malformed owned request. */
int gp50_capture_arm_request(gp50_capture_arm *,const uint8_t *,uint32_t,uint8_t [32]);
void gp50_capture_arm_boot(void);
void gp50_capture_overlay_call(uint32_t,gp50_capture_overlay_context *);
int gp50_capture_arm_dispatch(const uint8_t *,uint32_t);
#endif
