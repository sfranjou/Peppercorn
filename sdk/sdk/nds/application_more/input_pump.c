/* Direct build of compared source; normal entry ABI only. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "../own/stock_io.h"
/* Original timer call site0x49c7e is hooked by legacy_ui_c. Replacing the
 * whole dispatcher must preserve that hook explicitly. wah_poll invokes
 * encoder debounce first and then the auto-engage policy. */
extern uint32_t wah_poll(const StockIo *io);
#define GP50_INPUT_ENCODER_POLL(io) wah_poll(io)
#define input_encoder_debounce nds_more_49b52
#define input_timer_dispatch nds_more_49c58
#include "../../../firmware/reconstructed/nds/input_pump.c"
