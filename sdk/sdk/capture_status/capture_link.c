#include "capture_link.h"
static void put32(uint8_t *p,uint32_t x) {for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(x>>(8u*i));}
static uint32_t get32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
int gp50_capture_link_request(uint32_t token,uint8_t out[16]) {
 if(!token)return 0;
 put32(out,UINT32_C(0x001060f0));put32(out+4,3);put32(out+8,token);put32(out+12,0);return 1;
}
int gp50_capture_link_reply(const uint8_t *request,uint32_t bytes,
 const gp50_capture_snapshot *s,uint8_t out[32]) {
 if(bytes!=16 || get32(request)!=UINT32_C(0x001060f0) || get32(request+4)!=3 || !get32(request+8) || get32(request+12) || !gp50_capture_valid(s))return 0;
 uint8_t response[32];
 put32(response,UINT32_C(0x002060f0));put32(response+4,3);
 put32(response+8,get32(request+8));put32(response+12,0);
 put32(response+16,s->generation);put32(response+20,s->revision);put32(response+24,s->error);
 response[28]=s->kind;response[29]=s->state;response[30]=s->slot;response[31]=s->flags;
 for(unsigned i=0;i<32;i++)out[i]=response[i];
 return 1;
}
int gp50_capture_link_receive(gp50_capture_cache *c,const uint8_t *reply,uint32_t bytes,uint32_t now) {
 if(bytes!=32 || get32(reply)!=UINT32_C(0x002060f0) || get32(reply+4)!=3 || get32(reply+12))return 0;
 uint32_t token=get32(reply+8);
 gp50_capture_snapshot s={get32(reply+16),get32(reply+20),get32(reply+24),reply[28],reply[29],reply[30],reply[31]};
 if(!token || !c->pending || token!=c->request || !gp50_capture_valid(&s))return 0;
 if(s.state==GP50_CAPTURE_UNAVAILABLE) {
  /* A matching unavailable response invalidates cached success, not a timeout.
   * No producer pointer/error survives. Session resets still require an explicit
   * cache reset; don't infer reboot from a regressing generation. */
  c->snapshot=s;c->pending=0;c->valid=0;c->age_ms=0;c->received_tick=now;return 1;
 }
 return gp50_capture_receive(c,token,&s,now);
}
