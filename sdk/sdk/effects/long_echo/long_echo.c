/* Long Echo 0.1.0: mono feedback delay whose line lives in a resident-granted
 * managed-tail lease (up to ~1.8 s at 44.1 kHz, Q15). Without a resident adapter
 * (every installed image so far) or without a grant, it runs from a short
 * in-slot Q15 line (~0.37 s) instead. Offline SDK example; never installed.
 *
 * The line is not cleared at init (that would block the foreground for ~80k
 * external stores): a fill counter makes unwritten history read as silence. */
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

#ifndef FALLBACK_N
#define FALLBACK_N 16384u
#endif
#ifndef TAIL_N
#define TAIL_N 79380u /* 1.8 s; effect.json requests 2*TAIL_N bytes */
#endif
#ifndef TIME_MIN
#define TIME_MIN 20.0f
#define TIME_MAX 1800.0f
#endif
#define INLINE static __attribute__((always_inline)) inline

typedef struct {
 gp50_tail tail;
 uint32_t using_tail, capacity, write, filled;
 float delay, lowpass, mix, feedback, volume;
 uint16_t fallback[FALLBACK_N];
} LongEcho;
static LongEcho state;

INLINE float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
INLINE uint16_t line_read(uint32_t i){return state.using_tail?gp50_tail_read16(&state.tail,i):state.fallback[i];}
INLINE void line_write(uint32_t i,uint16_t v){if(state.using_tail)gp50_tail_write16(&state.tail,i,v);else state.fallback[i]=v;}
static void select_line(void) {
 const volatile gp50_lease_view *view=gp50_tail_view(GP50_EFFECT_GROUP);
 state.using_tail=gp50_resident_present() && gp50_tail_bind(view,&state.tail) && state.tail.bytes>=2u*FALLBACK_N;
 state.capacity=state.using_tail?state.tail.bytes/2u:FALLBACK_N;
 state.write=0;state.filled=0;
}
INLINE float target_delay(const float *params) {
 float d=bound(params[1],TIME_MIN,TIME_MAX)*(GP50_SAMPLE_RATE/1000.0f);
 return bound(d,1.0f,(float)(state.capacity-2u));
}
GP50_INIT void long_echo_init(const float *params) {
 select_line();
 state.delay=target_delay(params);state.lowpass=0;
 state.mix=bound(params[0]*.01f,0,1);state.feedback=bound(params[2]*.01f,0,.95f);
 state.volume=bound(params[4]*.01f,0,1);
}
GP50_PROCESS void long_echo_process(float *samples,uint32_t frames,const float *params,
 uint32_t reserved_r3,const uint8_t *enable,const uint32_t *beat_period_ms,void *reserved_b18) {
 (void)reserved_r3;(void)beat_period_ms;(void)reserved_b18;
 if(!*enable)return;
 /* Lease revoked or replaced underneath us: drop to the private line. */
 if(state.using_tail && !gp50_tail_current(gp50_tail_view(GP50_EFFECT_GROUP),&state.tail)) {
  state.using_tail=0;state.capacity=FALLBACK_N;state.write=0;state.filled=0;
  if(state.delay>(float)(FALLBACK_N-2u))state.delay=(float)(FALLBACK_N-2u);
 }
 const float goal=target_delay(params),mix=bound(params[0]*.01f,0,1),feedback=bound(params[2]*.01f,0,.95f);
 const float tone=.05f+.9f*bound(params[3]*.01f,0,1),volume=bound(params[4]*.01f,0,1);
 const uint32_t n=state.capacity;
 for(uint32_t f=0;f<frames;f++) {
  float x=samples[2*f];if(x!=x)x=0;x=bound(x,-8,8);
  /* Glide toward the requested time (~1.5 ms of delay per ms), no zipper jumps. */
  state.delay+=bound(goal-state.delay,-1.5f,1.5f);
  state.mix+=bound(mix-state.mix,-.002f,.002f);
  state.feedback+=bound(feedback-state.feedback,-.002f,.002f);
  state.volume+=bound(volume-state.volume,-.002f,.002f);
  uint32_t whole=(uint32_t)state.delay;float frac=state.delay-(float)whole;
  /* Tap i is `whole` samples old, j one older; unwritten history reads as 0. */
  float a=0,b=0;
  uint32_t i=state.write>=whole?state.write-whole:state.write+n-whole;
  if(whole && whole<=state.filled)a=gp50_q15_unpack(line_read(i));
  if(whole<state.filled)b=gp50_q15_unpack(line_read(i?i-1u:n-1u));
  float wet=a+(b-a)*frac;
  state.lowpass+=tone*(wet-state.lowpass);
  line_write(state.write,gp50_q15_pack(x+state.feedback*state.lowpass));
  state.write=state.write+1u==n?0:state.write+1u;
  if(state.filled<n)state.filled++;
  float y=(x+state.mix*wet)*state.volume;
  samples[2*f]=samples[2*f+1]=y;
 }
}
