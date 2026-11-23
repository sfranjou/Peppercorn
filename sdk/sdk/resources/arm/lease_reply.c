/* Schema-2 60f0 reply: the 44 B schema-1 telemetry fields plus a 36 B lease
 * summary of the resident adapter (MOD033 candidate). Foreground link dispatch;
 * same PRIMASK-masked snapshot as gp50_telemetry_reply. No pool access.
 * Lease block (36 B): u8 present, u8 groups(11), u16 transitions(low 16),
 * u32 granted bytes total, 11 x {u8 state<<4|reason, u8 KiB rounded up, 255 max},
 * zero padding. present=0 (adapter signature absent) leaves the block zero. */
#include "gp50_resident.h"
#ifdef GP50_STOCK_GR_REPLY
#include "stock_gr_reply.h"
#endif
#define TBASE 0x290fffb0u
#define TMAGIC 0x544c3030u
extern void gp50_stock_reply(const void *,uint32_t);
static inline uint32_t tget(unsigned o) {
 volatile uint16_t *p=(volatile uint16_t *)(TBASE+o);
 uint32_t low=p[0],high=p[1];return low|(high<<16);
}
void gp50_lease_reply(void) {
 uint32_t pkt[20],primask,i;
 pkt[0]=(80u<<16)|0x60f0u;pkt[1]=2;
 for(i=11;i<20;i++)pkt[i]=0;
 __asm volatile("mrs %0, primask\n cpsid i":"=r"(primask)::"memory");
 if(tget(0)==TMAGIC) {
  /* Same order as schema 1: completed, flags, arm last/peak, dsp last/peak, dsp count/block, frames. */
  pkt[2]=tget(4);pkt[3]=tget(32);pkt[4]=tget(16);pkt[5]=tget(20);
  pkt[6]=tget(24);pkt[7]=tget(28);pkt[8]=tget(8);pkt[9]=tget(12);pkt[10]=tget(40);
 } else {for(i=2;i<11;i++)pkt[i]=0;}
 const volatile gp50_resident *r=(const volatile gp50_resident *)GP50_RESIDENT_BASE;
 if(r->signature==GP50_RESIDENT_SIGNATURE && r->complement==~GP50_RESIDENT_SIGNATURE) {
  uint32_t total=0,w0=1u|(GP50_RES_GROUPS<<8)|((r->transitions&0xffffu)<<16);
  for(i=0;i<GP50_RES_GROUPS;i++) {
   uint32_t state=r->view[i].state&3u,reason=r->view[i].reason&15u,bytes=r->view[i].bytes;
   uint32_t kib=(bytes+1023u)/1024u;if(kib>255u)kib=255u;
   if(state==GP50_LEASE_GRANTED)total+=bytes;
   pkt[13+i/2]|=((state<<4)|reason|(kib<<8))<<(16*(i&1));
  }
  pkt[11]=w0;pkt[12]=total;
#ifdef GP50_METER_REPLY
  /* MOD034: meter mailbox -> lease bytes 30..35 (pkt[18] high half, pkt[19] low half):
   * [30..31] peak-hold GR (then cleared), [32] group, [33] bit0 valid, bit1 fresh. */
  volatile uint16_t *mb=(volatile uint16_t *)(GP50_RESIDENT_BASE+288u);
  if(mb[0]==0x4752u) {
#ifdef GP50_STOCK_GR_REPLY
   uint32_t seq=mb[3],fresh=seq!=mb[5];mb[5]=seq;
#else
   uint32_t fresh=mb[3]!=mb[5];mb[5]=mb[3];
#endif
   uint32_t hold=mb[4];mb[4]=0;
   pkt[18]|=hold<<16;pkt[19]=(mb[1]&0xffu)|((1u|(fresh<<1))<<8);
  } else pkt[19]=0xffu;
#endif
#ifdef GP50_STOCK_GR_REPLY
  stock_gr_reply(pkt,r);
#endif
 }
 __asm volatile("msr primask, %0"::"r"(primask):"memory");
 gp50_stock_reply(pkt,80);
}
