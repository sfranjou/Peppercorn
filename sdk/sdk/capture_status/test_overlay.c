/* Native MMIO substitution only; exercises actual v6 private state and wrapper. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include "arm_private.h"
#include <stdlib.h>
static float native_cells[4096],native_program[8192];
#include "copro_cells.h"
static uint32_t run_reg,status_reg;
#define GP50_NATIVE_TEST
#define NS_CELL(i) (&native_cells[(i)])
#define NS_PROG(i) (&native_program[(i)])
#include "ns_capture_status/ns_capture.c"
static gp50_capture_arm producer;
static gp50_capture_geometry factory={0x122000,0x36000,4096,3};
static const uint8_t *mapped;
static uint32_t mapped_address;
static unsigned cases,allocations,frees;
static int allocation_fails,hide_source;
static uint8_t *protected_page;static unsigned protected_bytes;
static void *allocate(uint32_t n) {assert(n && n<=2696);if(allocation_fails)return 0;allocations++;return malloc(n);}
static void release(void *p) {assert(p);frees++;free(p);}
static float params[5]={50,50,50,50,50};
void gp50_capture_overlay_call(uint32_t event,gp50_capture_overlay_context *c) {
 if(event==GP50_CAPTURE_PREPARE)assert(c->record==(uintptr_t)mapped);
 if(event==GP50_CAPTURE_PREPARE) {
  gp50_capture_private_prepare(&producer,c,mapped_address,allocate);
  if(c->run && hide_source)assert(!mprotect(protected_page,protected_bytes,PROT_NONE));
 } else {
  gp50_capture_arm_overlay(&producer,event,c,mapped_address);
  if(event==GP50_CAPTURE_COMPLETE) {
   if(hide_source)assert(!mprotect(protected_page,protected_bytes,PROT_READ|PROT_WRITE));
   gp50_capture_private_release(c,release);
   assert(allocations==frees && !c->owned);
  }
 }
}
static void put32(uint8_t *p,uint32_t v) {memcpy(p,&v,4);}
static void init(const uint8_t *r,uint32_t address) {
 mapped=r;mapped_address=address;run_reg=status_reg=0;
 uint32_t gen=gp50_capture_arm_begin(&producer,1);assert(gen);
 (void)gp50_capture_arm_bind(&producer,gen,address,&factory,0);
 ns_capture_init(params,&r);
 assert(gp50_capture_valid(&producer.snapshot));cases++;
}
static void process(uint8_t enable) {
 ns_capture_process(0,64,params,0,&enable,0,0);
 assert(gp50_capture_valid(&producer.snapshot));cases++;
}
int main(int argc,char **argv) {
 assert(argc==3);gp50_capture_arm_reset(&producer);
 uint8_t record[4096]={0};
 init(record,0x125000);assert(producer.snapshot.state==GP50_CAPTURE_UNSUPPORTED);
 put32(record,0x11223344);init(record,0x125000);assert(producer.snapshot.kind==GP50_CAPTURE_UNKNOWN);
 put32(record,0x4e355047);put32(record+4,2);put32(record+104,0);
 init(record,0x125000);assert(producer.snapshot.state==GP50_CAPTURE_ACCEPTED && valid);
 process(0);assert(producer.snapshot.flags&GP50_CAPTURE_BYPASSED);
 process(1);assert(!(producer.snapshot.flags&GP50_CAPTURE_BYPASSED));
 /* VLEVEL garbage must never be interpreted as GP5N failure. */
 *(uint32_t *)NS_CELL(NS_UERR)=0x12345678;process(1);
 assert(producer.snapshot.state==GP50_CAPTURE_ACCEPTED && !producer.snapshot.error);
 memset(record,0,sizeof(record));put32(record,0x49535456);
 init(record,0x125000);assert(!valid && producer.snapshot.state==GP50_CAPTURE_REJECTED);
 assert(producer.snapshot.error==GP50_CAPTURE_E_FORMAT);
 record[24]=1;init(record,0x125000);assert(valid && producer.snapshot.kind==GP50_CAPTURE_VTSI);
 allocation_fails=1;init(record,0x125000);
 assert(!valid && producer.snapshot.state==GP50_CAPTURE_REJECTED && producer.snapshot.error==GP50_CAPTURE_E_MEMORY);
 allocation_fails=0;init(record,0x125000);assert(valid);
 /* Checked extent is the 2KiB fallback, with unreadable guard immediately after. */
 unsigned page=(unsigned)sysconf(_SC_PAGESIZE);
 uint8_t *m=mmap(0,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
 assert(m!=MAP_FAILED);assert(!mprotect(m+page,page,PROT_NONE));
 /* Original mapped record becomes unreadable immediately after PREPARE.
  * The real initializer must complete from the independently owned copy. */
 memcpy(m,record,2696);protected_page=m;protected_bytes=page;hide_source=1;
 init(m,0x125000);assert(valid && producer.snapshot.state==GP50_CAPTURE_ACCEPTED);
 hide_source=0;
 uint8_t *short_record=m+page-2048;memset(short_record,0,2048);
 put32(short_record,0x49535456);init(short_record,0x20002074);
 assert(!valid && producer.snapshot.state==GP50_CAPTURE_REJECTED);
 assert(producer.snapshot.error==GP50_CAPTURE_E_EXTENT && (producer.snapshot.flags&GP50_CAPTURE_FALLBACK));
 /* An unbound record may be an unreadable address: no header access is allowed. */
 init(m+page,0x125001);assert(!valid && producer.snapshot.error==GP50_CAPTURE_E_EXTENT);
 FILE *f=fopen(argv[1],"rb");assert(f);assert(fread(record,1,2696,f)==2696);fclose(f);
 init(record,0x125000);assert(valid && umode && producer.snapshot.state==GP50_CAPTURE_ACCEPTED);
 uint32_t gen=producer.snapshot.generation;
 process(1);status_reg=2;run_reg=1;process(1);
 assert(!valid && !status_reg && !run_reg && producer.snapshot.state==GP50_CAPTURE_RUNTIME_ERROR);
 assert(producer.snapshot.error==0xffu && producer.snapshot.generation==gen);
 uint32_t revision=producer.snapshot.revision;process(1);assert(producer.snapshot.revision==revision);
 /* Real CRC error, including full validator PC/code bits. */
 record[128]^=1;init(record,0x125000);assert(!valid && producer.snapshot.state==GP50_CAPTURE_REJECTED);
 assert(producer.snapshot.error==E_CRC);
 f=fopen(argv[2],"rb");assert(f);assert(fread(record,1,2696,f)==2696);fclose(f);
 init(record,0x125000);assert(valid && gmode && producer.snapshot.kind==GP50_CAPTURE_GPTC);
 process(1);status_reg=2;run_reg=1;process(1);
 assert(producer.snapshot.state==GP50_CAPTURE_RUNTIME_ERROR && producer.snapshot.error==0xffu);
 record[452]^=1;init(record,0x125000);assert(!valid && producer.snapshot.error==GP50_CAPTURE_E_FORMAT);
 /* Failure publication from an old generation cannot alter new loading state. */
 gp50_capture_overlay_context c={0};c.generation=producer.snapshot.generation;
 assert(gp50_capture_arm_begin(&producer,2));c.error=0xff;
 gp50_capture_arm_overlay(&producer,GP50_CAPTURE_PROCESS,&c,0);
 assert(producer.snapshot.state==GP50_CAPTURE_LOADING);cases++;
 munmap(m,page*2);printf("%u actual capture init/process wrapper cases passed\n",cases);
 return 0;
}
