/* Small sanitizer and mutation-sensitivity lifecycle test. No device access. */
#include <assert.h>
#include <string.h>
#include "capture_status.h"
#include "capture_link.h"
#include "capture_text.h"
/* Normal exit status also makes deliberate corruption controls bounded. */
#undef assert
#define assert(x) do { if(!(x)) return 23; } while(0)
int main(void) {
 gp50_capture_snapshot s,old;gp50_capture_reset(&s);
 uint32_t stale=gp50_capture_begin(&s,1),gen=gp50_capture_begin(&s,2);
 old=s;assert(!gp50_capture_finish(&s,stale,5,2,0,0));assert(!memcmp(&s,&old,sizeof s));
 assert(gp50_capture_finish(&s,gen,5,2,0,0));
 assert(gp50_capture_watchdog(&s,gen,0xff000001));assert(s.error==0xff000001);
 assert(!gp50_capture_bypass(&s,gen,0));
 gen=gp50_capture_begin(&s,3);assert(!s.error && s.kind==0);
 assert(gp50_capture_finish(&s,gen,5,2,0,1));
 gp50_capture_cache c;gp50_capture_cache_reset(&c);
 uint32_t token=gp50_capture_request(&c);assert(token && !gp50_capture_request(&c));
 uint8_t req[16],rep[32],host[24];
 assert(gp50_capture_link_request(token,req));assert(gp50_capture_link_reply(req,16,&s,rep));
 rep[8]^=1;assert(!gp50_capture_link_receive(&c,rep,32,0xfffffff0u));rep[8]^=1;
 rep[12]=1;assert(!gp50_capture_link_receive(&c,rep,32,0xfffffff0u));rep[12]=0;
 assert(gp50_capture_link_receive(&c,rep,32,0xfffffff0u));
 assert(!gp50_capture_link_receive(&c,rep,32,0xfffffff0u));
 assert(gp50_capture_cached_frame(&c,0x10,host));assert(host[3]==1 && host[20]==32);
 assert(gp50_capture_cached_frame(&c,0x3d8,host));assert(host[3]==2);
 assert(gp50_capture_cached_frame(&c,0x800003d8,host));assert(host[3]==2);
 assert(gp50_capture_cached_frame(&c,0x3d8,host));assert(host[3]==2);
 for(unsigned capacity=0;capacity<64;capacity++) {
  char text[66];memset(text,'X',sizeof text);gp50_capture_text(&s,1,text,capacity);
  assert(text[capacity]=='X');if(capacity)assert(memchr(text,0,capacity));
 }
 s.generation=UINT32_MAX;old=s;assert(!gp50_capture_begin(&s,0));assert(!memcmp(&s,&old,sizeof s));
 return 0;
}
