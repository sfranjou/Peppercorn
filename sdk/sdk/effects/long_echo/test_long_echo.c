/* Native tests: Long Echo against a real gp50_resident adapter in host memory
 * mapped at the target addresses, plus no-adapter / stale-heap / revocation cases. */
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
#define GP50_EFFECT_GROUP 7u
#include <stdint.h>
#define GP50_SAMPLE_RATE 44100.0f
#define GP50_INIT
#define GP50_PROCESS
#include "long_echo.c"

static gp50_resident *res(void){return (gp50_resident *)host_resident;}
static float params[5]={35,450,40,60,100};
static uint8_t on=1;
/* Run an impulse and return the index of the first nonzero sample after start. */
static uint32_t first_echo(uint32_t limit,float *amplitude) {
 float s[128];uint32_t t=0;
 for(uint32_t b=0;b*64<limit;b++){
  for(int i=0;i<128;i++)s[i]=0; if(b==0)s[0]=s[1]=.5f;
  long_echo_process(s,64,params,0,&on,0,0);
  for(uint32_t i=0;i<64;i++,t++) if(t>0 && fabsf(s[2*i])>1e-4f){*amplitude=s[2*i];return t;}
 }
 return 0;
}
int main(void) {
 gp50_requirements q={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,2*TAIL_N,4};
 float amp=0;uint32_t t;
 /* 1. No adapter: random-looking heap bytes, even a view that looks granted. */
 memset(host_resident,0x3c,sizeof host_resident);
 gp50_lease_view *fake=(gp50_lease_view *)(host_resident+GP50_RESIDENT_VIEW_OFFSET+16*7);
 *fake=(gp50_lease_view){GP50_RM_BASE,2*TAIL_N,9,GP50_REQ_ABI,GP50_LEASE_GRANTED,0,0};
 memset(host_pool,0xa5,sizeof host_pool);
 long_echo_init(params);assert(!state.using_tail && state.capacity==FALLBACK_N);
 t=first_echo(20000,&amp);printf("fallback echo %u amp %f\n",t,amp);assert(t==FALLBACK_N-2u);
 for(size_t i=0;i<sizeof host_pool;i++)assert(host_pool[i]==0xa5);
 /* 2. Adapter present, lease granted: exact delay, pool used by halfword line. */
 memset(host_resident,0,sizeof host_resident);gp50_resident_init(res());
 assert(gp50_resident_load(res(),7,&q,1)==GP50_RES_OK && res()->view[7].state==GP50_LEASE_GRANTED);
 long_echo_init(params);assert(state.using_tail && state.capacity==TAIL_N);
 t=first_echo(30000,&amp);assert(t==19845u);
 assert(fabsf(amp-.35f*.5f)<.01f); /* mix * impulse, Q15 */
 params[1]=1800;long_echo_init(params);t=first_echo(80000,&amp);assert(t==79380u-2u);
 /* 3. Feedback decays and stays bounded for a sustained loud input. */
 params[1]=100;params[2]=95;long_echo_init(params);
 float s[128],peak=0;
 for(int b=0;b<4000;b++){for(int i=0;i<128;i++)s[i]=(b<2000)?((i/2)%2?1.f:-1.f):0;
  long_echo_process(s,64,params,0,&on,0,0);for(int i=0;i<128;i++){assert(isfinite(s[i]));if(fabsf(s[i])>peak)peak=fabsf(s[i]);}}
 assert(peak<8.f);
 /* 4. Bypass leaves samples untouched. */
 on=0;for(int i=0;i<128;i++)s[i]=(float)i;long_echo_process(s,64,params,0,&on,0,0);
 for(int i=0;i<128;i++)assert(s[i]==(float)i);on=1;
 /* 5. Revocation: tuner retire-all; next block uses fallback, pool untouched afterwards. */
 params[1]=450;params[2]=40;long_echo_init(params);assert(state.using_tail);
 assert(gp50_resident_retire_all(res(),1)==GP50_RES_OK);
 static unsigned char snapshot[GP50_RM_BYTES];memcpy(snapshot,host_pool,sizeof host_pool);
 for(int b=0;b<500;b++){for(int i=0;i<128;i++)s[i]=.1f;long_echo_process(s,64,params,0,&on,0,0);}
 assert(!state.using_tail && state.capacity==FALLBACK_N && !memcmp(snapshot,host_pool,sizeof host_pool));
 /* 6. Replacement with a new generation also revokes. */
 assert(gp50_resident_load(res(),7,&q,1)==GP50_RES_OK);long_echo_init(params);assert(state.using_tail);
 assert(gp50_resident_load(res(),7,&q,1)==GP50_RES_OK);
 for(int i=0;i<128;i++)s[i]=0;long_echo_process(s,64,params,0,&on,0,0);assert(!state.using_tail);
 /* 7. Too-small grant falls back. */
 gp50_requirements small=q;small.tail_bytes=1024;
 assert(gp50_resident_load(res(),7,&small,1)==GP50_RES_OK);long_echo_init(params);assert(!state.using_tail);
 /* 8. NaN/huge input and parameter sweeps stay finite. */
 assert(gp50_resident_load(res(),7,&q,1)==GP50_RES_OK);long_echo_init(params);
 for(int b=0;b<3000;b++){params[1]=(float)(b*7%2000);params[0]=(float)(b%101);params[3]=(float)(b*3%101);
  for(int i=0;i<128;i++)s[i]=(i==5)?NAN:(i==9?1e9f:.3f);long_echo_process(s,64,params,0,&on,0,0);
  for(int i=0;i<128;i++)assert(isfinite(s[i])&&fabsf(s[i])<20.f);}
 puts("PASS: fallback without adapter/stale heap, exact tail delays 19845/79378, bounded feedback, bypass, revocation, replacement, small grant, sweeps");
 return 0;
}
