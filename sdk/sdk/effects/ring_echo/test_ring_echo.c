/* Native: Ring Echo echoes at the set time from the looper RAM when the looper is empty,
 * falls back when it is busy, never touches the ring then, and restarts empty after. */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static uint8_t obj[0x40];static int16_t ring[441024];static int ring_ok=1;
static uintptr_t map(uint32_t a){
 if(a>=0x20003a4cu&&a<0x20003a8cu)return (uintptr_t)obj+(a-0x20003a4cu);
 assert(ring_ok&&a>=0x29000000u&&a<0x29000000u+2u*441024u);return (uintptr_t)ring+(a-0x29000000u);}
#define GP50_TAIL_PTR(a) map((uint32_t)(a))
#define GP50_NATIVE_TEST
#define GP50_SAMPLE_RATE 44100.0f
#include "ring_echo.c"
static float buf[128];static const uint8_t on=1;
static float run_impulse_find_echo(float *p,int blocks){
 int first=-1;
 for(int b=0;b<blocks;b++){
  for(int f=0;f<64;f++)buf[2*f]=buf[2*f+1]=(b==0&&f==0)?1.0f:0.0f;
  ring_echo_process(buf,64,p,0,&on,0,0);
  for(int f=0;f<64;f++)if(b*64+f>0&&first<0&&fabsf(buf[2*f])>0.2f)first=b*64+f;
 }
 return (float)first;
}
int main(void){
 uint32_t v[2]={0x29000000u,441024u};memcpy(obj+0x28,v,8);
 for(int i=0;i<441024;i++)ring[i]=(int16_t)((uint32_t)i*7919u);       /* garbage must never be heard */
 float p[8]={100,5000,0,100,100,0,0,0};
 ring_echo_init(p);
 /* glide from the fallback start to 5000 ms: run until settled, then measure a fresh impulse */
 for(int b=0;b<6000;b++){memset(buf,0,sizeof buf);ring_echo_process(buf,64,p,0,&on,0,0);}
 assert(state.using_ring==1);
 float t=run_impulse_find_echo(p,3600);
 printf("echo at %.0f samples (want %.0f)\n",t,5000*44.1);
 assert(fabsf(t-220500.0f)<=2.0f);
 /* looper starts recording: ring must not be touched; the effect falls back */
 obj[1]=4;ring_ok=0;
 for(int b=0;b<200;b++){memset(buf,0,sizeof buf);ring_echo_process(buf,64,p,0,&on,0,0);}
 assert(state.using_ring==0&&state.ring.valid==0);
 /* looper cleared: ring reacquired empty, no garbage */
 obj[1]=0;ring_ok=1;float peak=0;
 for(int b=0;b<4000;b++){memset(buf,0,sizeof buf);ring_echo_process(buf,64,p,0,&on,0,0);for(int f=0;f<128;f++)peak=fmaxf(peak,fabsf(buf[f]));}
 assert(state.using_ring==1&&peak==0.0f);
 printf("ring echo ok\n");return 0;
}
