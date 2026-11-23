/* Actual v8 initializer/process with mapped DSP MMIO and the real resident
 * lifecycle/private-copy code. COPY_IR storage operation is injected here;
 * target flash geometry/copy instructions require separate target execution. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "arm_private.h"
static uint8_t config[0x2e2],ir[2048];
static float native_cells[4096],native_program[8192];
static uint32_t run_reg,status_reg;
#define NS_CELL(i) (&native_cells[(i)])
#define NS_PROG(i) (&native_program[(i)])
#define COPRO_RUN_REG ((uintptr_t)&run_reg)
#define COPRO_STATUS_REG ((uintptr_t)&status_reg)
#define GP50_INIT
#define GP50_PROCESS
#define GP50_NATIVE_TEST
#define GP50_CAPTURE_WORKING_CONFIG config
#include "ns_capture_v8/ns_capture.c"
static gp50_capture_arm producer;
static gp50_capture_geometry factory={0x122000,0x36000,4096,3};
static unsigned copies,allocations,frees,record_copies;
static uint8_t second_record[2696];static int second_fails;
static int copy_fails;
static void *allocate(uint32_t n){allocations++;return malloc(n);}
static void release(void *p){frees++;free(p);}
void gp50_capture_overlay_call(uint32_t event,gp50_capture_overlay_context *c) {
 if(event==GP50_CAPTURE_PREPARE)
  gp50_capture_private_prepare(&producer,c,0x125000,allocate);
 else if(event==GP50_CAPTURE_COPY_IR) {
  assert(c->extent<41);assert(c->generation==producer.snapshot.generation);
  copies++;
  if(copy_fails)c->extent=0;
  else {memcpy((void *)c->record,ir,2048);c->extent=2048;}
 } else if(event==GP50_CAPTURE_COPY_RECORD) {
  assert(c->extent<30);record_copies++;
  if(second_fails)c->extent=0;
  else {memcpy((void *)c->record,second_record,2696);c->extent=2696;}
 } else {
  gp50_capture_arm_overlay(&producer,event,c,0);
  if(event==GP50_CAPTURE_COMPLETE)gp50_capture_private_release(c,release);
 }
}
static float p[5]={50,50,50,50,50};
static void init(uint8_t *record) {
 gp50_capture_arm_retire(&producer);
 uint32_t gen=gp50_capture_arm_begin(&producer,0);assert(gen);
 assert(gp50_capture_arm_bind(&producer,gen,0x125000,&factory,0));
 const uint8_t *r=record;ns_capture_init(p,&r);assert(allocations==frees);
}
static void process(void) {
 float samples[128]={0};uint8_t enable=1;
 ns_capture_process(samples,64,p,0,&enable,0,0);
}
int main(int argc,char **argv) {
 assert(argc==2);
 uint8_t record[2696];FILE *f=fopen(argv[1],"rb");assert(f);
 assert(fread(record,1,sizeof record,f)==sizeof record);fclose(f);
 gp50_capture_arm_reset(&producer);
 float level=100;memcpy(config+0x220,&level,4);
 init(record);assert(valid && gmode && !copies);process();
 float base=*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN);
 config[0x188]=16;config[0x175]=40;*(int32_t *)ir=8388607;
 init(record);assert(valid && cab.enabled && copies==1);process();
 assert(*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)==base);
 level=50;memcpy(config+0x220,&level,4);process();
 assert(*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)==base*.5f);
 config[0x188]=0;process();assert(config[0x2e1]==2);
 config[0x2e1]=0;init(record);assert(valid && !cab.enabled);process();
 assert(*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)==base);
 config[0x188]=16;copy_fails=1;init(record);
 assert(!valid && producer.snapshot.state==GP50_CAPTURE_REJECTED);
 unsigned before=copies;config[0x175]=41;init(record);assert(!valid && copies==before);
 config[0x175]=0;config[0x188]=0;memcpy(record,"GP5N",4);init(record);
 assert(!valid && producer.snapshot.state==GP50_CAPTURE_REJECTED);

 /* Capture pair (2026-11-08): DST Capture signature in DSP program memory, DST enable bit 2, Slot at +0x1e0. */
 memcpy(record,second_record,0);                       /* record buffer reused below: reload the main file */
 f=fopen(argv[1],"rb");assert(fread(record,1,sizeof record,f)==sizeof record);fclose(f);
 memcpy(second_record,record,sizeof record);
 uint32_t *pm=(uint32_t *)native_program;
 const uint32_t sig[3]={0x7d064443u,0x7d065054u,0xa0080500u};
 config[0x175]=40;config[0x188]=16|4;float slot=3;memcpy(config+0x1e0,&slot,4);config[0x2e1]=0;
 memcpy(pm+6,sig,12);
 unsigned ir_before=copies;
 init(record);assert(valid && gmode && record_copies==1 && dst_request==3);   /* copy_fails still 1: cab unreadable */
 assert(*(uint32_t *)NS_CELL(COPRO_CELL_G_PAIR)==1u && *(uint32_t *)NS_CELL(COPRO_CELL_G_MAIN_OFF)==0u);
 assert(*(uint32_t *)NS_CELL(COPRO_CELL_G_PARTS)==4u);          /* DST capture disables the cab IR */
 { /* 2026-11-21 DST Gain/VOL/Bass/Mid/Treble (working parameters 1..5 at +0x1e4) drive the second slot only. */
   float in2=*NS_CELL(COPRO_CELL_G_P2_INPUT_GAIN),out2=*NS_CELL(COPRO_CELL_G_P2_OUTPUT_GAIN),in1,flat[5],k[5]={50,50,50,50,50};
   memcpy(config+0x1e4,k,20);process();
   assert(*NS_CELL(COPRO_CELL_G_P2_INPUT_GAIN)==in2 && *NS_CELL(COPRO_CELL_G_P2_OUTPUT_GAIN)==out2);  /* 50 = record gains */
   in1=*NS_CELL(COPRO_CELL_G_INPUT_GAIN);memcpy(flat,NS_CELL(COPRO_CELL_G_P2_BASS),20);
   k[0]=100;k[1]=25;k[2]=80;memcpy(config+0x1e4,k,20);process();
   assert(*NS_CELL(COPRO_CELL_G_P2_INPUT_GAIN)==in2*2.0f && *NS_CELL(COPRO_CELL_G_P2_OUTPUT_GAIN)==out2*.5f);
   assert(memcmp(flat,NS_CELL(COPRO_CELL_G_P2_BASS),20) && !memcmp(flat,NS_CELL(COPRO_CELL_G_BASS),20));
   assert(*NS_CELL(COPRO_CELL_G_INPUT_GAIN)==in1);                 /* main slot follows the N->S parameters */
   float nan_=__builtin_nanf("");memcpy(config+0x1e4,&nan_,4);process();assert(*NS_CELL(COPRO_CELL_G_P2_INPUT_GAIN)==in2);
   k[0]=50;k[1]=50;k[2]=50;memcpy(config+0x1e4,k,20);process();
   assert(!memcmp(flat,NS_CELL(COPRO_CELL_G_P2_BASS),20) && config[0x2e1]==0); }  /* tone changes never reload */
 assert(copies==ir_before+1);                                    /* cab still recorded */
 config[0x188]=4;process();assert(config[0x2e1]==0);config[0x188]=16|4;   /* cab changes ignored while DST capture */
 process();assert(config[0x2e1]==0);                             /* stable: no reload */
 float og=*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN);level=50;memcpy(config+0x220,&level,4);process();
 assert(*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)==og);                 /* cab level not applied */
 slot=4;memcpy(config+0x1e0,&slot,4);process();assert(config[0x2e1]==2);   /* Slot change -> reload */
 config[0x2e1]=0;init(record);assert(dst_request==4);process();assert(config[0x2e1]==0);
 pm[7]=0;process();assert(config[0x2e1]==2);                     /* DST effect replaced -> reload */
 config[0x2e1]=0;copy_fails=0;init(record);assert(dst_request==0 && valid && cab.enabled);
 assert(*(uint32_t *)NS_CELL(COPRO_CELL_G_PAIR)==0u && *(uint32_t *)NS_CELL(COPRO_CELL_G_PARTS)==12u);  /* IR back */
 memcpy(pm+6,sig,12);config[0x188]=16;process();assert(config[0x2e1]==0);  /* DST bypassed: no request */
 config[0x188]=16|4;process();assert(config[0x2e1]==2);config[0x2e1]=0;
 second_fails=1;init(record);assert(valid && *(uint32_t *)NS_CELL(COPRO_CELL_G_PAIR)==0u &&
  *(uint32_t *)NS_CELL(COPRO_CELL_G_PARTS)==4u);                 /* unreadable slot: main alone, IR still off */
 process();assert(config[0x2e1]==0);                             /* no reload loop on failure */
 second_fails=0;
 /* Pre-only: no main record. */
 gp50_capture_arm_retire(&producer);
 const uint8_t *none=0;ns_capture_init(p,&none);assert(allocations==frees);
 assert(valid && gmode && *(uint32_t *)NS_CELL(COPRO_CELL_G_MAIN_OFF)==0u && *(uint32_t *)NS_CELL(COPRO_CELL_G_PAIR)==0u &&
        *(uint32_t *)NS_CELL(COPRO_CELL_G_PARTS)==4u);   /* DST record installed as the main capture */
 process(); { float k[2]={100,25},in1=*NS_CELL(COPRO_CELL_G_INPUT_GAIN),out1=*NS_CELL(COPRO_CELL_G_OUTPUT_GAIN);process();
   assert(*NS_CELL(COPRO_CELL_G_INPUT_GAIN)==in1 && *NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)==out1);
   memcpy(config+0x1e4,k,8);process();                            /* DST alone: DST Gain/VOL drive the main slot */
   assert(*NS_CELL(COPRO_CELL_G_INPUT_GAIN)==in1*2.0f && *NS_CELL(COPRO_CELL_G_OUTPUT_GAIN)==out1*.5f);
   k[0]=k[1]=50;memcpy(config+0x1e4,k,8); }
 process();assert(config[0x2e1]==0);
 /* v7 main-off marker (N->S parameter 8): main record ignored, DST capture alone; marker change -> reload. */
 { float p8[8]={50,50,50,50,50,0,0,0}; uint32_t mo=0xc2f6e979u; memcpy(&p8[7],&mo,4);
   gp50_capture_arm_retire(&producer);uint32_t g=gp50_capture_arm_begin(&producer,0);assert(g);
   assert(gp50_capture_arm_bind(&producer,g,0x125000,&factory,0));
   const uint8_t *r=record;ns_capture_init(p8,&r);assert(allocations==frees);
   assert(valid && main_off && *(uint32_t *)NS_CELL(COPRO_CELL_G_PAIR)==0u && *(uint32_t *)NS_CELL(COPRO_CELL_G_PARTS)==4u);
   config[0x2e1]=0;float samples[128]={0};uint8_t en=1;ns_capture_process(samples,64,p8,0,&en,0,0);assert(config[0x2e1]==0);
   ns_capture_process(samples,64,p,0,&en,0,0);assert(config[0x2e1]==2);config[0x2e1]=0; }
 /* Corrupt second record: nothing installed in pre-only. */
 second_record[100]^=1;ns_capture_init(p,&none);assert(!valid);process();assert(config[0x2e1]==0);

 puts("v8 fused overlay lifecycle, CAB copy/bypass/level/reload/rejection, capture pair/pre-only, DST tone controls passed");
}
