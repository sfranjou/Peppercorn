/* Ring Echo 0.1.0: mono feedback echo up to 9.5 s in the stock looper's RAM, borrowed only
 * while the looper is empty (sdk/resources/gp50_looper.h). Otherwise, or on firmware without
 * the looper signature, a short in-slot Q15 line (0.37 s). Test client for the looper lease;
 * history that predates the current ownership reads as silence, so taking the ring back after
 * the looper is cleared starts from an empty echo. Offline SDK example; never installed. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#endif
#include "gp50_looper.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#define FALLBACK_N 16384u
#define INLINE static __attribute__((always_inline)) inline
typedef struct {
 gp50_looper_ring ring;
 uint32_t write, filled, using_ring;
 float delay, lowpass, mix, feedback, volume;
 int16_t fallback[FALLBACK_N];
} RingEcho;
static RingEcho state;
INLINE float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
INLINE int16_t q15(float x){x=bound(x,-1.0f,0.99997f)*32768.0f;return (int16_t)(x<0?x-0.5f:x+0.5f);}
INLINE float unq(int16_t v){return (float)v*(1.0f/32768.0f);}
INLINE float target(const float *p,uint32_t cap){return bound(bound(p[1],20.0f,9500.0f)*(GP50_SAMPLE_RATE/1000.0f),1.0f,(float)(cap-2u));}
GP50_INIT void ring_echo_init(const float *p) {
 state.ring.owned=0;state.ring.valid=0;state.ring.write=0;state.write=0;state.filled=0;state.using_ring=0;
 state.delay=target(p,FALLBACK_N);state.lowpass=0;
 state.mix=bound(p[0]*.01f,0,1);state.feedback=bound(p[2]*.01f,0,.95f);state.volume=bound(p[4]*.01f,0,1);
}
GP50_PROCESS void ring_echo_process(float *s,uint32_t frames,const float *p,uint32_t r3,const uint8_t *enable,const uint32_t *beat,void *r6) {
 (void)r3;(void)beat;(void)r6;
 /* Ownership is checked every block, bypassed or not, so a looper take is never touched. */
 int own=gp50_looper_acquire(&state.ring);
 if(own!=(int)state.using_ring){state.using_ring=(uint32_t)own;state.write=0;state.filled=0;}
 if(!*enable)return;
 const uint32_t cap=own?GP50_LOOPER_CELLS:FALLBACK_N;
 if(state.delay>(float)(cap-2u))state.delay=(float)(cap-2u);
 const float goal=target(p,cap),mix=bound(p[0]*.01f,0,1),fb=bound(p[2]*.01f,0,.95f);
 const float tone=.05f+.9f*bound(p[3]*.01f,0,1),vol=bound(p[4]*.01f,0,1);
 for(uint32_t f=0;f<frames;f++){
  float x=s[2*f];if(x!=x)x=0;x=bound(x,-8,8);
  state.delay+=bound(goal-state.delay,-1.5f,1.5f);
  state.mix+=bound(mix-state.mix,-.002f,.002f);state.feedback+=bound(fb-state.feedback,-.002f,.002f);state.volume+=bound(vol-state.volume,-.002f,.002f);
  uint32_t whole=(uint32_t)state.delay;float frac=state.delay-(float)whole,a,b;
  if(own){a=unq(gp50_looper_read(&state.ring,whole));b=unq(gp50_looper_read(&state.ring,whole+1u));}
  else{
   uint32_t i=state.write>=whole?state.write-whole:state.write+FALLBACK_N-whole;
   a=whole&&whole<=state.filled?unq(state.fallback[i]):0;b=whole<state.filled?unq(state.fallback[i?i-1u:FALLBACK_N-1u]):0;
  }
  float wet=a+(b-a)*frac;state.lowpass+=tone*(wet-state.lowpass);
  int16_t v=q15(x+state.feedback*state.lowpass);
  if(own)gp50_looper_write(&state.ring,v);
  else{state.fallback[state.write]=v;state.write=state.write+1u==FALLBACK_N?0:state.write+1u;if(state.filled<FALLBACK_N)state.filled++;}
  s[2*f]=s[2*f+1]=(x+state.mix*wet)*state.volume;
 }
}
