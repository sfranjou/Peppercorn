#include "capture_status.h"
static int slot_ok(uint8_t slot) { return slot<GP50_CAPTURE_SLOTS || slot==GP50_CAPTURE_UNKNOWN_SLOT; }
static int supported(uint8_t kind) { return kind>=GP50_CAPTURE_VTSI && kind<=GP50_CAPTURE_GPTC; }
static void put32(uint8_t *p,uint32_t x) { for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(x>>(8u*i)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
void gp50_capture_reset(gp50_capture_snapshot *s) {
 *s=(gp50_capture_snapshot){0,0,0,GP50_CAPTURE_UNKNOWN,GP50_CAPTURE_UNAVAILABLE,GP50_CAPTURE_UNKNOWN_SLOT,0};
}
int gp50_capture_valid(const gp50_capture_snapshot *s) {
 if(s->kind>GP50_CAPTURE_GPTC || s->state>GP50_CAPTURE_RETIRED || !slot_ok(s->slot) || (s->flags&~7u))return 0;
 if(!!(s->flags&GP50_CAPTURE_SLOT_KNOWN)!=(s->slot!=GP50_CAPTURE_UNKNOWN_SLOT))return 0;
 if((s->flags&GP50_CAPTURE_BYPASSED) && s->state!=GP50_CAPTURE_ACCEPTED)return 0;
 if(s->state==GP50_CAPTURE_UNAVAILABLE)
  return !s->generation && !s->revision && !s->error && s->kind==GP50_CAPTURE_UNKNOWN && !s->flags;
 if(!s->generation || !s->revision)return 0;
 if(s->state==GP50_CAPTURE_LOADING || s->state==GP50_CAPTURE_RETIRED)
  return !s->error && s->kind==GP50_CAPTURE_UNKNOWN && !(s->flags&GP50_CAPTURE_FALLBACK) &&
   (s->state!=GP50_CAPTURE_RETIRED || s->slot==GP50_CAPTURE_UNKNOWN_SLOT);
 if(s->state==GP50_CAPTURE_ACCEPTED)return supported(s->kind) && !s->error;
 if(s->state==GP50_CAPTURE_RUNTIME_ERROR)return supported(s->kind) && s->error;
 if(s->state==GP50_CAPTURE_REJECTED)return s->kind!=GP50_CAPTURE_EMPTY && s->error;
 /* Unsupported includes empty content, unknown magic and recognized unsupported versions. */
 return !s->error;
}
uint32_t gp50_capture_begin(gp50_capture_snapshot *s,uint8_t slot) {
 if(!gp50_capture_valid(s) || !slot_ok(slot) || s->generation==UINT32_MAX)return 0;
 uint32_t gen=s->generation+1u;
 *s=(gp50_capture_snapshot){gen,1,0,GP50_CAPTURE_UNKNOWN,GP50_CAPTURE_LOADING,slot,
  slot==GP50_CAPTURE_UNKNOWN_SLOT?0:GP50_CAPTURE_SLOT_KNOWN};
 return gen;
}
uint32_t gp50_capture_retire(gp50_capture_snapshot *s) {
 uint32_t gen=gp50_capture_begin(s,GP50_CAPTURE_UNKNOWN_SLOT);
 if(gen)s->state=GP50_CAPTURE_RETIRED;
 return gen;
}
int gp50_capture_finish(gp50_capture_snapshot *s,uint32_t gen,uint8_t kind,uint8_t state,uint32_t error,uint8_t fallback) {
 if(!gp50_capture_valid(s) || gen!=s->generation || s->state!=GP50_CAPTURE_LOADING ||
  s->revision==UINT32_MAX || fallback>1u ||
  (state!=GP50_CAPTURE_ACCEPTED && state!=GP50_CAPTURE_REJECTED && state!=GP50_CAPTURE_UNSUPPORTED))return 0;
 gp50_capture_snapshot next=*s;
 next.revision++;next.kind=kind;next.state=state;next.error=error;
 if(fallback)next.flags|=GP50_CAPTURE_FALLBACK;
 if(!gp50_capture_valid(&next))return 0;
 *s=next;return 1;
}
int gp50_capture_bypass(gp50_capture_snapshot *s,uint32_t gen,uint8_t bypassed) {
 if(!gp50_capture_valid(s) || !gen || gen!=s->generation || s->state!=GP50_CAPTURE_ACCEPTED || bypassed>1u)return 0;
 if(!!(s->flags&GP50_CAPTURE_BYPASSED)==bypassed)return 1;
 if(s->revision==UINT32_MAX)return 0;
 s->revision++;s->flags=(uint8_t)((s->flags&~GP50_CAPTURE_BYPASSED)|bypassed);return 1;
}
int gp50_capture_watchdog(gp50_capture_snapshot *s,uint32_t gen,uint32_t error) {
 if(!gp50_capture_valid(s) || !gen || gen!=s->generation || s->state!=GP50_CAPTURE_ACCEPTED || !error || s->revision==UINT32_MAX)return 0;
 s->revision++;s->state=GP50_CAPTURE_RUNTIME_ERROR;s->error=error;
 s->flags&=(uint8_t)~GP50_CAPTURE_BYPASSED;return 1;
}
int gp50_capture_encode(const gp50_capture_snapshot *s,uint8_t freshness,uint32_t age,uint8_t out[24]) {
 if(!gp50_capture_valid(s) || freshness>GP50_CAPTURE_STALE)return 0;
 if(freshness==GP50_CAPTURE_NO_SAMPLE) {
  if(s->state!=GP50_CAPTURE_UNAVAILABLE || age!=GP50_CAPTURE_NO_AGE)return 0;
 } else if(s->state==GP50_CAPTURE_UNAVAILABLE || age==GP50_CAPTURE_NO_AGE ||
   (freshness==GP50_CAPTURE_FRESH)!=(age<GP50_CAPTURE_STALE_MS))return 0;
 uint8_t frame[24]={0x12,0x72,1,freshness,s->kind,s->state,s->slot,s->flags};
 put32(frame+8,s->generation);put32(frame+12,s->revision);put32(frame+16,s->error);put32(frame+20,age);
 for(unsigned i=0;i<24;i++)out[i]=frame[i];
 return 1;
}
int gp50_capture_decode(const uint8_t *in,uint32_t bytes,gp50_capture_snapshot *out,uint8_t *freshness,uint32_t *age) {
 if(bytes!=24u || in[0]!=0x12 || in[1]!=0x72 || in[2]!=1)return 0;
 gp50_capture_snapshot s={get32(in+8),get32(in+12),get32(in+16),in[4],in[5],in[6],in[7]};
 uint8_t check[24];uint32_t a=get32(in+20);
 if(!gp50_capture_encode(&s,in[3],a,check))return 0;
 *out=s;*freshness=in[3];*age=a;return 1;
}
void gp50_capture_cache_reset(gp50_capture_cache *c) {
 gp50_capture_reset(&c->snapshot);c->request=0;c->received_tick=0;c->age_ms=0;c->pending=0;c->valid=0;
}
uint32_t gp50_capture_request(gp50_capture_cache *c) {
 if(c->pending || c->request==UINT32_MAX)return 0;
 c->request++;c->pending=1;return c->request;
}
void gp50_capture_cancel(gp50_capture_cache *c,uint32_t request) {
 if(request && request==c->request)c->pending=0;
}
int gp50_capture_receive(gp50_capture_cache *c,uint32_t request,const gp50_capture_snapshot *s,uint32_t now) {
 if(!request || !c->pending || request!=c->request || !gp50_capture_valid(s) || s->state==GP50_CAPTURE_UNAVAILABLE)return 0;
 if(c->valid && (s->generation<c->snapshot.generation ||
  (s->generation==c->snapshot.generation && (s->revision<c->snapshot.revision ||
   (s->revision==c->snapshot.revision && (s->kind!=c->snapshot.kind || s->state!=c->snapshot.state ||
    s->slot!=c->snapshot.slot || s->flags!=c->snapshot.flags || s->error!=c->snapshot.error))))))return 0;
 c->snapshot=*s;c->received_tick=now;c->age_ms=0;c->valid=1;c->pending=0;return 1;
}
int gp50_capture_cached_frame(gp50_capture_cache *c,uint32_t now,uint8_t out[24]) {
 if(!c->valid) {gp50_capture_snapshot empty;gp50_capture_reset(&empty);return gp50_capture_encode(&empty,0,UINT32_MAX,out);}
 /* Age latches stale even across tick wraps. Service at least once per 2^31
  * ms; a larger ambiguous delta conservatively saturates rather than freshens. */
 uint32_t delta=now-c->received_tick, age=c->age_ms;
 c->received_tick=now;
 if(delta>=UINT32_C(0x80000000) || delta>UINT32_C(0x7fffffff)-age)age=UINT32_C(0x7fffffff);
 else age+=delta;
 c->age_ms=age;
 return gp50_capture_encode(&c->snapshot,age<1000u?GP50_CAPTURE_FRESH:GP50_CAPTURE_STALE,age,out);
}
