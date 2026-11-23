/* Host-only guarded-read and lifecycle tests; no hardware synchronization claim. */
#include <assert.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdio.h>
#include "arm_producer.h"
static unsigned cases;
static void records(void) {
 unsigned page=(unsigned)sysconf(_SC_PAGESIZE);
 uint8_t *m=mmap(0,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
 assert(m!=MAP_FAILED);assert(!mprotect(m+page,page,PROT_NONE));
 const uint32_t magics[]={0,0x11223344u,0x49535456u,0x43545047u,0x4e355047u,0x4e355047u,0x50355047u};
 const unsigned full[]={4,4,2696,2696,1520,1996,136};
 const unsigned kinds[]={1,0,2,5,3,3,4};
 for(unsigned k=0;k<7;k++) {
  uint8_t data[4096]={0};uint32_t magic=magics[k];memcpy(data,&magic,4);
  uint32_t version=k==4?2:k==5?3:1;memcpy(data+4,&version,4);
  uint32_t taps=704;memcpy(data+104,&taps,4);memcpy(data+580,&taps,4);data[16]=2;
  for(unsigned n=0;n<=4096;n++) {
   uint8_t *p=m+page-n;memcpy(p,data,n);
   gp50_capture_record_check c=gp50_capture_record_preflight(p,n);
   assert(c.kind==(n<4?0:kinds[k]));
   if(n>=4 && k>=4) {assert(!c.run && c.state==GP50_CAPTURE_REJECTED && c.error==GP50_CAPTURE_E_FORMAT);}
   else if(n<full[k]) {assert(!c.run && c.state==GP50_CAPTURE_REJECTED && c.error==GP50_CAPTURE_E_EXTENT);}
   else if(k<2)assert(!c.run && c.state==GP50_CAPTURE_UNSUPPORTED && !c.error);
   else assert(c.run && c.state==GP50_CAPTURE_LOADING && c.bytes==full[k] && !c.error);
   cases++;
  }
 }
 assert(!gp50_capture_record_preflight(0,UINT32_MAX).run);cases++;
 munmap(m,page*2);
}
static void extent(void) {
 gp50_capture_geometry b={0x122000,0x36000,4096,3},c={0x158000,0x78000,4096,3};
 for(uint32_t p=0x110000;p<0x1e0000;p+=127) {
  uint8_t fallback=99;
  unsigned expected=(!(p&4095) && ((p>=0x125000 && p<0x157000)||(p>=0x15b000 && p<0x1d0000)))?4096:0;
  assert(gp50_capture_record_extent(p,&b,&c,1,&fallback)==expected && !fallback);cases++;
 }
 for(unsigned i=0;i<50;i++) {
  uint8_t f;assert(gp50_capture_record_extent(0x125000+i*4096,&b,&c,1,&f)==4096);cases++;
 }
 for(unsigned i=0;i<117;i++) {
  uint8_t f;assert(gp50_capture_record_extent(0x15b000+i*4096,&b,&c,1,&f)==4096);cases++;
 }
 uint8_t f;assert(gp50_capture_record_extent(0x20002074,0,0,1,&f)==2048 && f);cases++;
 for(unsigned transaction=0;transaction<4;transaction++) {
  uint32_t e=gp50_capture_record_extent(0x125000,&b,&c,transaction,&f);
  assert(e==(transaction==1?4096u:0u));cases++;
 }
 for(unsigned word=0;word<4;word++) {
  gp50_capture_geometry bad=b;uint32_t *words=(uint32_t *)&bad;words[word]^=1;
  assert(!gp50_capture_record_extent(0x125000,&bad,&c,1,&f));cases++;
  bad=c;words=(uint32_t *)&bad;words[word]^=1;
  assert(!gp50_capture_record_extent(0x15b000,&b,&bad,1,&f));cases++;
 }
 assert(!gp50_capture_record_extent(UINT32_MAX,&b,&c,1,&f));cases++;
}
static void lifecycle(void) {
 gp50_capture_geometry b={0x122000,0x36000,4096,3},c={0x158000,0x78000,4096,3};
 for(unsigned slot=0;slot<GP50_CAPTURE_SLOTS;slot++)for(unsigned iteration=0;iteration<16;iteration++) {
  gp50_capture_arm a;memset(&a,0xa5,sizeof a);gp50_capture_snapshot snap;
  gp50_capture_arm_copy(&a,&snap);assert(snap.state==0 && snap.slot==255);
  gp50_capture_arm_reset(&a);assert(a.snapshot.slot==255);
  uint32_t old=gp50_capture_arm_begin(&a,(uint8_t)slot);assert(old);
  uint32_t gen=gp50_capture_arm_begin(&a,(uint8_t)slot);assert(gen==old+1);
  /* User slots 50..79 bind log-structured C records; factory slots B records. */
  uint32_t p=(iteration&1)?0x20002074:slot<50?0x125000:0x15b000+(slot-50)*4096*3;
  assert(!gp50_capture_arm_bind(&a,old,p,&b,&c));
  assert(gp50_capture_arm_bind(&a,gen,p,&b,&c));
  gp50_capture_arm_copy(&a,&snap);assert(gp50_capture_valid(&snap) && snap.state==1);
  uint32_t bytes;assert(!gp50_capture_arm_input(&a,p+1,&bytes) && !bytes);
  assert(gp50_capture_arm_input(&a,p,&bytes)==gen && bytes==((iteration&1)?2048u:4096u));
  assert(!gp50_capture_arm_finish(&a,old,5,2,0));
  assert(gp50_capture_arm_finish(&a,gen,5,2,0));
  assert(!!(a.snapshot.flags&4)==(iteration&1));
  assert(gp50_capture_arm_bypass(&a,gen,1));
  assert(gp50_capture_arm_watchdog(&a,gen,0xff123456));assert(a.snapshot.error==0xff123456);
  assert(!gp50_capture_arm_bypass(&a,gen,0));
  assert(gp50_capture_arm_write_enter(&a));assert(a.snapshot.state==6);
  assert(gp50_capture_arm_write_enter(&a));assert(a.writers==2);
  assert(!gp50_capture_arm_begin(&a,(uint8_t)slot));
  assert(!gp50_capture_arm_input(&a,p,&bytes) && !bytes);
  assert(!gp50_capture_arm_finish(&a,gen,5,2,0));
  gp50_capture_arm_write_leave(&a);assert(a.writers==1);gp50_capture_arm_write_leave(&a);assert(!a.writers);
  gen=gp50_capture_arm_begin(&a,(uint8_t)slot);assert(gen);
  assert(!gp50_capture_arm_bind(&a,gen,UINT32_MAX,&b,&c));assert(a.snapshot.state==3 && a.snapshot.error==0x10001);
  assert(gp50_capture_valid(&a.snapshot));
  a.snapshot.generation=UINT32_MAX;assert(!gp50_capture_arm_begin(&a,(uint8_t)slot));
  gp50_capture_arm_copy(&a,&snap);assert(snap.state==0 && snap.slot==255);
  assert(!gp50_capture_arm_begin(&a,(uint8_t)slot));cases++;
 }
 for(unsigned slot=GP50_CAPTURE_SLOTS;slot<256;slot++) {
  gp50_capture_arm a;gp50_capture_arm_reset(&a);
  assert(!gp50_capture_arm_begin(&a,(uint8_t)slot) && a.snapshot.slot==255);cases++;
 }
}
static void write_faults(void) {
 gp50_capture_geometry b={0x122000,0x36000,4096,3},c={0x158000,0x78000,4096,3};
 for(unsigned depth=0;depth<8;depth++)for(unsigned accepted=0;accepted<2;accepted++) {
  gp50_capture_arm a;gp50_capture_snapshot snap;uint32_t extent=99;
  gp50_capture_arm_reset(&a);uint32_t gen=gp50_capture_arm_begin(&a,0);
  assert(gp50_capture_arm_bind(&a,gen,0x125000,&b,&c));
  if(accepted)assert(gp50_capture_arm_finish(&a,gen,5,2,0));
  for(unsigned i=0;i<depth;i++)assert(gp50_capture_arm_write_enter(&a));
  gp50_capture_arm_write_fault(&a);
  assert(!a.record && !a.extent && !a.record_generation && a.writers==depth);
  gp50_capture_arm_copy(&a,&snap);assert(gp50_capture_valid(&snap) && snap.state==0);
  assert(!gp50_capture_arm_input(&a,0x125000,&extent) && !extent);
  assert(!gp50_capture_arm_bind(&a,gen,0x125000,&b,&c));
  assert(!gp50_capture_arm_finish(&a,gen,5,2,0));
  assert(!gp50_capture_arm_bypass(&a,gen,1));
  assert(!gp50_capture_arm_watchdog(&a,gen,1));
  for(unsigned i=0;i<depth+1;i++)gp50_capture_arm_write_leave(&a);
  assert(!a.writers && !gp50_capture_arm_begin(&a,0));
  gp50_capture_arm_retire(&a);gp50_capture_arm_write_fault(&a);
  assert(!gp50_capture_arm_write_enter(&a));
  gp50_capture_arm_copy(&a,&snap);assert(snap.state==0);
  gp50_capture_arm_reset(&a);assert(gp50_capture_arm_begin(&a,0));cases++;
 }
}
static void startup_fault_order(void) {
 gp50_capture_arm a;gp50_capture_snapshot snap;
 for(unsigned initial=0;initial<3;initial++) {
  memset(&a,0xa5,sizeof a);
  /* Model the exact two early stores, then a fault before C startup. */
  a.ready=0;a.complement=0;
  if(initial==1)gp50_capture_arm_write_fault(&a);
  if(initial==2) {gp50_capture_arm_write_fault(&a);gp50_capture_arm_write_fault(&a);}
  gp50_capture_arm_startup(&a);
  if(initial) {
   assert(!a.ready && a.complement==GP50_CAPTURE_ARM_FAULT);
   gp50_capture_arm_copy(&a,&snap);assert(snap.state==0);
   assert(!gp50_capture_arm_begin(&a,0));
   gp50_capture_arm_write_leave(&a);gp50_capture_arm_retire(&a);
   gp50_capture_arm_startup(&a);assert(!gp50_capture_arm_begin(&a,0));
   /* A real new boot's early stores clear the old marker. */
   a.ready=0;a.complement=0;gp50_capture_arm_startup(&a);
  }
  assert(gp50_capture_arm_begin(&a,0));cases++;
 }
}
int main(void) {records();extent();lifecycle();write_faults();startup_fault_order();printf("%u guarded-read, extent and producer cases passed\n",cases);return 0;}
