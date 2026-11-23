#ifndef GP50_CAPTURE_ARM_PRODUCER_H
#define GP50_CAPTURE_ARM_PRODUCER_H
#include "capture_record.h"
#include <stddef.h>
#define GP50_CAPTURE_ARM_BASE UINT32_C(0x20003ce8)
#define GP50_CAPTURE_ARM_END UINT32_C(0x20003d28)
#define GP50_CAPTURE_ARM_READY UINT32_C(0x43504131)
#define GP50_CAPTURE_ARM_FAULT UINT32_C(0x4641554c)
typedef struct {
 gp50_capture_snapshot snapshot;
 uint32_t record, extent, record_generation;
 uint32_t ready, complement, writers, fallback;
 uint32_t reserved[5];
} gp50_capture_arm;
/* arm_hooks.S clears these two words before C startup. Pin the actual
 * addresses so a C layout edit cannot silently leave readiness uncleared. */
_Static_assert(GP50_CAPTURE_ARM_BASE+offsetof(gp50_capture_arm,ready)==0x20003d04u,"early ready address");
_Static_assert(GP50_CAPTURE_ARM_BASE+offsetof(gp50_capture_arm,complement)==0x20003d08u,"early complement address");
_Static_assert(sizeof(gp50_capture_arm)==64,"ARM capture reservation");
_Static_assert(GP50_CAPTURE_ARM_BASE+sizeof(gp50_capture_arm)==GP50_CAPTURE_ARM_END,"ARM capture end");
/* Successor-only. All accesses require caller serialization: preserve PRIMASK,
 * mask interrupts, invoke the operation, restore PRIMASK. No allocation or
 * payload read here. The loader must retire BEFORE replacement, then bind the
 * actual lookup result. Boot reset precedes every foreground reader/producer.
 * No capture API may be invoked from an interrupt before reset initialization.
 * Every flash writer must bracket its whole erase/program/reload transaction.
 * These caller contracts are integration gates, not established by this file. */
/* Explicit unconditional reset for controlled initialization/tests. Startup
 * instead preserves a fault marker written since the early clear. */
void gp50_capture_arm_reset(gp50_capture_arm *);
void gp50_capture_arm_startup(gp50_capture_arm *);
void gp50_capture_arm_copy(const gp50_capture_arm *,gp50_capture_snapshot *);
uint32_t gp50_capture_arm_begin(gp50_capture_arm *,uint8_t slot);
int gp50_capture_arm_bind(gp50_capture_arm *,uint32_t generation,uint32_t pointer,
 const gp50_capture_geometry *factory,const gp50_capture_geometry *user);
uint32_t gp50_capture_arm_input(const gp50_capture_arm *,uint32_t pointer,uint32_t *extent);
int gp50_capture_arm_finish(gp50_capture_arm *,uint32_t generation,
 uint8_t kind,uint8_t state,uint32_t error);
int gp50_capture_arm_bypass(gp50_capture_arm *,uint32_t generation,uint8_t bypassed);
int gp50_capture_arm_watchdog(gp50_capture_arm *,uint32_t generation,uint32_t error);
void gp50_capture_arm_retire(gp50_capture_arm *);
int gp50_capture_arm_write_enter(gp50_capture_arm *);
void gp50_capture_arm_write_leave(gp50_capture_arm *);
/* Caller reports a known failed/uncertain flash operation while serialized.
 * Leaves capture unavailable until explicit boot initialization. Writer leave,
 * a later lookup or successful write must never reopen it. Not an idle test. */
void gp50_capture_arm_write_fault(gp50_capture_arm *);
#endif
