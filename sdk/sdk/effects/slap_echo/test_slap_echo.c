/* Native: Slap Echo granted with Tail Doubler resident, DENIED FULL with Long Echo. */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gp50_resident.h"
static _Alignas(8) unsigned char host_resident[512];
static _Alignas(8) unsigned char host_pool[GP50_RM_BYTES];
static uintptr_t map(uint32_t a){
 if(a>=GP50_RESIDENT_BASE&&a<GP50_RESIDENT_BASE+512u)return (uintptr_t)host_resident+(a-GP50_RESIDENT_BASE);
 assert(a>=GP50_RM_BASE&&a<GP50_RM_END);return (uintptr_t)host_pool+(a-GP50_RM_BASE);}
#define GP50_TAIL_PTR(a) map((uint32_t)(a))
#define GP50_NATIVE_TEST
#define GP50_EFFECT_GROUP 1u
#define GP50_SAMPLE_RATE 44100.0f
#include "slap_echo.c"
static gp50_resident *res(void){return (gp50_resident *)host_resident;}
static float params[5]={100,180,0,100,100};static uint8_t on=1;
static uint32_t first_echo(void){float s[128];uint32_t t=0;
 for(int b=0;b<200;b++){for(int i=0;i<128;i++)s[i]=0;if(!b)s[0]=s[1]=.5f;long_echo_process(s,64,params,0,&on,0,0);
  for(int i=0;i<64;i++,t++)if(t&&fabsf(s[2*i])>1e-4f)return t;}return 0;}
int main(void){
 gp50_requirements slap={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,2*TAIL_N,4},dbl={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,7680,4},echo={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,158760,4};
 memset(host_resident,0,512);gp50_resident_init(res());
 assert(gp50_resident_load(res(),6,&dbl,1)==GP50_RES_OK&&gp50_resident_load(res(),1,&slap,1)==GP50_RES_OK);
 assert(res()->view[1].state==GP50_LEASE_GRANTED);long_echo_init(params);assert(state.using_tail);
 uint32_t t=first_echo();printf("granted echo %u cap %u\n",t,state.capacity);assert(t==7937u||t==7938u);  /* 180 ms (7937.9995 in float32) */
 assert(gp50_resident_load(res(),7,&echo,1)==GP50_RES_OK&&res()->view[7].state==GP50_LEASE_DENIED); /* echo cannot fit now */
 /* Order Long Echo first: Slap Echo denied FULL, falls back to 46 ms clamp. */
 memset(host_resident,0,512);gp50_resident_init(res());
 assert(gp50_resident_load(res(),7,&echo,1)==GP50_RES_OK&&gp50_resident_load(res(),6,&dbl,1)==GP50_RES_OK);
 assert(gp50_resident_load(res(),1,&slap,1)==GP50_RES_OK&&res()->view[1].state==GP50_LEASE_DENIED&&res()->view[1].reason==GP50_DENY_FULL);
 long_echo_init(params);assert(!state.using_tail&&state.capacity==FALLBACK_N);t=first_echo();assert(t==FALLBACK_N-2u);
 printf("PASS: Slap Echo granted 180 ms beside Doubler; DENIED FULL beside Long Echo+Doubler -> fallback %u\n",t);return 0;}
