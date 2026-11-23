/* Tail Doubler 0.1.0 (MOD group 6): modulated doubling delay whose line lives in a
 * resident-granted managed-tail lease (3,840 Q15 samples, 87 ms). The MOD slot is
 * only 8 KiB, so without a lease it runs from a 1,024-sample in-slot line (23 ms):
 * Delay is then clamped. Second tail client next to Long Echo (DLY group 7).
 * Unwritten history reads as silence (tail content is arbitrary at boot). */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#endif
#include "gp50_tail.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif

#define FALLBACK_N 1024u
#define TAIL_N 3840u /* effect.json requests 2*TAIL_N bytes */
#define INLINE static __attribute__((always_inline)) inline

typedef struct {
 gp50_tail tail;
 uint32_t using_tail, capacity, write, filled;
 float delay, phase, mix, volume;
 uint16_t fallback[FALLBACK_N];
} TailDoubler;
static TailDoubler state;

INLINE float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
INLINE uint16_t line_read(uint32_t i){return state.using_tail?gp50_tail_read16(&state.tail,i):state.fallback[i];}
INLINE void line_write(uint32_t i,uint16_t v){if(state.using_tail)gp50_tail_write16(&state.tail,i,v);else state.fallback[i]=v;}
/* Sine-like LFO from phase in [0,1): triangle 4p-1 folded above 1 (=3-4p), then
 * cubic shaping, |error| < 0.06. The fold is an integer compare of the float's
 * bits plus an arithmetic blend: no conditional VFP move (clang 17 pads such IT
 * blocks with a NOP that breaks them; build_effect.py rejects that pattern). */
INLINE float lfo(float p){
 float x=4.0f*p-1.0f;union{float f;int32_t i;}u;u.f=x;
 int32_t c=u.i>0x3f800000;             /* x>1 for the positive/negative range used */
 __asm__("" : "+r"(c));                /* opaque: forces vcvt, prevents a VFP select */
 float over=(float)c;
 x=x+over*(2.0f-2.0f*x);
 return x*(1.5f-.5f*x*x);
}
static void select_line(void) {
 state.using_tail=gp50_resident_present() && gp50_tail_bind(gp50_tail_view(GP50_EFFECT_GROUP),&state.tail) && state.tail.bytes>=2u*TAIL_N;
 state.capacity=state.using_tail?TAIL_N:FALLBACK_N;
 state.write=0;state.filled=0;
}
/* Base delay in samples, leaving room for +/-3 ms modulation and interpolation. */
INLINE float base_delay(const float *params) {
 float d=bound(params[1],20.0f,85.0f)*(GP50_SAMPLE_RATE/1000.0f);
 return bound(d,1.0f,(float)(state.capacity-2u)-3.0f*(GP50_SAMPLE_RATE/1000.0f)-1.0f);
}
GP50_INIT void tail_doubler_init(const float *params) {
 select_line();
 state.delay=base_delay(params);state.phase=0;
 state.mix=bound(params[0]*.01f,0,1);state.volume=bound(params[4]*.01f,0,1);
}
GP50_PROCESS void tail_doubler_process(float *samples,uint32_t frames,const float *params,
 uint32_t reserved_r3,const uint8_t *enable,const uint32_t *beat_period_ms,void *reserved_b18) {
 (void)reserved_r3;(void)beat_period_ms;(void)reserved_b18;
 if(!*enable)return;
 if(state.using_tail && !gp50_tail_current(gp50_tail_view(GP50_EFFECT_GROUP),&state.tail)) {
  state.using_tail=0;state.capacity=FALLBACK_N;state.write=0;state.filled=0;
 }
 const float goal=base_delay(params),mix=bound(params[0]*.01f,0,1),volume=bound(params[4]*.01f,0,1);
 const float depth=bound(params[2]*.01f,0,1)*3.0f*(GP50_SAMPLE_RATE/1000.0f);
 const float step=bound(params[3],.1f,5.0f)*(1.0f/GP50_SAMPLE_RATE);
 const uint32_t n=state.capacity;
 for(uint32_t f=0;f<frames;f++) {
  float x=samples[2*f];if(x!=x)x=0;x=bound(x,-8,8);
  state.delay+=bound(goal-state.delay,-.5f,.5f);
  state.mix+=bound(mix-state.mix,-.002f,.002f);
  state.volume+=bound(volume-state.volume,-.002f,.002f);
  state.phase+=step;if(state.phase>=1.0f)state.phase-=1.0f;
  float d=bound(state.delay+depth*lfo(state.phase),1.0f,(float)(n-2u));
  uint32_t whole=(uint32_t)d;float frac=d-(float)whole;
  float a=0,b=0;
  uint32_t i=state.write>=whole?state.write-whole:state.write+n-whole;
  if(whole<=state.filled)a=gp50_q15_unpack(line_read(i));
  if(whole<state.filled)b=gp50_q15_unpack(line_read(i?i-1u:n-1u));
  float wet=a+(b-a)*frac;
  line_write(state.write,gp50_q15_pack(x));
  state.write=state.write+1u==n?0:state.write+1u;
  if(state.filled<n)state.filled++;
  float y=(x+state.mix*wet)*state.volume;
  samples[2*f]=samples[2*f+1]=y;
 }
}
