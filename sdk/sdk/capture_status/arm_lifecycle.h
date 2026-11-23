#ifndef GP50_CAPTURE_ARM_LIFECYCLE_H
#define GP50_CAPTURE_ARM_LIFECYCLE_H
#include "arm_producer.h"
/* Fixed RAM objects only; byte loads avoid host/target alignment differences.
 * Never follows an object-supplied pointer. A mismatch rejects that area. */
void gp50_capture_live_geometry(const volatile uint8_t flash[12],
 const volatile uint8_t factory[16],const volatile uint8_t user[36],
 gp50_capture_geometry *,gp50_capture_geometry *);
#ifndef GP50_CAPTURE_NATIVE_LIFECYCLE
uint32_t gp50_capture_lookup_call(uint32_t id,uint32_t group);
void gp50_capture_retire_group(uint32_t group);
void gp50_capture_retire_all(void);
void gp50_capture_writer_enter(void);
void gp50_capture_writer_leave(void);
#endif
#endif
