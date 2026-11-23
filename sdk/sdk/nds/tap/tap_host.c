/* Optional MOD060 host dispatch; no released firmware advertises this command. */
#include "tap_host.h"
uint32_t tap_host_get(uint32_t sel,uint32_t length,uint32_t ctx,const StockIo *io){
 if(sel!=0x73) return 0;
 if(length!=2) return 1;
 LOCAL_BUFFER(io,f,5);
 uint32_t bpm=STOCK_CALL0(io,0x451fe);
 IO_W8(io,f,0x12);IO_W8(io,f+1,0x73);IO_W8(io,f+2,TAP_POLICY);
 IO_W8(io,f+3,bpm);IO_W8(io,f+4,bpm>>8);
 STOCK_CALL(io,0x40942,f,5,ctx);
 return 1;
}
uint32_t tap_host_set(uint32_t sel,uint32_t args,uint32_t length,uint32_t *status,const StockIo *io){
 if(sel!=0x73) return 0;
 *status=1;
 if(length!=4) return 1;
 tap_safe_interval(io_r32(io,args),io);
 *status=0; /* Well-formed zero/long intervals are successful no-ops. */
 return 1;
}
