#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gp50_capture_cab.h"
static uint8_t source[2048];static unsigned calls;static int fail;
static int copy(void *ctx,uint32_t ordinal,uint8_t *dst,uint32_t bytes) {
 assert(ctx==source && ordinal<41 && bytes==2048);calls++;
 if(fail)return 0;
 memcpy(dst,ctx,bytes);return 1;
}
int main(void) {
 uint8_t cfg[GP50_CAPTURE_CAB_CONFIG_BYTES]={0},buf[2048];gp50_capture_cab cab;
 unsigned cases=0;
 for(unsigned i=0;i<2048;i++)source[i]=(uint8_t)i;
 assert(gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,0,0,0,0));
 assert(!cab.ir && !cab.bytes && !calls);cases++;
 cfg[0x188]=16;
 for(unsigned id=0;id<41;id++) {
  cfg[0x175]=(uint8_t)id;
  assert(gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,buf,sizeof buf,copy,source));
  assert(cab.enabled && cab.ordinal==id && cab.ir==buf && cab.bytes==2048);
  assert(!memcmp(buf,source,2048));cases++;
 }
 /* Caller can discard/change source immediately after the snapshot. */
 source[2047]^=1;assert(buf[2047]!=source[2047]);source[2047]^=1;cases++;
 for(unsigned id=41;id<256;id++) {
  cfg[0x175]=(uint8_t)id;unsigned before=calls;
  assert(!gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,buf,sizeof buf,copy,source));
  assert(!cab.ir && !cab.bytes && calls==before);cases++;
 }
 cfg[0x175]=0;fail=1;
 assert(!gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,buf,sizeof buf,copy,source));
 assert(!cab.ir && !cab.bytes);fail=0;cases++;
 assert(!gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,buf,2047,copy,source));cases++;
 assert(!gp50_capture_cab_prepare(&cab,cfg,sizeof cfg-1,buf,2048,copy,source));cases++;
 assert(!gp50_capture_cab_prepare(&cab,0,sizeof cfg,buf,2048,copy,source));cases++;
 assert(gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,buf,2048,copy,source));
 for(unsigned pending=0;pending<256;pending++) {
  cfg[0x2e1]=(uint8_t)pending;
  assert(!gp50_capture_cab_request_reload(&cab,cfg,sizeof cfg));cases++;
  cfg[0x188]=0;
  assert(gp50_capture_cab_request_reload(&cab,cfg,sizeof cfg)==(pending<2));
  assert(cfg[0x2e1]==(pending<2?2:pending));cfg[0x188]=16;cases++;
 }
 cfg[0x175]=1;cfg[0x2e1]=1;
 assert(gp50_capture_cab_request_reload(&cab,cfg,sizeof cfg) && cfg[0x2e1]==2);cases++;
 cfg[0x188]=0;cfg[0x175]=255;
 assert(gp50_capture_cab_prepare(&cab,cfg,sizeof cfg,0,0,0,0));
 assert(!gp50_capture_cab_request_reload(&cab,cfg,sizeof cfg));cases++;
 printf("%u selected-CAB adapter cases passed\n",cases);
}
