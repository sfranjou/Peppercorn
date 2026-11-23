#include "capture_host.h"
uint32_t gp50_capture_host_get(uint32_t sel,uint32_t length,uint32_t ctx,
 gp50_capture_cache *cache,uint32_t now,const StockIo *io) {
 if(sel!=0x72)return 0;
 if(length!=2)return 1;
 uint8_t bytes[GP50_CAPTURE_REPLY_BYTES];
 if(!gp50_capture_cached_frame(cache,now,bytes))return 1;
 LOCAL_BUFFER(io,f,GP50_CAPTURE_REPLY_BYTES);
 if(!f)return 1;
 for(uint32_t i=0;i<GP50_CAPTURE_REPLY_BYTES;i++)IO_W8(io,f+i,bytes[i]);
 STOCK_CALL(io,0x40942,f,GP50_CAPTURE_REPLY_BYTES,ctx);
 return 1;
}
