/* Successor wrapper around the frozen v6 implementation. New status comes
 * from its actual private init/validator/watchdog result, never from a generic
 * DSP cell interpretation. Resident lookup must bind the readable extent first.
 * An unbound/short record is passed as NULL to v6, retaining dry-safe init.
 * This source requires a new resident gate; not compatible with MOD087. */
#define ns_capture_init capture_inner_init
#define ns_capture_process capture_inner_process
#include "../ns_capture_v6/ns_capture.c"
#undef ns_capture_init
#undef ns_capture_process
#include "../../capture_status/arm_overlay.h"
static uint32_t capture_generation;

GP50_INIT void ns_capture_init(const float *p,const uint8_t *const *content) {
 gp50_capture_overlay_context c={0};
 c.record=(uintptr_t)(content?*content:0);
 gp50_capture_overlay_call(GP50_CAPTURE_PREPARE,&c);
 capture_generation=c.generation;
 const uint8_t *safe=c.run?(const uint8_t *)c.record:0;
 capture_inner_init(p,&safe);
 if(c.run) {
  c.state=valid?GP50_CAPTURE_ACCEPTED:GP50_CAPTURE_REJECTED;
  /* NS_UERR is initialized by install_user on BOTH success and failure.
   * Other modes own this cell as VLEVEL; never read it for those modes. */
  c.error=valid?0:c.kind==GP50_CAPTURE_GP5P?
   *(volatile uint32_t *)NS_CELL(NS_UERR):GP50_CAPTURE_E_FORMAT;
 }
 gp50_capture_overlay_call(GP50_CAPTURE_COMPLETE,&c);
}
GP50_PROCESS void ns_capture_process(float *samples,uint32_t frames,const float *p,
 uint32_t r3,const uint8_t *enable,const uint32_t *beat,void *r6) {
 uint32_t was_valid=valid;
 capture_inner_process(samples,frames,p,r3,enable,beat,r6);
 gp50_capture_overlay_context c={0};
 c.generation=capture_generation;c.bypassed=(uint8_t)!*enable;
 /* v6's sole valid -> invalid processing transition is its watchdog.
  * Report once, using the actual branch outcome, not a stale UERR value. */
 if(was_valid && !valid && (umode || gmode))c.error=0xffu;
 gp50_capture_overlay_call(GP50_CAPTURE_PROCESS,&c);
}

/* Freestanding AEABI clear used by Clang for the initialized context. Volatile
 * stores keep the implementation independent of compiler-generated libc calls. */
void __aeabi_memclr4(void *pointer,unsigned bytes) {
 volatile unsigned char *p=pointer;
 while(bytes--)*p++=0;
}
