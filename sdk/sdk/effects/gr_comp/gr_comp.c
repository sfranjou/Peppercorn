/* GR Comp 0.1.0 (PRE group 1): feed-forward compressor that publishes its block
 * maximum gain reduction to the MOD034 meter mailbox (home-screen GR page).
 * Params: Thresh -40..0 dB, Ratio 1..20, Attack 1..50 ms, Release 20..500 ms,
 * Gain 0..24 dB makeup. No libm: bit-level log2/exp2 approximations. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#endif
#include "gp50_meter.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#define INLINE static __attribute__((always_inline)) inline
typedef struct { float env,gain_db; } GrComp;
static GrComp state;
INLINE float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
/* log2 for x>0 (|err|<1e-4), exp2 for x in [-30,30] (rel err <1e-4). */
INLINE float fast_log2(float x){
 union{float f;uint32_t i;}u;u.f=x;float e=(float)((int32_t)((u.i>>23)&255u)-127);
 u.i=(u.i&0x7fffffu)|0x3f800000u;float m=u.f;
 float p=(m-1.0f)/(m+1.0f),q=p*p;   /* atanh series, |err| ~1e-5 on [1,2) */
 return e+2.8853901f*p*(1.0f+q*(0.33333333f+q*(0.2f+q*0.14285714f)));
}
INLINE float fast_exp2(float x){
 x=bound(x,-30.0f,30.0f);int32_t i=(int32_t)(x+30.0f)-30;float f=x-(float)i;
 float p=1.0f+f*(0.6931472f+f*(0.2402265f+f*(0.0555041f+f*(0.0096181f+f*0.0013334f))));
 union{float f;uint32_t i;}u;u.f=p;u.i+=(uint32_t)i<<23;return u.f;
}
INLINE float coef(float ms){return fast_exp2(-1.442695f/(bound(ms,0.1f,1000.0f)*(GP50_SAMPLE_RATE/1000.0f)));}
GP50_INIT void gr_comp_init(const float *params){(void)params;state.env=0;state.gain_db=0;}
GP50_PROCESS void gr_comp_process(float *samples,uint32_t frames,const float *params,
 uint32_t reserved_r3,const uint8_t *enable,const uint32_t *beat_period_ms,void *reserved_b18) {
 (void)reserved_r3;(void)beat_period_ms;(void)reserved_b18;
 if(!*enable)return;
 const float thr=bound(params[0],-40.0f,0.0f),slope=1.0f-1.0f/bound(params[1],1.0f,20.0f);
 const float att=coef(params[2]),rel=coef(params[3]),makeup=bound(params[4],0.0f,24.0f);
 float peak=0;
 for(uint32_t f=0;f<frames;f++){
  float x=samples[2*f];if(x!=x)x=0;x=bound(x,-8,8);
  float a=x<0?-x:x;
  float k=a>state.env?att:rel;
  state.env=a+(state.env-a)*k;
  float lvl=6.0206f*fast_log2(state.env+1e-6f);
  float gr=(lvl-thr)*slope;gr=gr>0?gr:0;
  if(gr>peak)peak=gr;
  float y=x*fast_exp2((makeup-gr)*0.16609640f);
  samples[2*f]=samples[2*f+1]=y;
 }
 gp50_meter_publish(GP50_EFFECT_GROUP,(uint32_t)(peak*100.0f+0.5f));
}
