/* Native reference driver for the Thumb differential (scripts/verify_tail_doubler.py).
 * argv[1]: scenario A (no adapter), B (granted), C (granted, revoked, regranted).
 * Output lines: "R <block> <hex 512B resident>" whenever resident memory changes
 * before a block, "O <block> <hex float32 x128>" per block, "P <sha-free hex pool
 * checksum words>" at the end. Deterministic input, shared with the Python side. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gp50_resident.h"
static _Alignas(8) unsigned char host_resident[512];
static _Alignas(8) unsigned char host_pool[GP50_RM_BYTES];
static uintptr_t map(uint32_t a) {
 if(a>=GP50_RESIDENT_BASE && a<GP50_RESIDENT_BASE+512u) return (uintptr_t)host_resident+(a-GP50_RESIDENT_BASE);
 return (uintptr_t)host_pool+(a-GP50_RM_BASE);
}
#define GP50_TAIL_PTR(a) map((uint32_t)(a))
#define GP50_NATIVE_TEST
#define GP50_EFFECT_GROUP 6u
#define GP50_SAMPLE_RATE 44100.0f
#include "tail_doubler.c"
static void dump_resident(int block) {
 printf("R %d ",block);for(int i=0;i<512;i++)printf("%02x",host_resident[i]);putchar('\n');
}
static float input(uint32_t t) {
 /* Bursts of a decaying square-ish pattern, then silence; exact in float32. */
 uint32_t phase=t%3000u;
 if(phase>=600u)return 0.0f;
 return ((t/37u)&1u?0.25f:-0.25f)*(float)(600u-phase)*(1.0f/600.0f);
}
int main(int argc,char **argv) {
 char scenario=argc>1?argv[1][0]:'B';
 gp50_resident *r=(gp50_resident *)host_resident;
 gp50_requirements q={GP50_REQ_MAGIC,GP50_REQ_ABI,24,0,2*TAIL_N,4};
 memset(host_pool,0xa5,sizeof host_pool);
 if(scenario=='A'){memset(host_resident,0x3c,sizeof host_resident);}
 else {memset(host_resident,0,sizeof host_resident);gp50_resident_init(r);gp50_resident_load(r,6,&q,1);}
 dump_resident(0);
 float params[8]={60,30,50,1.5f,90,0,0,0};
 tail_doubler_init(params);
 uint8_t on=1;float s[128];
 for(int b=0;b<240;b++) {
  if(scenario=='C' && b==100){gp50_resident_retire_all(r,1);dump_resident(b);}
  if(scenario=='C' && b==150){gp50_resident_load(r,6,&q,1);dump_resident(b);}
  if(b==60)params[1]=70;
  if(b==120){params[1]=25;params[3]=4.0f;}
  if(b==200)params[2]=100;
  on=(uint8_t)!(b>=170 && b<175);
  for(int i=0;i<64;i++)s[2*i]=s[2*i+1]=input((uint32_t)(b*64+i));
  tail_doubler_process(s,64,params,0,&on,0,0);
  printf("O %d ",b);
  for(int i=0;i<128;i++){uint32_t w;memcpy(&w,&s[i],4);printf("%08x",w);}
  putchar('\n');
 }
 uint32_t sum=0,x=0;for(size_t i=0;i<sizeof host_pool;i++){sum=sum*31u+host_pool[i];x^=(uint32_t)host_pool[i]<<(8*(i&3));}
 printf("P %08x %08x\n",sum,x);
 return 0;
}
