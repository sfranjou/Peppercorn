/* MEM home page in C (DRUM mode 3; behaviour identical to MOD033-037 assembly, proved by the
 * unchanged refresh oracle cases). nds_refresh2 is the router every accepted meter-refresh call
 * site enters: mode 3 here, everything else to the home meter's `refresh` (asm, linked by name).
 * Text: "MEM" + up to three " <ABR><kib>K" (granted) or " <ABR>!<reason>" (denied), " 0K" if none. */
#include <stdint.h>
#include "stock_api.h"
#include "mem_page_table.h"

int refresh(void *ctx);   /* home_meter (asm) */

#define ST ((volatile uint32_t *)NDS_UI_STATE)
enum { S_REQUESTED = 0, S_VALID = 2, S_ERROR = 3, S_RX_TICK = 5, S_UI_TICK = 21, S_UI_VALID = 22, S_LEASE = 24 };
static const char abbr[] = "NR PREDSTAMPCABEQ MODDLYRVBNS AUX";
static const char reasons[] = "?DFXI";

static char *put(char *d, const char *s) { while (*s) *d++ = *s++; return d; }

int nds_mem_refresh(uint8_t *ctx) {
 uint32_t snap[10], valid, error, rx;
 irq_guard_enter();
 uint32_t now = *(volatile uint32_t *)GP50_TICK_COUNTER;
 if (!ST[S_UI_VALID] || (now - ST[S_UI_TICK]) >= (uint32_t)MEM_POLL_TICKS) { ST[S_UI_TICK] = now; ST[S_UI_VALID] = 1; ST[S_REQUESTED] = 1; }
 for (uint32_t i = 0; i < 10; i++) snap[i] = ST[S_LEASE + i];
 valid = ST[S_VALID]; error = ST[S_ERROR]; rx = ST[S_RX_TICK];
 irq_guard_leave();
 const uint8_t *lb = (const uint8_t *)snap;
 char text[40]; const char *s = text;
 if (!valid) s = "MEM --";
 else if (error) s = "MEM ERR";
 else if ((now - rx) >= (uint32_t)1000) s = "MEM OLD";
 else if (!snap[9]) s = "MEM --";
 else if (!lb[0]) s = "MEM NONE";
 else {
  char *d = put(text, "MEM"); uint32_t shown = 0;
  for (uint32_t g = 0; g < 11u && shown < 3u; g++) {
   uint32_t b0 = lb[8 + 2 * g], kib = lb[9 + 2 * g], st = b0 >> 4;
   if (st != 2u && st != 3u) continue;
   *d++ = ' ';
   for (uint32_t k = 0; k < 3u; k++) if (abbr[3 * g + k] != ' ') *d++ = abbr[3 * g + k];
   if (st == 3u) { uint32_t r = b0 & 15u; *d++ = '!'; *d++ = reasons[r < 5u ? r : 0u]; }
   else {
    if (kib / 100u) *d++ = (char)('0' + kib / 100u);
    if (kib / 10u) *d++ = (char)('0' + kib / 10u % 10u);
    *d++ = (char)('0' + kib % 10u); *d++ = 'K';
   }
   shown++;
  }
  if (!shown) d = put(d, " 0K");
  *d = 0;
 }
 mod026_set_text(*(lv_obj_t **)(ctx + 0x34), s);
 return 0;
}

#if MEM_WITH_REFUSAL      /* refuse_c (sdk/nds/ui/refuse.c): home CPU FULL message first */
uint32_t nds_refuse_home(uint8_t *ctx);
#endif
int nds_refresh2(uint8_t *ctx) {
#if MEM_WITH_REFUSAL
 if (nds_refuse_home(ctx)) return 0;
#endif
 if (*(volatile uint32_t *)GP50_MOD029_DISPLAY_MODE == 3u) return nds_mem_refresh(ctx);
 return refresh(ctx);
}
