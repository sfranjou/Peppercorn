/* Called by the single own-command dispatcher. No alternate parser or queue. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "../own/stock_io.h"
#include "component.h"
#include "gp50.h"   /* GP50_HOST_BYTES_MAX */
uint32_t gp50_component_host_get(uint32_t selector,uint32_t length,uint32_t ctx,const StockIo *io) {
    if(!gp50_components_has(selector)) return 0;
    if(length!=2) return 1;
    uint8_t payload[GP50_HOST_BYTES_MAX];
    uint32_t n=gp50_components_read(selector,payload,sizeof(payload));
    LOCAL_BUFFER(io,f,GP50_HOST_BYTES_MAX+2);
    if(n) {
        IO_W8(io,f,0x12);IO_W8(io,f+1,selector);
        for(uint32_t i=0;i<n;i++) IO_W8(io,f+2+i,payload[i]);
        n+=2;
    } else {
        IO_W8(io,f,0x14);IO_W8(io,f+1,0x08);IO_W8(io,f+2,1);n=3;
    }
    STOCK_CALL(io,0x40942,f,n,ctx);
    return 1;
}
uint32_t gp50_component_host_set(uint32_t selector,uint32_t args,uint32_t length,uint32_t *status,const StockIo *io) {
    if(!gp50_components_has(selector)) return 0;
    *status=1;
    if(length>GP50_HOST_BYTES_MAX) return 1;
    uint8_t payload[GP50_HOST_BYTES_MAX];
    for(uint32_t i=0;i<length;i++) payload[i]=IO_R8(io,args+i);
    *status=gp50_components_write(selector,payload,length);
    return 1;
}
