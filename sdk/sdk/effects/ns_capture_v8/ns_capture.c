/* Resident-integrated two-format player. Must be linked with the matching
 * capture resident and v7 staged secondary, never installed independently. */
#define ns_capture_init capture_unused_init
#define ns_capture_process capture_inner_process
#include "../ns_capture_v7/ns_capture.c"
#undef ns_capture_init
#undef ns_capture_process
#include "../../capture_status/arm_overlay.h"
#include "gp50_capture_cab.h"
#ifndef GP50_CAPTURE_WORKING_CONFIG
#define GP50_CAPTURE_WORKING_CONFIG ((volatile uint8_t *)0x20001bf4u)
#endif
static uint8_t cab_ir[2048];
static gp50_capture_cab cab;
static uint32_t capture_generation;
/* Capture pair (2026-11-08, analysis/tone_capture/TWO_CAPTURES_20261108.md). The DST slot's "Capture" effect
 * (sdk/effects/dst_capture) names a user capture slot; its audio runs here, before the main capture. The DST
 * program is recognised by its signature in DSP program memory (rewritten by the stock loader on every DST load);
 * enable and Slot come from the stock working config (stable across reloads, unlike the effect's own cells). */
#define DST_SIG0 0x7d064443u
#define DST_SIG1 0x7d065054u
#define DST_EXIT 0xa0080500u
static uint8_t pair_buf[GP50_CAPTURE_RECORD_BYTES];
/* N->S parameter 8 = this float pattern: the main chip keeps N->S loaded only for a DST capture while the user's N->S
 * block is off (admission table v7, sdk/nds/ui/refuse.c gp50_link_filter) -> no main capture. */
#define MAIN_OFF_BITS 0xc2f6e979u
static uint32_t main_off;
static uint32_t main_off_of(const float *p) { union { float f; uint32_t u; } v = { .f = p[7] }; return v.u == MAIN_OFF_BITS; }
static uint32_t dst_request;        /* requested at init: 0 none, else slot 1..30 */
static uint32_t dst_requested(void) {
 const volatile uint32_t *pm=(const volatile uint32_t *)NS_PROG(0u);
 const volatile uint8_t *cfg=GP50_CAPTURE_WORKING_CONFIG;
 if(pm[6]!=DST_SIG0||pm[7]!=DST_SIG1||pm[8]!=DST_EXIT||!((cfg[0x188]>>2)&1u))return 0;
 float slot=*(const volatile float *)(cfg+0x1e0u);       /* DST working parameter 0 (C+0x1a0+32*2) */
 if(!tc_finite(slot)||slot<0.5f||slot>30.5f)return 0;
 return (uint32_t)(slot+0.5f);
}
static int copy_selected(void *context,uint32_t ordinal,uint8_t *destination,uint32_t bytes) {
 (void)context;
 gp50_capture_overlay_context c={0};
 if(bytes!=2048u)return 0;
 c.generation=capture_generation;c.record=(uintptr_t)destination;c.extent=ordinal;
 gp50_capture_overlay_call(GP50_CAPTURE_COPY_IR,&c);
 return c.extent==bytes;
}
GP50_INIT void ns_capture_init(const float *p,const uint8_t *const *content) {
 gp50_capture_overlay_context c={0};
 c.record=(uintptr_t)(content?*content:0);
 gp50_capture_overlay_call(GP50_CAPTURE_PREPARE,&c);
 capture_generation=c.generation;
 main_off=main_off_of(p);
 const uint8_t *safe=c.run && !main_off?(const uint8_t *)c.record:0;
 int ok=1;
 cab=(gp50_capture_cab){0};
 if(c.run && !main_off && c.kind==GP50_CAPTURE_GPTC)
  ok=gp50_capture_cab_prepare(&cab,GP50_CAPTURE_WORKING_CONFIG,
   GP50_CAPTURE_CAB_CONFIG_BYTES,cab_ir,sizeof cab_ir,copy_selected,0);
 /* A DST capture disables the cab IR: the cab selection is still recorded (reload watch), its
  * IR and level are not applied, so an unreadable cab does not reject the main capture then. The second record
  * is copied by the resident (area C, live geometry). */
 dst_request=dst_requested();
 if(!ok && !dst_request)safe=0;
 const uint8_t *second=0;
 if(dst_request) {
  gp50_capture_overlay_context r={0};
  r.record=(uintptr_t)pair_buf;r.extent=dst_request-1u;
  gp50_capture_overlay_call(GP50_CAPTURE_COPY_RECORD,&r);
  if(r.extent==GP50_CAPTURE_RECORD_BYTES)second=pair_buf;
  ns_capture_init_pair(p,&safe,0,0,second);
 } else
 ns_capture_init_selected(p,&safe,cab.ir,cab.bytes);
 if(c.run) {
  c.state=valid?GP50_CAPTURE_ACCEPTED:GP50_CAPTURE_REJECTED;
  c.error=valid?0:GP50_CAPTURE_E_FORMAT;
 }
 gp50_capture_overlay_call(GP50_CAPTURE_COMPLETE,&c);
}
GP50_PROCESS void ns_capture_process(float *samples,uint32_t frames,const float *p,
 uint32_t r3,const uint8_t *enable,const uint32_t *beat,void *r6) {
 uint32_t was_valid=valid;
 /* DST Capture working parameters 1..5 (Gain, VOL, Bass, Mid, Treble; parameter 0 = Slot at +0x1e0). */
 dst_tone=dst_request?(const volatile float *)(GP50_CAPTURE_WORKING_CONFIG+0x1e4u):0;
 capture_inner_process(samples,frames,p,r3,enable,beat,r6);
 gp50_capture_overlay_context c={0};
 c.generation=capture_generation;c.bypassed=(uint8_t)!*enable;
 if(was_valid && !valid && gmode)c.error=0xffu;
 gp50_capture_overlay_call(GP50_CAPTURE_PROCESS,&c);
 if(valid && gmode) {
  if(cab.enabled && !dst_request) {
   float level=*(volatile float *)(GP50_CAPTURE_WORKING_CONFIG+0x220u);
   *NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)*=tc_finite(level)?clampf(level,0,100)*0.01f:0.0f;
  }
#ifndef GP50_NATIVE_TEST
  uint32_t mask;
  __asm volatile("mrs %0, primask\n cpsid i":"=r"(mask)::"memory");
#endif
  /* While a DST capture is requested the cab is not used; its watch would loop in pre-only mode (no cab recorded).
   * Deselecting the DST capture reloads through the DST watch below, which then records the cab again. */
  if(!dst_request)gp50_capture_cab_request_reload(&cab,GP50_CAPTURE_WORKING_CONFIG,GP50_CAPTURE_CAB_CONFIG_BYTES);
#ifndef GP50_NATIVE_TEST
  __asm volatile("msr primask, %0"::"r"(mask):"memory");
#endif
 }
 /* DST capture selection changed since init (selected, deselected, Slot, enable): ask for the normal muted full
  * reload, also when this init installed nothing (pre-only needs it). Compared with the request recorded at
  * init, not with success, so a failing slot cannot cause a reload loop. */
 if(dst_requested()!=dst_request || main_off_of(p)!=main_off) {
#ifndef GP50_NATIVE_TEST
  uint32_t mask;
  __asm volatile("mrs %0, primask\n cpsid i":"=r"(mask)::"memory");
#endif
  volatile uint8_t *cfg=GP50_CAPTURE_WORKING_CONFIG;
  if(cfg[0x2e1]<=1u)cfg[0x2e1]=2u;
#ifndef GP50_NATIVE_TEST
  __asm volatile("msr primask, %0"::"r"(mask):"memory");
#endif
 }
}
void __aeabi_memclr4(void *pointer,unsigned bytes) {
 volatile unsigned char *p=pointer;while(bytes--)*p++=0;
}
