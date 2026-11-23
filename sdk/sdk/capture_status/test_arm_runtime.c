#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "arm_runtime.h"
#include "capture_link.h"
int main(void) {
 gp50_capture_arm a;memset(&a,0xa5,sizeof(a));
 uint8_t request[64]={0},reply[32],before[32],unavailable[32];unsigned cases=0;
 assert(gp50_capture_link_request(1,request));
 assert(gp50_capture_arm_request(&a,request,16,reply)==2);
 assert(reply[31]==0 && reply[30]==255 && reply[29]==0);
 memcpy(unavailable,reply,32);cases++;
 gp50_capture_arm_reset(&a);
 uint32_t gen=gp50_capture_arm_begin(&a,3);
 gp50_capture_geometry b={0x122000,0x36000,4096,3};
 assert(gp50_capture_arm_bind(&a,gen,0x125000,&b,0));
 assert(gp50_capture_arm_finish(&a,gen,GP50_CAPTURE_GP5P,GP50_CAPTURE_ACCEPTED,0));
 assert(gp50_capture_arm_request(&a,request,16,reply)==2);
 assert(reply[29]==GP50_CAPTURE_ACCEPTED && reply[30]==3);cases++;
 for(unsigned n=0;n<65;n++) {
  memset(reply,0xa5,32);memcpy(before,reply,32);
  int r=gp50_capture_arm_request(&a,request,n,reply);
  assert(r==(n<8?0:n==16?2:1));
  if(r!=2)assert(!memcmp(before,reply,32));cases++;
 }
 for(unsigned i=0;i<16;i++)for(unsigned bit=0;bit<8;bit++) {
  request[i]^=(uint8_t)(1u<<bit);memset(reply,0xa5,32);memcpy(before,reply,32);
  int r=gp50_capture_arm_request(&a,request,16,reply);
  if(i<2 || (i>=4 && i<8))assert(!r);
  else if(i==2 || i==3 || i>=12)assert(r==1);
  else assert(r==(i==8 && bit==0?1:2)); /* zero refused; nonzero echoed */
  if(r!=2)assert(!memcmp(reply,before,32));
  request[i]^=(uint8_t)(1u<<bit);cases++;
 }
 gp50_capture_arm_retire(&a);assert(gp50_capture_arm_request(&a,request,16,reply)==2);
 assert(reply[29]==GP50_CAPTURE_RETIRED);cases++;
 gp50_capture_arm_write_fault(&a);
 assert(gp50_capture_arm_request(&a,request,16,reply)==2);
 assert(!memcmp(reply,unavailable,32));cases++;
 /* Old results and unmatched writer returns cannot leak retired/accepted state. */
 gp50_capture_arm_write_leave(&a);
 assert(!gp50_capture_arm_finish(&a,gen,GP50_CAPTURE_GP5P,GP50_CAPTURE_ACCEPTED,0));
 assert(gp50_capture_arm_request(&a,request,16,reply)==2);
 assert(!memcmp(reply,unavailable,32));cases++;
 /* Startup after a marked fault must retain canonical unavailable status. */
 a.ready=0;a.complement=0;gp50_capture_arm_write_fault(&a);
 gp50_capture_arm_startup(&a);
 assert(gp50_capture_arm_request(&a,request,16,reply)==2);
 assert(!memcmp(reply,unavailable,32));cases++;
 a.ready=0;a.complement=0;gp50_capture_arm_startup(&a);
 assert(gp50_capture_arm_begin(&a,0));cases++;
 printf("%u ARM schema3 dispatch cases passed\n",cases);
}
