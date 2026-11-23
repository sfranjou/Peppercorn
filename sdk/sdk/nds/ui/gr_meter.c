/* Gain-reduction strip on the edit page. Window-4 tick entry: the stock tick site jumps here directly.
 *  - chains the MOD026 editor tick first;
 *  - assignment prompt active: drop the meter (MOD026 owns the strip);
 *  - selected effect supplies a meter: build once, then poll telemetry at ~10 Hz and show the reading;
 *  - legacy builds use the MOD035/037 GR Comp bar with ticks;
 *  - any other edit page: remove the meter if shown, then the admission strip warning.
 * Geometry and state offsets come from the generated gr_meter_table.h. */
#include <stdint.h>
#include "stock_api.h"
#include "gr_meter_table.h"

void nds_cpu_edit_strip(void *ctx, lv_obj_t *label, volatile uint32_t *state);   /* admission.c */
#if defined(GP50_FEATURE_GR_METER) || defined(GP50_FEATURE_ASSIGNMENT)
#include "components/platform/gp50_features.h"
#endif
#define ST ((volatile uint32_t *)NDS_UI_STATE)
enum { S_REQUESTED = 0, S_VALID = 2, S_ERROR = 3, S_RX_TICK = 5, S_UI_TICK = 21, S_UI_VALID = 22,
       S_SHOWN = 23, S_LEASE = 24, S_LEASE_VALID = 33, S_METER = 34, S_WARN = 35, S_KEY = 36 };

static void build(lv_obj_t *label, const char *title) {
 lv_obj_set_pos(label, 0, 0);
 lv_obj_set_size(label, GR_STRIP_W, GR_STRIP_H);
#ifdef GP50_FEATURE_GR_METER
 mod026_set_text(label, " ");   /* the strip's own text is centred under the bar: the title gets its own label */
#else
 mod026_set_text(label, title);
#endif
 strip_label_show(label, 1);
 lv_obj_t *box = lv_obj_create(label);
 lv_obj_remove_style(box, 0, GR_REMOVE_ALL);
 lv_obj_set_size(box, GR_STRIP_W, GR_STRIP_H);
 lv_obj_set_pos(box, 0, 0);
 lv_obj_t *bar = lv_bar_create(box);
#ifdef GP50_FEATURE_GR_METER
 /* Match the stock parameter row's track and indicator styling (widget 0x27498). */
 lv_obj_remove_style(bar, 0, 0x30000u);
 lv_obj_remove_style(bar, 0, LV_PART_MAIN);
 lv_obj_set_size(bar, GR_FBAR_W, GR_FBAR_H);
 lv_obj_set_pos(bar, GR_FBAR_X, GR_FBAR_Y);
 lv_obj_set_style_bg_opa(bar, 255, LV_PART_MAIN);
 lv_obj_set_style_bg_color(bar, 0xcc11, LV_PART_MAIN);   /* stock dark blue */
 lv_obj_set_style_bg_opa(bar, 255, LV_PART_INDICATOR);
 lv_obj_set_style_bg_color(bar, 0xfe23, LV_PART_INDICATOR);   /* stock blue */
#else
 lv_obj_set_size(bar, GR_BAR_W, GR_BAR_H);
 lv_obj_set_pos(bar, GR_BAR_X, GR_BAR_Y);
#endif
 lv_bar_set_range(bar, 0, GR_BAR_MAX);
 lv_obj_set_style_radius(bar, GR_BAR_RADIUS, LV_PART_MAIN);
 lv_obj_set_style_radius(bar, GR_BAR_RADIUS, LV_PART_INDICATOR);
#ifndef GP50_FEATURE_GR_METER
 static const uint8_t ticks[] = GR_TICKS_X;
 for (uint32_t i = 0; i < sizeof ticks; i++) {
  lv_obj_t *t = lv_obj_create(box);
  lv_obj_remove_style(t, 0, GR_REMOVE_ALL);
  lv_obj_set_size(t, GR_TICK_W, GR_TICK_H);
  lv_obj_set_pos(t, ticks[i], GR_TICK_Y);
  lv_obj_set_style_bg_color(t, 0xffff, 0);
  lv_obj_set_style_bg_opa(t, 255, 0);
 }
#endif
 lv_obj_t *value = lv_label_create(box);
#ifdef GP50_FEATURE_GR_METER
 lv_obj_set_pos(value, GR_TEXT_RIGHT, GR_TEXT_Y);   /* update_strip right-aligns it */
 lv_obj_t *name = lv_label_create(box);             /* child 2 */
 lv_obj_set_pos(name, GR_LABEL_X, GR_TEXT_Y);
 lv_label_set_text(name, title);
#else
 lv_obj_set_pos(value, GR_VALUE_X, GR_VALUE_Y);
#endif
 ST[S_METER] = (uint32_t)box; ST[S_SHOWN] = 1;
}

#ifndef GP50_FEATURE_GR_METER
/* Value text "d.d"/"dd.d" from peak-hold gain reduction in 0.01 dB; returns bar tenths. */
static uint32_t gr_text(uint32_t hold, char *d) {
 if (hold > 6000u) hold = 6000u;
 uint32_t t = (hold + 5u) / 10u;            /* tenths of a dB, 0..600 */
 if (t / 100u) *d++ = (char)('0' + t / 100u);
 *d++ = (char)('0' + t / 10u % 10u);
 *d++ = '.'; *d++ = (char)('0' + t % 10u); *d = 0;
 return t;
}

static void update(lv_obj_t *box) {
 lv_obj_t *bar = lv_obj_get_child(box, 0), *value = lv_obj_get_child(box, 4);
 uint32_t snap[10], valid, error, rx;
 irq_guard_enter();
 uint32_t now = *(volatile uint32_t *)GP50_TICK_COUNTER;
 if (!ST[S_UI_VALID] || (now - ST[S_UI_TICK]) >= (uint32_t)GR_POLL_TICKS) { ST[S_UI_TICK] = now; ST[S_UI_VALID] = 1; ST[S_REQUESTED] = 1; }
 for (uint32_t i = 0; i < 10; i++) snap[i] = ST[S_LEASE + i];
 valid = ST[S_VALID]; error = ST[S_ERROR]; rx = ST[S_RX_TICK];
 irq_guard_leave();
 const uint8_t *lb = (const uint8_t *)snap;   /* 36-byte lease block + lease-valid word */
 char text[8]; const char *s; uint32_t v = 0;
 if (!valid) s = "--";
 else if (error) s = "ERR";
 else if ((now - rx) >= (uint32_t)1000) s = "OLD";
 else if (!snap[9]) s = "--";
 else if (!lb[0] || lb[32] >= 11u || !(lb[33] & 1u)) s = "NONE";
 else if (!(lb[33] & 2u)) s = "OFF";
 else { v = gr_text((uint32_t)lb[30] | (uint32_t)lb[31] << 8, text); s = text; }
 if (v > GR_BAR_MAX) v = GR_BAR_MAX;
 lv_bar_set_value(bar, (int32_t)v, 0);
 lv_label_set_text(value, s);
}
#endif

#ifdef GP50_FEATURE_GR_METER
static void update_strip(lv_obj_t *box, const gp50_strip *s) {
 lv_obj_t *bar = lv_obj_get_child(box, 0), *value = lv_obj_get_child(box, 1);
 lv_bar_set_value(bar, (int32_t)((uint32_t)s->level * GR_BAR_MAX / s->level_max), 0);
 uint32_t n = 0;
 while (n < sizeof s->value && s->value[n]) n++;
 lv_obj_set_pos(value, GR_TEXT_RIGHT - (int32_t)(n * GR_CHAR_W), GR_TEXT_Y);
 lv_label_set_text(value, s->value);
}
#endif

int nds_gr_editor_tick(uint8_t *ctx, void *msg) {
 mod026_editor_tick(ctx, msg);
#ifdef GP50_FEATURE_ASSIGNMENT
 if (*(volatile uint32_t *)GP50_MOD026_ASSIGN_STATE || gp50_features_editor_text_active()) {   /* prompt owns the strip */
#else
 if (*(volatile uint32_t *)GP50_MOD026_ASSIGN_STATE) {          /* assignment prompt owns the strip */
#endif
  ST[S_WARN] = 0; ST[S_KEY] = 0;
  lv_obj_t *box = (lv_obj_t *)ST[S_METER];
  if (box) { lv_obj_del(box); ST[S_METER] = 0; ST[S_SHOWN] = 0; }
  return 0;
 }
 uint32_t idx = ctx[0x90];
#ifdef GP50_FEATURE_GR_METER
 gp50_strip strip;
 if (idx < 10u && ctx[0x80 + idx] < 10u && gp50_features_strip(ctx[0x80 + idx], &strip)) {
  lv_obj_t *label = *(lv_obj_t **)(ctx + 0xe0);
  if (!label) return 0;
  ST[S_WARN] = 0; ST[S_KEY] = 0;
  if (!ST[S_METER]) build(label, strip.label);
  update_strip((lv_obj_t *)ST[S_METER], &strip);
  return 0;
 }
#else
 if (idx < 10u && ctx[0x80 + idx] == 1u && effect_ordinal(1) == GR_ORDINAL) {
  lv_obj_t *label = *(lv_obj_t **)(ctx + 0xe0);
  if (!label) return 0;
  ST[S_WARN] = 0; ST[S_KEY] = 0;
  if (!ST[S_METER]) build(label, "GR");
  update((lv_obj_t *)ST[S_METER]);
  return 0;
 }
#endif
 if (ST[S_SHOWN]) {
  lv_obj_t *box = (lv_obj_t *)ST[S_METER];
  if (box) lv_obj_del(box);
  ST[S_METER] = 0; ST[S_SHOWN] = 0;
  mod026_restore_ctx(ctx);
 }
 lv_obj_t *label = *(lv_obj_t **)(ctx + 0xe0);
 if (label) nds_cpu_edit_strip(ctx, label, ST);
 return 0;
}
