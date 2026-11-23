/* Native: GR Comp gain law, published mailbox, no publish without adapter. */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gp50_resident.h"
static _Alignas(8) unsigned char host_resident[512];
static uintptr_t map(uint32_t a){assert(a>=GP50_RESIDENT_BASE&&a<GP50_RESIDENT_BASE+512u);return (uintptr_t)host_resident+(a-GP50_RESIDENT_BASE);}
#define GP50_TAIL_PTR(a) map((uint32_t)(a))
#define GP50_NATIVE_TEST
#define GP50_EFFECT_GROUP 1u
#define GP50_SAMPLE_RATE 44100.0f
#include "gr_comp.c"
static uint16_t mb(int i){uint16_t v;memcpy(&v,host_resident+288+2*i,2);return v;}
int main(void){
 /* approximations */
 for(float x=1e-5f;x<8;x*=1.37f)assert(fabsf(fast_log2(x)-log2f(x))<1e-4f);
 for(float x=-29;x<29;x+=0.37f)assert(fabsf(fast_exp2(x)/exp2f(x)-1)<3e-4f);
 float p[5]={-20,4,5,120,6};uint8_t on=1;float s[128];
 memset(host_resident,0x3c,512);gr_comp_init(p);           /* no adapter: never publishes */
 for(int b=0;b<50;b++){for(int i=0;i<64;i++)s[2*i]=s[2*i+1]=.5f*sinf((b*64+i)*.06f);gr_comp_process(s,64,p,0,&on,0,0);}
 for(int i=0;i<4;i++)assert(mb(i)==0x3c3c);
 memset(host_resident,0,512);gp50_resident_init((gp50_resident*)host_resident);gr_comp_init(p);
 float peak=0;
 for(int b=0;b<800;b++){for(int i=0;i<64;i++)s[2*i]=s[2*i+1]=.5f*sinf((b*64+i)*.06f);gr_comp_process(s,64,p,0,&on,0,0);
  if(b>600)for(int i=0;i<64;i++)if(fabsf(s[2*i])>peak)peak=fabsf(s[2*i]);}
 /* -6.02 dBFS peak, thr -20, ratio 4 -> GR = 13.98*0.75 = 10.49 dB at peaks */
 printf("mailbox magic %#x group %u gr %u seq %u peak out %.3f\n",mb(0),mb(1),mb(2),mb(3),peak);
 assert(mb(0)==0x4752&&mb(1)==1&&mb(3)==800&&mb(2)>900&&mb(2)<1100);
 assert(peak>0.27f&&peak<0.34f);
 assert(mb(4)>=mb(2)&&mb(4)<1100);  /* peak-hold since boot (no reply clears it here) */   /* static law 0.30; 5 ms attack smoothing leaves ~9.9 dB GR */
 /* bypass: untouched, no publish */
 on=0;for(int i=0;i<128;i++)s[i]=(float)i;gr_comp_process(s,64,p,0,&on,0,0);for(int i=0;i<128;i++)assert(s[i]==(float)i);assert(mb(3)==800);
 /* quiet input: zero GR; NaN/huge safe */
 on=1;for(int b=0;b<400;b++){for(int i=0;i<128;i++)s[i]=(i==7)?NAN:(b%50==0?1e9f:.001f);gr_comp_process(s,64,p,0,&on,0,0);for(int i=0;i<128;i++)assert(isfinite(s[i]));}
 for(int b=0;b<800;b++){for(int i=0;i<128;i++)s[i]=.001f;gr_comp_process(s,64,p,0,&on,0,0);}
 assert(mb(2)==0);
 puts("PASS: approximations, gain law (~10.5 dB GR), publish only with adapter, bypass, quiet=0, NaN/huge safe");return 0;}
