/* Admission warning / CPU % in C (first C port; behaviour identical to the MOD037 assembly,
 * proved by the unchanged oracle cases). Design: analysis/firmware/ADMISSION.md.
 * Entered from two small asm hooks in scripts/nds_ui/features/admission.py:
 *   home ARM page:  nds_cpu_home_text(has_measurement, raw, buf) fills "CPU NN%[!][?]"
 *   edit pages:     nds_cpu_edit_strip(ctx, strip_label, state) shows/clears "CPU HIGH NN%[?]"
 * Cost table, constants and the state layout come from the generated admission_table.h. */
#include <stdint.h>
#include "stock_api.h"
#include "admission_table.h"
#include "adm_dsp.h"

/* Predicted ARM load in thousandths of the ARM ratio; *unknown set when an enabled ARM-side
 * group holds an effect without a measured cost. Mask and ids are unaligned: byte loads only. */
static uint32_t u32_at(const volatile uint8_t *p) {
 return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint32_t est_compute(uint32_t *unknown) {
 const volatile uint8_t *md = (const volatile uint8_t *)GP50_MDATA_ENABLE_MASK;
 uint32_t mask = (uint32_t)md[0] | (uint32_t)md[1] << 8, est = ADM_BASE;
 *unknown = 0;
 for (uint32_t k = 0; k < ADM_GROUPS; k++) {
  const struct adm_group *g = &adm_groups[k];
  uint32_t id = u32_at(md + GP50_MDATA_IDS_OFFSET + 4u * g->group);
  if (!(mask >> g->group & 1u)) {
   if (g->group == 7u && id == ADM_PING_PONG_ID) est += ADM_PING_PONG_COST;   /* costs the same bypassed */
   continue;
  }
  uint32_t i = 0;
  while (i < g->count && g->rows[i].id != id) i++;
  if (i < g->count) est += g->rows[i].cost;
  else { est += ADM_UNKNOWN; *unknown = 1; }
 }
#if ADM_WITH_DSP          /* table v4+: the one number is max(ARM, DSP) */
 uint32_t dsp = adm_dsp_of(mask, 10u, 0, unknown);
 if (dsp > est) est = dsp;
#endif
 return est;
}
/* Estimated load in percent (rounded up), the figure CPU protection and the home CPU text start from (SDK gp50_dsp_load). */
uint32_t nds_cpu_estimate_percent(void) { uint32_t unknown; return (est_compute(&unknown) + 9u) / 10u; }
/* v in 0..999 as decimal without leading zeros; returns the end pointer. */
static char *fmt_pct(uint32_t v, char *d) {
 uint32_t h = v / 100u, t = v / 10u % 10u, o = v % 10u;
 if (h) *d++ = (char)('0' + h);
 if (h || t) *d++ = (char)('0' + t);
 *d++ = (char)('0' + o);
 return d;
}
static char *put(char *d, const char *s) { while (*s) *d++ = *s++; return d; }

/* Measured ARM ratio raw -> percent rounded up, 999 at or above 10.0 (as MOD037). */
static uint32_t measured_pct(uint32_t raw) {
 uint32_t q = raw / ADM_ARM_RAW_FULL, r = raw % ADM_ARM_RAW_FULL;
 if (q >= 10u) return 999u;
 uint32_t m = q * 100u + (r * 100u + ADM_ARM_RAW_FULL - 1u) / ADM_ARM_RAW_FULL;
 return m >= 1000u ? 999u : m;
}
void nds_cpu_home_text(uint32_t has_measurement, uint32_t raw, char *buf) {
 uint32_t unknown, pct = (est_compute(&unknown) + 9u) / 10u;
 if (has_measurement) { uint32_t m = measured_pct(raw); if (pct < m) pct = m; }
 char *d = fmt_pct(pct, put(buf, "CPU "));
 *d++ = '%';
 if (pct >= ADM_WARN_PCT) *d++ = '!';
 if (unknown) *d++ = '?';
 *d = 0;
}
#if ADM_WITH_REFUSAL      /* refuse_c feature (sdk/nds/ui/refuse.c): a pending refusal message wins */
uint32_t nds_refuse_strip(lv_obj_t *label, volatile uint32_t *state);
#endif
void nds_cpu_edit_strip(void *ctx, lv_obj_t *label, volatile uint32_t *state) {
#if ADM_WITH_REFUSAL
 if (nds_refuse_strip(label, state)) return;
#endif
 uint32_t unknown, pct = (est_compute(&unknown) + 9u) / 10u;
 if (pct < ADM_WARN_PCT) {
  if (state[ADM_STATE_WARN]) { state[ADM_STATE_WARN] = 0; state[ADM_STATE_KEY] = 0; mod026_restore_ctx(ctx); }
  return;
 }
 uint32_t key = pct * 2u | unknown;
 if (state[ADM_STATE_WARN] && state[ADM_STATE_KEY] == key) return;   /* redraw only on change */
 char text[16], *d = fmt_pct(pct, put(text, "CPU HIGH "));
 *d++ = '%';
 if (unknown) *d++ = '?';
 *d = 0;
 lv_obj_set_pos(label, 0, 0);
 lv_obj_set_size(label, 160, 20);
 mod026_set_text(label, text);
 strip_label_show(label, 1);
 state[ADM_STATE_WARN] = 1; state[ADM_STATE_KEY] = key;
}
