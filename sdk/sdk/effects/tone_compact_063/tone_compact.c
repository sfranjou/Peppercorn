/* Actual compact32/16->256 fitted model adapter, GPTC v1, controlled trial063.
 * Unknown formats bypass. No stock VTSI/GP5N compatibility claim.
 * Program constants / cell offsets generated from program.py by SDK builder. */
#include "gp50_effect.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#include "copro_cells.h"
#include "gp50_biquad.h"
#include "compact_tw.h"
#ifndef TC_CELL
#define TC_CELL(i) ((volatile float *)(0x28000000u+4u*(i)))
#define TC_PROG(i) ((volatile float *)(0x28004000u+4u*(i)))
#endif
#define TC_SIZE 2696u
#define TC_DATA_END (COPRO_CELL_TREBLE+9u)
#ifndef TC_TW
#define TC_TW 0xb58u
#define TC_SPEC 0xbf8u
#endif
#ifndef TC_INIT_FINISH
#define TC_INIT_FINISH(r) 1u
#endif
#define TC_INLINE static inline __attribute__((always_inline))
static uint32_t valid;
static float input_base, output_base, last[5];
TC_INLINE uint32_t rd32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
TC_INLINE float rdf(const uint8_t *p){union{uint32_t u;float f;}x={.u=rd32(p)};return x.f;}
TC_INLINE float limit(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
TC_INLINE int finite(float x){union{float f;uint32_t u;}v={.f=x};return (v.u&0x7f800000u)!=0x7f800000u;}
TC_INLINE void put(uint32_t cell,const uint8_t *r,uint32_t n){
 volatile float *t=TC_CELL(cell);
 for(uint32_t i=0;i<n;i++){__asm__ volatile("" : "+r"(t));*t++=rdf(r);r+=4;}
}
TC_INLINE void design(uint32_t cell,gp50_biquad b){volatile float *t=TC_CELL(cell);t[0]=b.b0;t[1]=b.b1;t[2]=b.b2;t[3]=b.a1;t[4]=b.a2;}
TC_INLINE uint32_t hash(const uint8_t *r){uint32_t h=2166136261u;for(uint32_t i=0;i<TC_SIZE;i++){if(i<44u||i>=48u)h=(h^r[i])*16777619u;}return h;}
TC_INLINE int check(const uint8_t *r){
 if(!r||rd32(r)!=0x43545047u||rd32(r+4)!=1u||rd32(r+8)!=TC_SIZE)return 0;
 uint32_t parallel=rd32(r+12);
 if(parallel>1u||rd32(r+16)!=32u||rd32(r+20)!=16u*parallel||rd32(r+24)!=256u||hash(r)!=rd32(r+44))return 0;
 float branch=rdf(r+28),floor=rdf(r+32),ig=rdf(r+36),og=rdf(r+40);
 if(!finite(branch)||!finite(ig)||!finite(og)||!(floor==-1024.0f||floor==-2047.0f)||branch>100.0f||branch< -100.0f||ig<0||ig>4||og<0||og>8)return 0;
 for(uint32_t i=48u;i<2532u;i+=4u){float x=rdf(r+i);if(!finite(x)||x>1e6f||x< -1e6f)return 0;}
 for(uint32_t i=240u;i<272u;i+=4u)if(!(rdf(r+i)>0))return 0;
 float a1=rdf(r+444),a2=rdf(r+448);
 return a2<1&&a2> -1&&1+a1+a2>0&&1-a1+a2>0;
}
GP50_INIT void tone_compact_init(const float *params,const uint8_t *const *content){
 (void)params;valid=0;*(volatile uint32_t *)TC_CELL(COPRO_CELL_ENABLE)=0;
 /* Init/reload runs with the resident DSP reload ordering, not in an audio loop. */
 for(uint32_t i=COPRO_CELL_ENABLE;i<TC_DATA_END;i++)*TC_CELL(i)=0;
 for(uint32_t i=0;i<5;i++)last[i]=-999.0f;
 const uint8_t *r=content?*content:0;if(!check(r))return;
 input_base=rdf(r+36);output_base=rdf(r+40);
 *TC_CELL(COPRO_CELL_ONE)=1;*TC_CELL(COPRO_CELL_INV1024)=1.0f/1024;
 *TC_CELL(COPRO_CELL_THIRD)=1.0f/3;*TC_CELL(COPRO_CELL_TWOTHIRD)=2.0f/3;
 *TC_CELL(COPRO_CELL_CUTOFF_SQUARED)=.9025f;
 *TC_CELL(COPRO_CELL_FLOOR)=rdf(r+32);*TC_CELL(COPRO_CELL_BRANCH_GAIN)=rdf(r+28);
 *(volatile uint32_t *)TC_CELL(COPRO_CELL_PARALLEL)=rd32(r+12);
 put(COPRO_CELL_PRE,r+48,32);put(COPRO_CELL_SECOND,r+176,16);
 put(COPRO_CELL_NL0,r+240,4);put(COPRO_CELL_NL1,r+256,4);
 put(COPRO_CELL_LPF,r+272,40);put(COPRO_CELL_BQ,r+432,5);
 for(uint32_t i=0;i<160u;i++)*TC_PROG(TC_TW+i)=compact_tw[i];
 for(uint32_t i=0;i<520u;i++)*TC_PROG(TC_SPEC+i)=rdf(r+452u+4u*i);
 design(COPRO_CELL_BASS,gp50_eq_flat());design(COPRO_CELL_MID,gp50_eq_flat());design(COPRO_CELL_TREBLE,gp50_eq_flat());
 valid=TC_INIT_FINISH(r);
}
GP50_PROCESS void tone_compact_process(float *samples,uint32_t frames,const float *p,uint32_t r3,const uint8_t *enable,const uint32_t *period,void *r6){
 (void)samples;(void)frames;(void)r3;(void)period;(void)r6;
 if(valid){
  float gain=finite(p[0])?limit(p[0],0,100):50.0f,vol=finite(p[1])?limit(p[1],0,100):50.0f;
  *TC_CELL(COPRO_CELL_INPUT_GAIN)=input_base*(gain*.02f);
  *TC_CELL(COPRO_CELL_OUTPUT_GAIN)=output_base*(vol*.02f);
  for(uint32_t i=2;i<5;i++){
   float k=finite(p[i])?limit(p[i],0,100):50.0f;
   if(k!=last[i]){float db=(k-50.0f)*.12f;gp50_biquad b=gp50_eq_flat();
    if(k!=50.0f){if(i==2)b=gp50_eq_peak(125.0f,db,.70710678f);else if(i==3)b=gp50_eq_peak(800.0f,db,.70710678f);else b=gp50_eq_high_shelf(1600.0f,db);}
    design(i==2?COPRO_CELL_BASS:i==3?COPRO_CELL_MID:COPRO_CELL_TREBLE,b);last[i]=k;
   }
  }
 }
 *(volatile uint32_t *)TC_CELL(COPRO_CELL_ENABLE)=(valid&&*enable)?1u:0u;
}
