#include "arm_lifecycle.h"
static uint32_t get16(const volatile uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8;}
static uint32_t get32(const volatile uint8_t *p) {return get16(p)|get16(p+2)<<16;}
void gp50_capture_live_geometry(const volatile uint8_t *f,
 const volatile uint8_t *b,const volatile uint8_t *c,
 gp50_capture_geometry *factory,gp50_capture_geometry *user) {
 *factory=(gp50_capture_geometry){0};*user=(gp50_capture_geometry){0};
 if(get32(f)!=0 || get32(f+4)!=0x200u || get16(f+8)!=4096u || get16(f+10)!=256u)return;
 if(get32(b)==0x20001ef4u && get32(b+4)==0x122000u &&
    get16(b+8)==4096u && get16(b+10)==4096u &&
    b[12]==54u && b[13]==1u && b[14]==50u && b[15]==16u)
  *factory=(gp50_capture_geometry){0x122000u,0x36000u,4096u,3u};
 if(get32(c)==0x20001ef4u && get32(c+4)==0x158000u &&
    get16(c+8)==4096u && get16(c+10)==120u && get16(c+34)==4096u &&
    c[30]==3u && c[28]==100u && c[29]==56u)
  *user=(gp50_capture_geometry){0x158000u,0x78000u,4096u,3u};
}
#ifndef GP50_CAPTURE_NATIVE_LIFECYCLE
#define ARM_STATE ((gp50_capture_arm *)GP50_CAPTURE_ARM_BASE)
static uint32_t enter(void) {uint32_t p;__asm volatile("mrs %0, primask\n cpsid i":"=r"(p)::"memory");return p;}
static void leave(uint32_t p) {__asm volatile("msr primask, %0"::"r"(p):"memory");}
extern uint32_t gp50_capture_stock_lookup(uint32_t);
uint32_t gp50_capture_lookup_call(uint32_t id,uint32_t group) {
 uint32_t gen=0,p=enter();
 if(group==9u) {
  gp50_capture_arm_retire(ARM_STATE);
  if(id>=41u && id<121u)gen=gp50_capture_arm_begin(ARM_STATE,(uint8_t)(id-41u));
 }
 leave(p);
 uint32_t record=gp50_capture_stock_lookup(id);
 if(group==9u && gen) {
  gp50_capture_geometry b,c;p=enter();
  gp50_capture_live_geometry((const volatile uint8_t *)0x20001ef4u,
   (const volatile uint8_t *)0x20003778u,(const volatile uint8_t *)0x20002884u,&b,&c);
  (void)gp50_capture_arm_bind(ARM_STATE,gen,record,&b,&c);leave(p);
 }
 return record;
}
void gp50_capture_retire_group(uint32_t group) {
 if(group!=9u)return;
 gp50_capture_retire_all();
}
void gp50_capture_retire_all(void) {uint32_t p=enter();gp50_capture_arm_retire(ARM_STATE);leave(p);}
void gp50_capture_writer_enter(void) {uint32_t p=enter();(void)gp50_capture_arm_write_enter(ARM_STATE);leave(p);}
void gp50_capture_writer_leave(void) {uint32_t p=enter();gp50_capture_arm_write_leave(ARM_STATE);leave(p);}
#endif
