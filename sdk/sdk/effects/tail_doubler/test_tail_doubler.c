/* Native tests: Tail Doubler with a real resident adapter in host memory, and the
 * two-client pool (Long Echo group 7 + Tail Doubler group 6) in both load orders. */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gp50_resident.h"
static _Alignas(8) unsigned char host_resident[512];
static _Alignas(8) unsigned char host_pool[GP50_RM_BYTES];
static uintptr_t map(uint32_t a) {
 if(a>=GP50_RESIDENT_BASE && a<GP50_RESIDENT_BASE+512u) return (uintptr_t)host_resident+(a-GP50_RESIDENT_BASE);
 assert(a>=GP50_RM_BASE && a<GP50_RM_END);
 return (uintptr_t)host_pool+(a-GP50_RM_BASE);
}
#define GP50_TAIL_PTR(a) map((uint32_t)(a))
#define GP50_NATIVE_TEST
#define GP50_EFFECT_GROUP 6u
#define GP50_SAMPLE_RATE 44100.0f
#include "tail_doubler.c"
static gp50_resident *res(void){return (gp50_resident *)host_resident;}
static float params[5]={100,80,0,1,100};
static uint8_t on=1;
static uint32_t first_echo(uint32_t limit) {
 float s[128];uint32_t t=0;
 for(uint32_t b=0;b*64<limit;b++){
  for(int i=0;i<128;i++)s[i]=0; if(b==0)s[0]=s[1]=.5f;
  tail_doubler_process(s,64,params,0,&on,0,0);
  for(uint32_t i=0;i<64;i++,t++) if(t>0 && fabsf(s[2*i])>1e-4f)return t;
 }
 return 0;
}
int main(void) {
 gp50_requirements dbl={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,2*TAIL_N,4},echo={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,158760,4};
 /* No adapter: fallback, Delay clamped inside 1,024 samples. */
 memset(host_resident,0x3c,sizeof host_resident);memset(host_pool,0xa5,sizeof host_pool);
 tail_doubler_init(params);assert(!state.using_tail && state.capacity==FALLBACK_N);
 uint32_t t=first_echo(4000);printf("fallback echo %u\n",t);assert(t>0 && t<FALLBACK_N);
 for(size_t i=0;i<sizeof host_pool;i++)assert(host_pool[i]==0xa5);
 /* Two clients, both orders: both granted, disjoint, whole pool fits. */
 for(int order=0;order<2;order++){
  memset(host_resident,0,sizeof host_resident);gp50_resident_init(res());
  if(order){assert(gp50_resident_load(res(),6,&dbl,1)==GP50_RES_OK);assert(gp50_resident_load(res(),7,&echo,1)==GP50_RES_OK);}
  else{assert(gp50_resident_load(res(),7,&echo,1)==GP50_RES_OK);assert(gp50_resident_load(res(),6,&dbl,1)==GP50_RES_OK);}
  gp50_lease_view *v6=&res()->view[6],*v7=&res()->view[7];
  assert(v6->state==GP50_LEASE_GRANTED && v7->state==GP50_LEASE_GRANTED);
  assert(v6->address+v6->bytes<=v7->address || v7->address+v7->bytes<=v6->address);
  assert(v6->address+v6->bytes<=GP50_RM_END && v7->address+v7->bytes<=GP50_RM_END);
  printf("order %d: dbl %#x+%u echo %#x+%u\n",order,v6->address,v6->bytes,v7->address,v7->bytes);
  tail_doubler_init(params);assert(state.using_tail && state.capacity==TAIL_N);
  t=first_echo(8000);assert(t==3528u); /* 80 ms, depth 0 */
 }
 /* Its writes stay inside its lease: compare echo region before/after a run. */
 memset(host_pool,0xa5,sizeof host_pool);
 gp50_lease_view *v7=&res()->view[7];
 tail_doubler_init(params);float s[128];
 for(int b=0;b<400;b++){for(int i=0;i<128;i++)s[i]=.3f;tail_doubler_process(s,64,params,0,&on,0,0);}
 for(uint32_t a=v7->address;a<v7->address+v7->bytes;a++)assert(host_pool[a-GP50_RM_BASE]==0xa5);
 /* Revocation by its own group's replacement: falls back next block. */
 assert(gp50_resident_load(res(),6,&dbl,1)==GP50_RES_OK);
 for(int i=0;i<128;i++)s[i]=0;tail_doubler_process(s,64,params,0,&on,0,0);assert(!state.using_tail);
 /* Third grant for the same group while Long Echo holds most of the pool still fits (old retired first). */
 assert(res()->view[6].state==GP50_LEASE_GRANTED);
 /* Oversize request is denied FULL while Long Echo is resident. */
 gp50_requirements big=dbl;big.tail_bytes=8192;
 assert(gp50_resident_load(res(),6,&big,1)==GP50_RES_OK && res()->view[6].state==GP50_LEASE_DENIED && res()->view[6].reason==GP50_DENY_FULL);
 tail_doubler_init(params);assert(!state.using_tail);
 /* Bypass untouched; modulation sweeps finite and bounded. */
 assert(gp50_resident_load(res(),6,&dbl,1)==GP50_RES_OK);tail_doubler_init(params);assert(state.using_tail);
 on=0;for(int i=0;i<128;i++)s[i]=(float)i;tail_doubler_process(s,64,params,0,&on,0,0);for(int i=0;i<128;i++)assert(s[i]==(float)i);on=1;
 for(int b=0;b<4000;b++){params[1]=(float)(b%90);params[2]=(float)(b*7%101);params[3]=(float)(b%60)*.1f;params[0]=(float)(b%101);
  for(int i=0;i<128;i++)s[i]=(i==3)?NAN:.4f*sinf((float)(b*64+i)*.05f);tail_doubler_process(s,64,params,0,&on,0,0);
  for(int i=0;i<128;i++)assert(isfinite(s[i])&&fabsf(s[i])<3.f);}
 puts("PASS: fallback clamp, two clients both orders disjoint, exact 80 ms, lease isolation, revocation, FULL denial, bypass, sweeps");
 return 0;
}
