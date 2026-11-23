#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "arm_lifecycle.h"
static void put16(uint8_t *p,unsigned n){p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static void put32(uint8_t *p,unsigned n){put16(p,n);put16(p+2,n>>16);}
int main(void) {
 uint8_t f[12]={0},b[16]={0},c[36]={0};gp50_capture_geometry x,y;
 put32(f+4,0x200);put16(f+8,4096);put16(f+10,256);
 put32(b,0x20001ef4);put32(b+4,0x122000);put16(b+8,4096);put16(b+10,4096);
 b[12]=54;b[13]=1;b[14]=50;b[15]=16;
 put32(c,0x20001ef4);put32(c+4,0x158000);put16(c+8,4096);put16(c+10,120);
 put16(c+34,4096);c[30]=3;c[28]=100;c[29]=56;
 gp50_capture_live_geometry(f,b,c,&x,&y);assert(x.bytes==0x36000 && y.bytes==0x78000);
 unsigned cases=1;uint8_t *arrays[]={f,b,c};unsigned lengths[]={12,16,36};
 /* Exhaust every bit of each field actually consumed, keeping unrelated fields
  * unconstrained. Corrupt flash rejects both; one area's corruption leaves the
  * other area eligible. Pointer classification still runs separately. */
 for(unsigned a=0;a<3;a++)for(unsigned i=0;i<lengths[a];i++) {
  int checked=a<2 || i<12 || i==28 || i==29 || i==30 || i==34 || i==35;
  for(unsigned bit=0;bit<8;bit++) {
   arrays[a][i]^=(uint8_t)(1u<<bit);
   gp50_capture_live_geometry(f,b,c,&x,&y);
   assert(!!x.bytes==!(checked && a<2));assert(!!y.bytes==!(checked && a!=1));
   arrays[a][i]^=(uint8_t)(1u<<bit);cases++;
  }
 }
 printf("%u live capture geometry cases passed\n",cases);
}
