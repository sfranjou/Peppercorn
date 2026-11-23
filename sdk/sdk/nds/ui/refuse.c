/* Admission refusal in C (2026-10-20). Design and call-site evidence: analysis/firmware/ADMISSION_REFUSAL.md.
 * Every user-initiated block or model change passes one of three stock call sites; each is
 * re-pointed (one jal) at a gate here that predicts the ARM load after the change and, when the
 * change would raise it to ADM_REFUSE (thousandths) or more, makes the change a no-op:
 *   0x473f6 jal 0x452ae -> nds_adm_enable_get(group, requested): returns `requested` so 0x473f0
 *                          sees "unchanged" and stores, notifies and sends nothing.
 *   0x475de jal 0x453d0 -> nds_adm_select_apply(group, ordinal): returns 0 ("rejected") without
 *                          applying, as 0x453d0 does for an unchanged selection.
 *   0x47456 jal 0x4586a -> nds_adm_footswitch(index): skips the toggle (mask and LED byte unchanged).
 * Disabling, a cheaper model and anything that lowers or keeps the prediction are never refused.
 * Preset loads, parameter changes and the coprocessor groups are not gated. A refusal is noted
 * in the state (tick, key) and the edit page shows "CPU FULL NN%" for ADM_REFUSE_SHOW ticks
 * (nds_refuse_strip, called first by the admission edit strip) and the home title label shows it
 * too (nds_refuse_home, called first by the home-refresh router in every DRUM mode).
 * The estimate is the admission prediction (sdk/telemetry/nds/admission_costs.py predict) with
 * one group's enable bit or model id replaced; mask and ids are unaligned: byte loads only. */
#include <stdint.h>
#include "stock_api.h"
#include "admission_table.h"
#include "refuse_table.h"
#include "adm_dsp.h"

#define ST ((volatile uint32_t *)NDS_UI_STATE)
#define W32(a) (*(volatile uint32_t *)(a))

static uint32_t u32_at(const volatile uint8_t *p) {
 return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint32_t live_mask(void) { return u32_at((const volatile uint8_t *)GP50_MDATA_ENABLE_MASK); }

/* Prediction for `mask` with group `og`'s id replaced by `oid` (og >= 10: no replacement). */
static uint32_t est_of(uint32_t mask, uint32_t og, uint32_t oid, uint32_t *unknown) {
 const volatile uint8_t *md = (const volatile uint8_t *)GP50_MDATA_ENABLE_MASK;
 uint32_t est = ADM_BASE;
 *unknown = 0;
 for (uint32_t k = 0; k < ADM_GROUPS; k++) {
  const struct adm_group *g = &adm_groups[k];
  uint32_t id = g->group == og ? oid : u32_at(md + GP50_MDATA_IDS_OFFSET + 4u * g->group);
  if (!(mask >> g->group & 1u)) {
   if (g->group == 7u && id == ADM_PING_PONG_ID) est += ADM_PING_PONG_COST;
   continue;
  }
  uint32_t i = 0;
  while (i < g->count && g->rows[i].id != id) i++;
  if (i < g->count) est += g->rows[i].cost;
  else { est += ADM_UNKNOWN; *unknown = 1; }
 }
#if ADM_WITH_DSP
 uint32_t dsp = adm_dsp_of(mask, og, oid, unknown);
 if (dsp > est) est = dsp;
#endif
 return est;
}

static void note(uint32_t key) {
 irq_guard_enter();
 ST[ADM_STATE_REFUSE_TICK] = W32(GP50_TICK_COUNTER);
 ST[ADM_STATE_REFUSE_KEY] = key;                                  /* nonzero = pending display */
 irq_guard_leave();
}

/* 1 = refuse (and note it for the edit page). */
static uint32_t refuse(uint32_t before, uint32_t after, uint32_t unknown) {
 if (after < ADM_REFUSE || after <= before) return 0;
 uint32_t pct = (after + 9u) / 10u;
 note((pct * 2u | unknown) | 0x80000000u);
 return 1;
}

#ifndef ADM_CAPTURE_RULES
#define ADM_CAPTURE_RULES 0
#endif
#if ADM_CAPTURE_RULES
/* Capture-pair rules (admission table v6, 2026-11-09; oracle model_refuse.capture_violation): the DST Capture
 * (ADM_DST_CAPTURE_ID in DST) needs the cab off (1), the N->S block on (2) and no factory VTSI N->S capture (3).
 * A change that newly creates a violation is refused; the key is 0xc0000000 | reason << 1 (bit 30 = rule text).
 * Only switching on is gated (enable path; footswitch when DST or CAB turns on); turning N->S off, or selecting a
 * factory N->S slot (N->S selection is not gated), leaves the DST capture silent instead. */
static uint32_t id_with(uint32_t g, uint32_t og, uint32_t oid) {
 return g == og ? oid : u32_at((const volatile uint8_t *)GP50_MDATA_ENABLE_MASK + GP50_MDATA_IDS_OFFSET + 4u * g);
}
static uint32_t violation(uint32_t mask, uint32_t og, uint32_t oid) {
 if (!(mask >> 2 & 1u) || id_with(2u, og, oid) != ADM_DST_CAPTURE_ID) return 0;
 if (mask >> 4 & 1u) return 1;
#ifdef ADM_CAPTURE_FORCE
 if (!(mask >> 9 & 1u)) return 0;        /* v7: valid, the link filter keeps N->S loaded toward the ARM */
#else
 if (!(mask >> 9 & 1u)) return 2;
#endif
 if ((id_with(9u, og, oid) & 0xffu) < 50u) return 3;
 return 0;
}
static uint32_t refuse_rule(uint32_t mask0, uint32_t mask1, uint32_t og, uint32_t oid) {
 uint32_t v = violation(mask1, og, oid);
 if (!v || violation(mask0, 10u, 0)) return 0;
 note(0xc0000000u | v << 1);
 return 1;
}
#else
#define refuse_rule(m0, m1, og, oid) 0u
#endif

/* The v7 link filter (DST capture with N->S off) lives in dst_capture_link.c (gp50_link_filter, v7-only object). */

uint32_t nds_adm_enable_get(uint32_t group, uint32_t requested) {
 uint32_t cur = enable_get(group);
 if (group < 10u && requested && !cur) {
  uint32_t m = live_mask(), u0, u1;
  if (refuse_rule(m, m | 1u << group, 10u, 0)) return requested;
  uint32_t before = est_of(m, 10u, 0, &u0), after = est_of(m | 1u << group, 10u, 0, &u1);
  if (refuse(before, after, u1)) return requested;   /* looks unchanged to 0x473f0 */
 }
 return cur;
}

uint32_t nds_adm_select_apply(uint32_t group, uint32_t ordinal) {
 if (group < 10u && group != 4u && group != 9u && ordinal < effect_count(group)) {
  uint32_t m = live_mask(), id = effect_id_for(group, ordinal), u0, u1;
  if (refuse_rule(m, m, group, id)) return 0;
  uint32_t before = est_of(m, 10u, 0, &u0), after = est_of(m, group, id, &u1);
  if (refuse(before, after, u1)) return 0;
 }
 return select_apply(group, ordinal);
}

void nds_adm_footswitch(uint32_t index) {
 if (index < 2u) {
  uint32_t assign = u32_at((const volatile uint8_t *)GP50_FOOTSWITCH_ASSIGN + 4u * index);
  if (assign) {
   uint32_t m = live_mask(), u0, u1;
   if ((assign & ~m & 0x14u) && refuse_rule(m, m ^ assign, 10u, 0)) return;   /* rules only when DST or CAB turns on */
   uint32_t before = est_of(m, 10u, 0, &u0), after = est_of(m ^ assign, 10u, 0, &u1);
   if (refuse(before, after, u1)) return;
  }
 }
 footswitch_toggle(index);
}

/* v in 0..999 without leading zeros. */
static char *fmt_pct(uint32_t v, char *d);
/* Refusal text for `key`: "CPU FULL NN%[?]" or, bit 30, the capture-rule reason (<= 13 characters). */
static void refusal_text(uint32_t key, char *d) {
#if ADM_CAPTURE_RULES
 if (key & 0x40000000u) {
  uint32_t r = (key >> 1) & 3u;
  const char *s = r == 1u ? "CAB OFF FIRST" : r == 2u ? "N->S ON FIRST" : "N->S NOT LTTC";
  while (*s) *d++ = *s++;
  *d = 0; return;
 }
#endif
 for (const char *s = "CPU FULL "; *s; ) *d++ = *s++;
 d = fmt_pct((key & 0x7fffffffu) >> 1, d);
 *d++ = '%';
 if (key & 1u) *d++ = '?';
 *d = 0;
}
static char *fmt_pct(uint32_t v, char *d) {
 uint32_t h = v / 100u, t = v / 10u % 10u, o = v % 10u;
 if (h) *d++ = (char)('0' + h);
 if (h || t) *d++ = (char)('0' + t);
 *d++ = (char)('0' + o);
 return d;
}

/* Edit-page strip: 1 = showing the refusal (caller returns), 0 = no pending refusal (caller
 * continues with the warning logic, which redraws or restores because the shown key differs). */
uint32_t nds_refuse_strip(lv_obj_t *label, volatile uint32_t *state) {
 uint32_t key = state[ADM_STATE_REFUSE_KEY];
 if (!key) return 0;
 if (W32(GP50_TICK_COUNTER) - state[ADM_STATE_REFUSE_TICK] >= ADM_REFUSE_SHOW) {
  state[ADM_STATE_REFUSE_KEY] = 0; return 0;
 }
 if (state[ADM_STATE_WARN] && state[ADM_STATE_KEY] == key) return 1;    /* already shown */
 char text[16];
 refusal_text(key, text);
 lv_obj_set_pos(label, 0, 0);
 lv_obj_set_size(label, 160, 20);
 mod026_set_text(label, text);
 strip_label_show(label, 1);
 state[ADM_STATE_WARN] = 1; state[ADM_STATE_KEY] = key;
 return 1;
}

#if ADM_REFUSE_HOME      /* image config "refusal_home": true (MOD043+) */
/* Home page (router nds_refresh2, every home tick): while a refusal is younger than ADM_REFUSE_SHOW
 * the title label (ctx+0x34, the preset name in DRUM mode 0) shows "CPU FULL NN%". When it ends,
 * mode 0 gets the preset name back (as the MOD029 restore does) and 1 is returned; in modes 1-3 the
 * router's normal refresh redraws its own text. 1 = handled, router returns. */
#ifdef GP50_FS_AB
uint32_t gp50_fs_ab_home(uint8_t *ctx);   /* A/B footswitch messages (sdk/nds/footswitch_ab/fs_ab_ui.c) take the title first */
#endif
uint32_t nds_refuse_home(uint8_t *ctx) {
#ifdef GP50_FS_AB
 if (gp50_fs_ab_home(ctx)) return 1;
#endif
 lv_obj_t *label = *(lv_obj_t **)(ctx + 0x34);
 uint32_t key = ST[ADM_STATE_REFUSE_KEY];
 if (key && W32(GP50_TICK_COUNTER) - ST[ADM_STATE_REFUSE_TICK] < ADM_REFUSE_SHOW) {
  if (ST[ADM_STATE_HOME_SHOWN] != key) {
   char text[16];
   refusal_text(key, text);
   mod026_set_text(label, text);
   ST[ADM_STATE_HOME_SHOWN] = key;
  }
  return 1;
 }
 if (!ST[ADM_STATE_HOME_SHOWN]) return 0;
 ST[ADM_STATE_HOME_SHOWN] = 0;
 if (*(volatile uint32_t *)GP50_MOD029_DISPLAY_MODE) return 0;
 mod026_set_text(label, preset_name_text());
 return 1;
}
#endif
