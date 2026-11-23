/* Native parser/control memory-bound checks, run with UBSan. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static float data[4096],program[4096];
#define TC_CELL(i) (&data[i])
#define TC_PROG(i) (&program[i])
#include "tone_compact.c"
static void wr32(unsigned char *r,unsigned off,unsigned v){for(unsigned j=0;j<4;j++)r[off+j]=(unsigned char)(v>>(8*j));}
int main(int argc,char **argv){
 unsigned char raw[2696]={0},bad[2696];
 if(argc==2){FILE *f=fopen(argv[1],"rb");assert(f);assert(fread(raw,1,sizeof raw,f)==sizeof raw);fclose(f);}
 else{
  assert(argc==1);wr32(raw,0,0x43545047u);wr32(raw,4,1);wr32(raw,8,2696);wr32(raw,12,1);wr32(raw,16,32);wr32(raw,20,16);wr32(raw,24,256);
  wr32(raw,32,0xc4800000u);wr32(raw,36,0x3f000000u);wr32(raw,40,0x3f800000u);
  for(unsigned off=240;off<272;off+=4)wr32(raw,off,0x3f800000u);
  wr32(raw,432,0x3f800000u);wr32(raw,44,hash(raw));
 }
 for(unsigned i=0;i<4096;i++){data[i]=17.0f;program[i]=19.0f;}
 float params[8]={50,50,50,50,50,0,0,0};const unsigned char *content=raw;unsigned char enabled=1;float samples[128];for(unsigned i=0;i<128;i++)samples[i]=.123f;
 tone_compact_init(params,&content);assert(valid==1);tone_compact_process(samples,64,params,0,&enabled,0,0);
 assert(*(unsigned*)&data[COPRO_CELL_ENABLE]==1);assert(data[COPRO_CELL_INPUT_GAIN]==.5f);
 for(unsigned i=0;i<COPRO_CELL_ENABLE;i++)assert(data[i]==17.0f);
 for(unsigned i=TC_DATA_END;i<4096;i++)assert(data[i]==17.0f);
 for(unsigned i=0;i<TC_TW;i++)assert(program[i]==19.0f);
 for(unsigned i=0xe00;i<4096;i++)assert(program[i]==19.0f);
 for(unsigned i=0;i<128;i++)assert(samples[i]==.123f);
 enabled=0;tone_compact_process(samples,64,params,0,&enabled,0,0);assert(*(unsigned*)&data[COPRO_CELL_ENABLE]==0);
 enabled=1;params[0]=0;tone_compact_process(samples,64,params,0,&enabled,0,0);assert(data[COPRO_CELL_INPUT_GAIN]==0);
 for(unsigned variant=0;variant<5;variant++){
  memcpy(bad,raw,sizeof raw);
  if(variant==0)bad[0]='?';
  if(variant==1)bad[100]^=1;
  if(variant==2){wr32(bad,240,0x7fc00000u);wr32(bad,44,hash(bad));}
  if(variant==3){wr32(bad,448,0x40000000u);wr32(bad,44,hash(bad));}
  if(variant==4){wr32(bad,12,2);wr32(bad,44,hash(bad));}
  content=bad;tone_compact_init(params,&content);assert(!valid);tone_compact_process(samples,64,params,0,&enabled,0,0);assert(*(unsigned*)&data[COPRO_CELL_ENABLE]==0);
 }
 content=0;tone_compact_init(params,&content);assert(!valid);
 puts("GPTC parser/control/region bounds PASS");return 0;
}
