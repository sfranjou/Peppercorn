/* Pedal build of firmware/reconstructed/nds/diagnostics.c (MOD056+, feature diagnostics_c; analysis/firmware/NDS_CODE_ROOM.md
 * section 8.3): our diagnostics assembly of 0x16c6c0..0x16cb60 (MOD002/030 load bridge, MOD007 USB guard, MOD016 peek)
 * runs the readable source compared with it (scripts/study_nds_diagnostics.py), compiled with plain loads/stores and
 * direct calls (GP50_CATALOG_DIRECT; the StockIo pointer is never dereferenced, so a stock caller may leave anything in
 * that register). Entries: diag_gui, diag_service, diag_finite, diag_host, diag_putword, diag_usb_guard, diag_peek.
 * Not compiled into the image: diag_dispatch and diag_receive. Stock link_receive 0x46a0a enters them mid-body (the
 * telemetry dispatch stub, a5 = command, s0 = received count) and they leave by tail jumps into its body (0x46aba with
 * a5 intact, 0x46b7a on link_receive's frame), which C cannot express; they stay byte-faithful assembly stubs of the
 * feature (diag_dispatch_asm / diag_receive_asm, scripts/nds_ui/features/diagnostics_c.py) and the receive stub calls the
 * C diag_finite. Their C bodies here are unreferenced and dropped by --gc-sections. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "../own/stock_io.h"
#include "../own/diagnostics.h"
#define NOINLINE __attribute__((noinline))
/* Every entry is a real function at its own address: stock code (0x431dc jal, the 11 15 / 12 50 table words), the
 * receive stub and the image proof (scripts/verify_nds_generic_image.py --remap) reach each one directly. */
NOINLINE uint32_t diag_gui(const StockIo *io);
NOINLINE uint32_t diag_service(const StockIo *io);
NOINLINE uint32_t diag_finite(uint32_t bits, const StockIo *io);
NOINLINE uint32_t diag_host(uint32_t context, const StockIo *io);
NOINLINE uint32_t diag_putword(uint32_t value, uint32_t destination, const StockIo *io);
NOINLINE uint32_t diag_usb_guard(uint32_t object, uint32_t length, const StockIo *io);
NOINLINE uint32_t diag_peek(uint32_t request, const StockIo *io);
#include "../own/diagnostics.c"
