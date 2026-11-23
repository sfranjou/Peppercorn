/* Home-page processing meter in C (DRUM modes 1/2; behaviour identical to MOD029-037 assembly,
 * proved by the unchanged refresh and format oracle cases). `refresh` keeps its asm name: the
 * MEM-page router and the MOD029 refresh call sites enter it. Mode 1 (ARM) text comes from the
 * admission feature when it is linked (weak symbol), else the raw "ARM~x.xx" text. */
#include <stdint.h>
#include "stock_api.h"
#include "home_meter_table.h"

void nds_cpu_home_text(uint32_t has_measurement, uint32_t raw, char *buf) __attribute__((weak));

#define ST ((volatile uint32_t *)NDS_UI_STATE)
enum { S_REQUESTED = 0, S_VALID = 2, S_ERROR = 3, S_RX_TICK = 5, S_FLAGS = 9, S_ARM_LAST = 10,
       S_DSP_LAST = 12, S_PROGRESS = 17, S_UI_TICK = 21, S_UI_VALID = 22 };

/* "ARM~d.dd"/"DSP~d.dd": exact truncation raw*100/262244 via quotient/remainder; >= 10.0 "HIGH". */
void raw_text(uint32_t mode, uint32_t raw, char *d) {
 const char *p = mode == 1u ? "ARM~" : "DSP~";
 for (uint32_t i = 0; i < 4u; i++) d[i] = p[i];
 uint32_t q = raw / HOME_RAW_FULL, r = raw % HOME_RAW_FULL;
 if (q >= 10u) { d[4] = 'H'; d[5] = 'I'; d[6] = 'G'; d[7] = 'H'; d[8] = 0; return; }
 uint32_t f = r * 100u / HOME_RAW_FULL;
 d[4] = (char)('0' + q); d[5] = '.'; d[6] = (char)('0' + f / 10u); d[7] = (char)('0' + f % 10u); d[8] = 0;
}

int refresh(uint8_t *ctx) {
 uint32_t mode = *(volatile uint32_t *)GP50_MOD029_DISPLAY_MODE;
 if (!mode) return 0;
 irq_guard_enter();
 uint32_t now = *(volatile uint32_t *)GP50_TICK_COUNTER;
 if (!ST[S_UI_VALID] || (now - ST[S_UI_TICK]) >= (uint32_t)HOME_POLL_TICKS) { ST[S_UI_TICK] = now; ST[S_UI_VALID] = 1; ST[S_REQUESTED] = 1; }
 uint32_t valid = ST[S_VALID], error = ST[S_ERROR], rx = ST[S_RX_TICK], flags = ST[S_FLAGS],
          arm = ST[S_ARM_LAST], dsp = ST[S_DSP_LAST], progress = ST[S_PROGRESS];
 irq_guard_leave();
 const uint32_t arm_mode = mode == 1u;
 uint32_t has_measurement = 0;
 char buf[32]; const char *text = buf;
 if (!valid) text = arm_mode ? "ARM --" : "DSP --";
 else if (error) text = arm_mode ? "ARM ERR" : "DSP ERR";
 else if ((now - rx) >= (uint32_t)1000) text = arm_mode ? "ARM OLD" : "DSP OLD";
 else if (progress) text = arm_mode ? "ARM HOLD" : "DSP HOLD";
 else if (!(flags & 1u)) text = arm_mode ? "ARM --" : "DSP --";
 else if (arm_mode) { has_measurement = 1; raw_text(mode, arm, buf); }
 else if (!(flags & 4u)) text = "DSP IDLE";
 else raw_text(mode, dsp, buf);
 if (arm_mode && nds_cpu_home_text) { nds_cpu_home_text(has_measurement, arm, buf); text = buf; }
 mod026_set_text(*(lv_obj_t **)(ctx + 0x34), text);
 return 0;
}
