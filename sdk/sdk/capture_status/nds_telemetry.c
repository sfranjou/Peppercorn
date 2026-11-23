#ifdef GP50_COMPONENTS
#include "../nds/components/component.h"
#endif
/* Successor integration of capture into the existing shared telemetry owner.
 * Included base source is frozen MOD087 telemetry, with private renamed entry
 * points. No second queue owner: pending/cadence/TX/queue gates are shared.
 * Requires explicit startup reset and 64 newly reserved bytes. Not installed.
 */
#include "nds_transport.h"
#include "capture_link.h"
#ifndef GP50_CAPTURE_NATIVE_TRANSPORT
#define service gp50_telemetry_service_base
#define gui gp50_telemetry_gui_base
#define nds_receive gp50_telemetry_receive_base
#include "../nds/ui/telemetry.c"
#undef service
#undef gui
#undef nds_receive
#endif
#ifndef CAPTURE_STATE
#define CAPTURE_STATE ((gp50_capture_nds_state *)GP50_CAPTURE_NDS_BASE)
#endif
#ifndef GP50_CAPTURE_FRAME_ADDRESS
#define GP50_CAPTURE_FRAME_ADDRESS(a) ((uintptr_t)(a))
#endif
static int capture_ready(void) {
 return CAPTURE_STATE->ready==GP50_CAPTURE_NDS_READY &&
  CAPTURE_STATE->complement==~GP50_CAPTURE_NDS_READY;
}
void gp50_capture_transport_reset(void) {
 gp50_capture_nds_state *c=CAPTURE_STATE;
 c->ready=0;c->complement=0;
 gp50_capture_cache_reset(&c->cache);
 c->sent_tick=0;c->requested=0;c->last_capture=0;c->timed_out=0;
 c->reserved[0]=0;c->reserved[1]=0;
 c->complement=~GP50_CAPTURE_NDS_READY;
 __asm__ volatile("" ::: "memory");
 c->ready=GP50_CAPTURE_NDS_READY;
}
void gp50_capture_refresh(void) {
 irq_guard_enter();
 if(capture_ready())CAPTURE_STATE->requested=1;
 irq_guard_leave();
}
int gp50_capture_display_frame(uint8_t out[GP50_CAPTURE_REPLY_BYTES]) {
 int result=0;
 irq_guard_enter();
 if(capture_ready()) {
  result=gp50_capture_cached_frame(&CAPTURE_STATE->cache,W32(GP50_TICK_COUNTER),out);
  CAPTURE_STATE->requested=1;
 }
 irq_guard_leave();
 return result;
}
void service(void) {
 irq_guard_enter();
 gp50_capture_nds_state *c=CAPTURE_STATE;
 uint32_t now=W32(GP50_TICK_COUNTER);
 if(!capture_ready())goto base;
 if(c->cache.pending && now-c->sent_tick>=1000u) {
  gp50_capture_cancel(&c->cache,c->cache.request);c->timed_out=1;
 }
 /* Base owns expiration of its own pending fields. Let it run even while
  * blocked by old pending; it cannot admit while these fields remain set. */
 if(ST[S_PENDING] || LEG[L_PENDING])goto base;
 if(c->cache.pending)goto out;
 /* Alternate a capture operation and the existing fair legacy/schema2 pair.
  * Preserve the base's LAST_KIND boolean; never store schema3 in that field. */
 if(!c->requested || (c->last_capture && (ST[S_REQUESTED] || LEG[L_REQUESTED])))goto base;
 if(ST[S_ADMIT_VALID] && now-ST[S_ADMIT_TICK]<(ST[S_FAST]?100u:500u))goto out;
 const volatile uint8_t *tx=(const volatile uint8_t *)GP50_LINK_TX_STATE;
 if(tx[16])goto out;
 const volatile uint16_t *q=(const volatile uint16_t *)GP50_LINK_QUEUE_COUNTERS;
 if(q[0]!=q[1] || q[0]>=12u)goto out;
 uint32_t token=gp50_capture_request(&c->cache);
 if(!token)goto out;
 /* Stack bytes are copied synchronously by stock link_queue_produce, as in
  * the base telemetry producer. Failed enqueue consumes the token safely. */
 uint32_t message[4];
 gp50_capture_link_request(token,(uint8_t *)message);
 if(link_queue_produce(1,message,16,0)) {
  gp50_capture_cancel(&c->cache,token);goto out;
 }
 c->sent_tick=now;c->requested=0;c->timed_out=0;c->last_capture=1;
 ST[S_ADMIT_TICK]=now;ST[S_ADMIT_VALID]=1;
 goto out;
base:
 /* Do not hold a nested irq guard around the original base function. The
  * GUI/service caller is the sole producer; receive never queues messages. */
 if(capture_ready() && c->cache.pending)goto out;
 uint32_t old_valid=ST[S_ADMIT_VALID],old_tick=ST[S_ADMIT_TICK];
 irq_guard_leave();
 gp50_telemetry_service_base();
 irq_guard_enter();
 if(capture_ready() && ST[S_ADMIT_VALID] &&
  (!old_valid || old_tick!=ST[S_ADMIT_TICK]))c->last_capture=0;
out:
 irq_guard_leave();
}
int gui(void) {
 int result=gui_link_receive_tick();
 service();
 #ifdef GP50_COMPONENTS
 gp50_components_tick();
 #endif
 return result;
}
void nds_receive(uint32_t count) {
 if(count!=36u) {gp50_telemetry_receive_base(count);return;}
 const volatile uint8_t *b=(const volatile uint8_t *)GP50_LINK_RX_FRAME;
 static const uint8_t head[7]={36,0,1,0xf0,0x60,32,0};
 for(uint32_t i=0;i<7;i++)if(b[1+i]!=head[i])return;
 /* Copy under guard; rx frame is caller-owned for this synchronous callback. */
 irq_guard_enter();
 if(!capture_ready() || !CAPTURE_STATE->cache.pending)goto out;
 const volatile uint8_t *tx=(const volatile uint8_t *)GP50_LINK_TX_STATE;
 if(!tx[16] || *(const volatile uint16_t *)(tx+10)!=20u)goto out;
 uint32_t frame=*(const volatile uint32_t *)(tx+4);
 if(!frame)goto out;
 const volatile uint8_t *outer=(const volatile uint8_t *)GP50_CAPTURE_FRAME_ADDRESS(frame);
 if(outer[1]!=20u || outer[2] || outer[3]!=1u)goto out;
 const volatile uint32_t *request=(const volatile uint32_t *)(outer+4);
 if(request[0]!=UINT32_C(0x001060f0) || request[1]!=3u ||
  request[2]!=CAPTURE_STATE->cache.request || request[3])goto out;
 uint8_t reply[32];
 for(uint32_t i=0;i<32;i++)reply[i]=b[4+i];
 if(gp50_capture_link_receive(&CAPTURE_STATE->cache,reply,32,W32(GP50_TICK_COUNTER))) {
  CAPTURE_STATE->timed_out=0;link_release_owned();
 }
out:
 irq_guard_leave();
}
