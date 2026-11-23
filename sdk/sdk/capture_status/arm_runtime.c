#include "arm_runtime.h"
#include "capture_link.h"
#include "arm_private.h"
#include "arm_lifecycle.h"
/* Called with stable foreground request bytes. Ownership is decided before
 * response validity, so malformed schema3 never falls through to stock. */
int gp50_capture_arm_request(gp50_capture_arm *a,const uint8_t *p,uint32_t n,uint8_t out[32]) {
 if(n<8u || p[0]!=0xf0 || p[1]!=0x60 || p[4]!=3 || p[5] || p[6] || p[7])return 0;
 gp50_capture_snapshot s;
 gp50_capture_arm_copy(a,&s);
 return gp50_capture_link_reply(p,n,&s,out)?2:1;
}
#ifndef GP50_CAPTURE_NATIVE_RUNTIME
#define ARM_STATE ((gp50_capture_arm *)GP50_CAPTURE_ARM_BASE)
static uint32_t enter(void) {
 uint32_t p;
 __asm volatile("mrs %0, primask\n cpsid i":"=r"(p)::"memory");return p;
}
static void leave(uint32_t p) {__asm volatile("msr primask, %0"::"r"(p):"memory");}
extern void *gp50_capture_stock_alloc(uint32_t);
extern void gp50_capture_stock_free(void *);
extern uint32_t gp50_capture_stock_lookup(uint32_t);
extern void gp50_stock_reply(const void *,uint32_t);
void gp50_capture_arm_boot(void) {
 uint32_t p=enter();gp50_capture_arm_startup(ARM_STATE);leave(p);
}
void gp50_capture_overlay_call(uint32_t event,gp50_capture_overlay_context *c) {
 uint32_t p=enter();
 if(event==GP50_CAPTURE_COPY_IR || event==GP50_CAPTURE_COPY_RECORD) {
  /* COPY_IR: CAB IR ordinal 0..40 (2048 bytes, areas A/C). COPY_RECORD (2026-11-08 capture pair): user capture
   * slot 0..29 = stored slot 50+n (2696 bytes, area C only), no capture writer active. One shared body keeps the
   * resident inside its reservation. The only destination is a private buffer inside the N->S overlay slot
   * (destination + length <= 0x10008c00, the old IR bound start <= 0x10008400 exactly). Content is validated by
   * the player; this bounds the source and destination under the live storage geometry. */
  const uint32_t rec=event==GP50_CAPTURE_COPY_RECORD,n=rec?GP50_CAPTURE_RECORD_BYTES:2048u;
  uint32_t extent=0,ordinal=c->extent; c->extent=0;
  if(ordinal<(rec?30u:41u) && c->record>=0x10004800u && c->record+n<=0x10008c00u &&
     (rec?ARM_STATE->ready==GP50_CAPTURE_ARM_READY && !ARM_STATE->writers:
      c->generation && gp50_capture_arm_input(ARM_STATE,ARM_STATE->record,&extent)==c->generation)) {
   gp50_capture_geometry b,user;
   gp50_capture_live_geometry((const volatile uint8_t *)0x20001ef4u,
    (const volatile uint8_t *)0x20003778u,(const volatile uint8_t *)0x20002884u,&b,&user);
   /* Reject before lookup if storage geometry is not initialized. Factory
    * table uses A's 2KiB sectors; user lookup may follow C descriptors. */
   const volatile uint32_t *a=(const volatile uint32_t *)0x20002874u;
   uint32_t src=0;
   if(user.bytes && a[0]==0x20001ef4u && a[1]==0x114000u &&
      *(const volatile uint16_t *)(a+2)==2048u)
    src=gp50_capture_stock_lookup(rec?91u+ordinal:ordinal);
   if((!rec && src>=0x116800u && src<=0x120800u && !(src&2047u)) ||
      (src>=0x15b000u && src+n<=0x1d0000u && !(src&4095u))) {
    volatile uint8_t *dst=(volatile uint8_t *)c->record;
    const volatile uint8_t *in=(const volatile uint8_t *)src;
    for(uint32_t i=0;i<n;i++)dst[i]=in[i];
    c->extent=n;
   }
  }
 } else if(event==GP50_CAPTURE_PREPARE)
  gp50_capture_private_prepare(ARM_STATE,c,(uint32_t)c->record,gp50_capture_stock_alloc);
 else {
  gp50_capture_arm_overlay(ARM_STATE,event,c,(uint32_t)c->record);
  if(event==GP50_CAPTURE_COMPLETE)gp50_capture_private_release(c,gp50_capture_stock_free);
 }
 leave(p);
}
int gp50_capture_arm_dispatch(const uint8_t *request,uint32_t n) {
 uint8_t reply[32];uint32_t p=enter();
 int result=gp50_capture_arm_request(ARM_STATE,request,n,reply);
 leave(p);
 /* Stock serializer runs outside mask, matching existing schema2 handling. */
 if(result==2)gp50_stock_reply(reply,32);
 return result!=0;
}
#endif
