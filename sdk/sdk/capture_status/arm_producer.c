#include "arm_producer.h"
static int ready(const gp50_capture_arm *a) {
 return a->ready==GP50_CAPTURE_ARM_READY && a->complement==~GP50_CAPTURE_ARM_READY;
}
static void invalidate_record(gp50_capture_arm *a) {
 a->record=0;a->extent=0;a->record_generation=0;a->fallback=0;
}
static void exhausted(gp50_capture_arm *a) {
 /* Keep exhaustion unavailable until an explicit boot reset; never revive
  * old accepted state by wrapping a generation or reinitializing lazily. */
 a->ready=0;a->complement=0;invalidate_record(a);
}
void gp50_capture_arm_reset(gp50_capture_arm *a) {
 a->ready=0;a->complement=0;invalidate_record(a);a->writers=0;
 gp50_capture_reset(&a->snapshot);
 for(unsigned i=0;i<5;i++)a->reserved[i]=0;
 a->complement=~GP50_CAPTURE_ARM_READY;
 __asm__ volatile("" ::: "memory");
 a->ready=GP50_CAPTURE_ARM_READY;
}
void gp50_capture_arm_startup(gp50_capture_arm *a) {
 /* Caller masks interrupts; an early failure must survive this initialization.
  * Scatter clearing the marker earlier remains an integration limitation. */
 if(a->complement==GP50_CAPTURE_ARM_FAULT) {
  /* The fault already invalidated readiness and record; unavailable APIs
   * do not expose snapshot or reserved storage. */
  a->writers=0;
  return;
 }
 gp50_capture_arm_reset(a);
}
void gp50_capture_arm_copy(const gp50_capture_arm *a,gp50_capture_snapshot *s) {
 if(!ready(a))gp50_capture_reset(s);else *s=a->snapshot;
}
uint32_t gp50_capture_arm_begin(gp50_capture_arm *a,uint8_t slot) {
 if(!ready(a) || a->writers || slot>=GP50_CAPTURE_SLOTS)return 0;
 invalidate_record(a);
 uint32_t gen=gp50_capture_begin(&a->snapshot,slot);
 if(!gen)exhausted(a);
 return gen;
}
int gp50_capture_arm_bind(gp50_capture_arm *a,uint32_t gen,uint32_t pointer,
 const gp50_capture_geometry *b,const gp50_capture_geometry *c) {
 if(!ready(a) || a->writers || !gen || gen!=a->snapshot.generation ||
    a->snapshot.state!=GP50_CAPTURE_LOADING || a->record_generation)return 0;
 uint8_t fallback;
 uint32_t extent=gp50_capture_record_extent(pointer,b,c,1,&fallback);
 if(!extent) {
  gp50_capture_finish(&a->snapshot,gen,GP50_CAPTURE_UNKNOWN,GP50_CAPTURE_REJECTED,GP50_CAPTURE_E_EXTENT,0);
  return 0;
 }
 a->record=pointer;a->extent=extent;a->record_generation=gen;
 /* This flag describes lookup fallback, never inferred from a later magic. */
 a->fallback=fallback;
 return 1;
}
uint32_t gp50_capture_arm_input(const gp50_capture_arm *a,uint32_t pointer,uint32_t *extent) {
 *extent=0;
 if(!ready(a) || a->writers || !pointer || pointer!=a->record ||
    !a->record_generation || a->record_generation!=a->snapshot.generation ||
    a->snapshot.state!=GP50_CAPTURE_LOADING)return 0;
 *extent=a->extent;return a->record_generation;
}
int gp50_capture_arm_finish(gp50_capture_arm *a,uint32_t gen,uint8_t kind,uint8_t state,uint32_t error) {
 if(!ready(a) || a->writers || gen!=a->record_generation)return 0;
 return gp50_capture_finish(&a->snapshot,gen,kind,state,error,(uint8_t)a->fallback);
}
int gp50_capture_arm_bypass(gp50_capture_arm *a,uint32_t gen,uint8_t bypassed) {
 return ready(a) && !a->writers && gp50_capture_bypass(&a->snapshot,gen,bypassed);
}
int gp50_capture_arm_watchdog(gp50_capture_arm *a,uint32_t gen,uint32_t error) {
 return ready(a) && !a->writers && gp50_capture_watchdog(&a->snapshot,gen,error);
}
void gp50_capture_arm_retire(gp50_capture_arm *a) {
 if(!ready(a))return;
 invalidate_record(a);
 if(!gp50_capture_retire(&a->snapshot))exhausted(a);
}
int gp50_capture_arm_write_enter(gp50_capture_arm *a) {
 if(!ready(a) || a->writers==UINT32_MAX)return 0;
 if(!a->writers)gp50_capture_arm_retire(a);
 /* Retire exhaustion prevents future publication. Writer may still perform
  * its normal operation; it must not rely on capture availability. */
 a->writers++;return 1;
}
void gp50_capture_arm_write_leave(gp50_capture_arm *a) {
 if(a->writers)a->writers--;
}

void gp50_capture_arm_write_fault(gp50_capture_arm *a) {
 /* Preserve nesting so each original writer still unwinds normally. Reuse
  * the existing fail-closed publication boundary; no mapped input survives. */
 exhausted(a);
 a->complement=GP50_CAPTURE_ARM_FAULT;
}
