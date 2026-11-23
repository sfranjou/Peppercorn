#include "endpoint.h"
static int finite32(uint32_t x) { return (x&0x7f800000u)!=0x7f800000u; }
static float number(uint32_t x) { union {uint32_t u;float f;} v={.u=x};return v.f; }
int gp50_fs_ab_endpoint(uint32_t bits,uint32_t lob,uint32_t hib,uint32_t sb) {
    if(!finite32(bits)||!finite32(lob)||!finite32(hib)||!finite32(sb)) return 0;
    float v=number(bits),lo=number(lob),hi=number(hib),step=number(sb);
    if(!(step>0) || !(lo<=hi) || v<lo || v>hi) return 0;
    float q=v/step;
    q=v>0?q+0.5f:q-0.5f;
    /* The setter casts this value to int32_t. Bound it before the cast so an
     * extreme/subnormal step cannot introduce undefined behavior here. */
    if(!(q>=-2147483648.0f && q<2147483648.0f)) return 0;
    q=(float)(int32_t)q*step;
    if(hi<q) q=hi;
    if(q<lo) q=lo;
    return q==v;
}
