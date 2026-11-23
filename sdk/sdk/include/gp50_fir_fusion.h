/* Init-time FIR fusion for the SDK's 64-frame/FFT128 convolver.
 * No heap, libm, hardware access, or audio-loop work. Caller validates the
 * capture record and owns stable input/output spans for the entire call.
 * GPTC spectra use FFT(taps)/128; IR bytes are signed int32LE Q23, 44.1 kHz.
 * Scratch may be reused by mutually exclusive record validators at init. */
#ifndef GP50_FIR_FUSION_H
#define GP50_FIR_FUSION_H
#include <stdint.h>

typedef struct { float re[128], im[128], post[256]; } gp50_fir_fusion_scratch;
enum { GP50_FUSION_POST_TAPS=256, GP50_FUSION_IR_TAPS=512,
       GP50_FUSION_PARTITIONS=12, GP50_FUSION_SPECTRAL_WORDS=1560 };

static uint32_t gp50_fusion_u32(const uint8_t *p) {
 return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static float gp50_fusion_float(const uint8_t *p) {
 union { uint32_t u; float f; } v={.u=gp50_fusion_u32(p)};return v.f;
}
static int gp50_fusion_finite(float f) {
 union { float f; uint32_t u; } v={.f=f};return (v.u&0x7f800000u)!=0x7f800000u;
}
/* Forward unnormalised FFT; tw[n]=cos(2*pi*n/128), 160 float32 entries.
 * Use the same exact-cardinal table as the compact kernel. */
static void gp50_fusion_fft(gp50_fir_fusion_scratch *s,const float *tw) {
 for(uint32_t i=0;i<128u;i++) {
  uint32_t j=0,v=i;
  for(uint32_t b=0;b<7u;b++){j=j<<1|(v&1u);v>>=1;}
  if(i<j){float t=s->re[i];s->re[i]=s->re[j];s->re[j]=t;
   t=s->im[i];s->im[i]=s->im[j];s->im[j]=t;}
 }
 for(uint32_t half=1;half<128u;half<<=1) {
  uint32_t step=64u/half;
  for(uint32_t j=0;j<half;j++) {
   float wr=tw[j*step],si=tw[j*step+96u];
   for(uint32_t k=j;k<128u;k+=2u*half) {
    uint32_t q=k+half;
    float tr=wr*s->re[q]+si*s->im[q],ti=wr*s->im[q]-si*s->re[q];
    s->re[q]=s->re[k]-tr;s->im[q]=s->im[k]-ti;
    s->re[k]+=tr;s->im[k]+=ti;
   }
  }
 }
}
/* post_spectra: exactly four packed 65-bin complex partitions (2080 bytes).
 * ir==NULL && ir_bytes==0 means bypass: preserve original spectra bitwise.
 * Output spans are disjoint from inputs/scratch. On failure output is invalid;
 * keep the DSP disabled until the caller has completed a successful install.
 * Level stays a runtime scalar; this function never normalises/truncates IRs. */
static int gp50_fir_fuse_q23(const uint8_t *post_spectra,uint32_t post_bytes,
 const uint8_t *ir,uint32_t ir_bytes,volatile float *out,uint32_t out_words,
 gp50_fir_fusion_scratch *s,const float *tw) {
 if(!post_spectra||post_bytes!=2080u||!out||out_words<1560u||!s||!tw||
    (ir?ir_bytes!=2048u:ir_bytes!=0u))return 0;
 for(uint32_t i=0;i<520u;i++)if(!gp50_fusion_finite(gp50_fusion_float(post_spectra+4u*i)))return 0;
 if(!ir) {
  for(uint32_t i=0;i<1560u;i++)out[i]=i<520u?gp50_fusion_float(post_spectra+4u*i):0.0f;
  return 1;
 }
 /* Inverse FFT of each H/128: conjugate symmetry + forward FFT of
  * conjugate(H/128) gives real taps directly, with no extra /128. */
 for(uint32_t part=0;part<4u;part++) {
  for(uint32_t k=0;k<128u;k++) {
   uint32_t bin=k<=64u?k:128u-k,off=4u*(part*130u+2u*bin);
   s->re[k]=gp50_fusion_float(post_spectra+off);
   s->im[k]=(k==0u||k==64u)?0.0f:
    (k<=64u?-gp50_fusion_float(post_spectra+off+4u):gp50_fusion_float(post_spectra+off+4u));
  }
  gp50_fusion_fft(s,tw);
  for(uint32_t j=0;j<64u;j++)s->post[part*64u+j]=s->re[j];
 }
 /* Form only the current output partition; the full 767-tap temporary
  * would otherwise exceed the tight ARM overlay state budget. */
 for(uint32_t part=0;part<12u;part++) {
  for(uint32_t j=0;j<128u;j++) {
   float sum=0.0f;
   if(j<64u) {
    uint32_t n=part*64u+j,lo=n>511u?n-511u:0u,hi=n<255u?n:255u;
    for(uint32_t i=lo;i<=hi;i++) {
     uint32_t u=gp50_fusion_u32(ir+4u*(n-i));
     /* Avoid implementation-defined conversion from uint32 to int32. */
     float tap=(u&0x80000000u)?-(float)(~u)-1.0f:(float)u;
     sum+=s->post[i]*(tap*(1.0f/8388608.0f));
    }
   }
   s->re[j]=sum;s->im[j]=0.0f;
  }
  gp50_fusion_fft(s,tw);
  for(uint32_t k=0;k<65u;k++) {
   float re=s->re[k]*(1.0f/128.0f),im=s->im[k]*(1.0f/128.0f);
   if(!gp50_fusion_finite(re)||!gp50_fusion_finite(im))return 0;
   out[part*130u+2u*k]=re;out[part*130u+2u*k+1u]=im;
  }
 }
 return 1;
}
#endif
