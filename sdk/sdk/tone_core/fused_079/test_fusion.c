/* Native UBSan executable used by qualify_fused_079.py. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gp50_fir_fusion.h"
#include "../../effects/tone_compact_063/compact_tw.h"
static struct { uint32_t before; gp50_fir_fusion_scratch s; uint32_t after; } scratch;
static struct { uint32_t before; float words[1560]; uint32_t after; } result;
int main(int argc,char **argv) {
 assert(argc==4);
 uint8_t spectra[2080],ir[2048];
 FILE *f=fopen(argv[1],"rb");assert(f&&fread(spectra,1,2080,f)==2080);fclose(f);
 const uint8_t *input=0;
 if(strcmp(argv[2],"bypass")){f=fopen(argv[2],"rb");assert(f&&fread(ir,1,2048,f)==2048);fclose(f);input=ir;}
 scratch.before=result.before=0x12345678u;scratch.after=result.after=0x87654321u;
 assert(!gp50_fir_fuse_q23(0,2080,input,input?2048:0,result.words,1560,&scratch.s,compact_tw));
 assert(!gp50_fir_fuse_q23(spectra,2079,input,input?2048:0,result.words,1560,&scratch.s,compact_tw));
 assert(!gp50_fir_fuse_q23(spectra,2080,input,input?2048:0,result.words,1559,&scratch.s,compact_tw));
 assert(!gp50_fir_fuse_q23(spectra,2080,ir,2047,result.words,1560,&scratch.s,compact_tw));
 assert(!gp50_fir_fuse_q23(spectra,2080,0,2048,result.words,1560,&scratch.s,compact_tw));
 assert(gp50_fir_fuse_q23(spectra,2080,input,input?2048:0,result.words,1560,&scratch.s,compact_tw));
 assert(scratch.before==0x12345678u&&scratch.after==0x87654321u);
 assert(result.before==0x12345678u&&result.after==0x87654321u);
 if(!input){assert(!memcmp(spectra,result.words,2080));for(unsigned i=520;i<1560;i++)assert(result.words[i]==0);}
 f=fopen(argv[3],"wb");assert(f&&fwrite(result.words,4,1560,f)==1560);fclose(f);
 /* Nonfinite spectra must fail even on the bypass path. */
 spectra[0]=0;spectra[1]=0;spectra[2]=0x80;spectra[3]=0x7f;
 assert(!gp50_fir_fuse_q23(spectra,2080,0,0,result.words,1560,&scratch.s,compact_tw));
 return 0;
}
