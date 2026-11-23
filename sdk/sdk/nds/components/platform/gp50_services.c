/* Pedal implementation of the gp50.h services (ABI 3) over the stock application. Platform code: the only place that
 * knows stock routines and addresses. Hard-float (parameter values travel in fs0 like the stock knob path).
 * Each service follows a reviewed stock caller sequence, cited per function:
 *   block on/off       = UI effect-set knob 1 (firmware/reconstructed/nds/ui_effect_set.c: 0x473f0(slot, on)),
 *                        which carries the CPU-admission gate hook at 0x473f6
 *   model select       = UI effect-set knob 2 (0x475d8(slot, ordinal), admission gate hook at 0x475de)
 *   parameter set      = stock knob nudge 0x4772c (firmware/reconstructed/nds/ui_knob.c): setter 0x4557e with notify,
 *                        kind-4 notification 0x4305e, link send 0x46750 or the Sync companion path
 *   parameter getters  = 0x4555a value, 0x43b2c/0x43ba6/0x43c20 min/max/step (ui_knob.c)
 *   names              = catalog entries 0x197ca (model) and 0x46c32 (parameter, used by the assignment UI)
 *   host notify        = own_commands.c own_assign_notify: connection 0x432ec == 2, reply queue 0x15a1e(frame, n, 1)
 *   expression pedal   = the MOD027 auto-wah gates (sdk/nds/own/wah_auto.c): global EXP mode 0x46e80() == 0, EXP on
 *                        0x47bf8(0) == 1, assignment 0x47d58(0,0)/0x47d60(0,0), filtered reading 0x480be(0) against the
 *                        stock 0x44bf0 calibration (s16 max at 0x2001068a, min at +4), span >= 100
 */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#pragma GCC optimize("no-function-cse")   /* stock calls stay direct jal: the callback stack audit refuses indirect calls */
#include "../gp50.h"
#include "../../own/stock_io.h"
#include "gp50_features.h"
extern gp50_features_ram *const gp50_features_ram_block;

static const StockIo direct_io;
#define IO (&direct_io)

#define PRESET_IDS 0x200106d3       /* live public model IDs, u32 LE unaligned, 4 per block (mData + 0xe) */
#define ENABLE_GET 0x452ae          /* (block) -> 0/1 */
#define ENABLE_SET 0x473f0          /* (block, on): UI/host on-off path with CPU admission */
#define SELECT_APPLY 0x475d8        /* (block, ordinal) -> 0 when refused */
#define BLOCK_ORDINAL 0x475d0       /* (block) -> current ordinal */
#define MODEL_COUNT 0x43996         /* (block) -> models available */
#define ORDINAL_TO_ID 0x439b6       /* (block, ordinal) -> public ID */
#define ID_TO_ORDINAL 0x439dc       /* (block, public ID) -> ordinal (0 when unknown) */
#define MODEL_NAME 0x197ca          /* (block, ordinal, dst, size) */
#define PARAM_COUNT 0x46c2a         /* (block) -> parameters of the current model */
#define PARAM_NAME 0x46c32          /* (block, param, dst, size) */
#define PARAM_VALUE 0x4555a         /* (block, param) -> float */
#define PARAM_MIN 0x43b2c
#define PARAM_MAX 0x43ba6
#define PARAM_STEP 0x43c20
#define PARAM_STORE 0x4557e         /* (block, param, notify, fs0 value) -> Sync companion index or 0xffff */
#define NOTIFY 0x4305e              /* (kind, a, b): editor/host change notification */
#define LINK_PARAM 0x46750          /* (block, param): send one parameter to the DSP */
#define LINK_BLOCK 0x466ac          /* (block, companion): send a block's parameters (Sync companion changed) */
#define RUN_MODE 0x47696            /* (4) after a companion change, as the knob path */
#define CURRENT_PRESET 0x471d6      /* () -> current preset number */
#define PRESET_MODIFIED 0x43d52     /* (1) */
#define TICKS 0x20004ad0            /* u32 raw application tick, 1 ms */
#define CONNECTION 0x432ec          /* () -> 2 when a host listens */
#define REPLY_QUEUE 0x15a1e         /* (frame, length, 1): host notification queue */

static uint32_t svc_u32_at(uint32_t a) {
    const volatile uint8_t *p = (const volatile uint8_t *)(uintptr_t)a;
    return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static float svc_as_float(uint32_t u) { union { uint32_t u; float f; } x = { .u = u }; return x.f; }
static uint32_t svc_as_bits(float f) { union { float f; uint32_t u; } x = { .f = f }; return x.u; }
enum { TEXT_MODEL, TEXT_PARAM, TEXT_VALUE };
static uint32_t svc_text(char *out, uint32_t capacity, uint32_t which, uint32_t a, uint32_t b) {
    if (!out || !capacity) return 0;
    char tmp[GP50_NAME_TEXT_MAX + 9];                 /* stock name fields are at most 20 bytes plus NUL */
    for (uint32_t i = 0; i < sizeof tmp; i++) tmp[i] = 0;
    uint32_t dst = (uint32_t)(uintptr_t)tmp;          /* direct calls (no function pointer: stack audit) */
    if (which == TEXT_MODEL) STOCK_CALL(IO, 0x197ca, a, b, dst, sizeof tmp - 1);
    else if (which == TEXT_PARAM) STOCK_CALL(IO, 0x46c32, a, b, dst, sizeof tmp - 1);
    else STOCK_CALL(IO, 0x46c4a, a, b, dst, 16);
    uint32_t n = 0, limit = capacity - 1 < GP50_NAME_TEXT_MAX ? capacity - 1 : GP50_NAME_TEXT_MAX;
    while (n < limit && tmp[n]) { out[n] = tmp[n]; n++; }
    out[n] = 0;
    return n;
}

/* ---- blocks ---- */
uint32_t gp50_block_model(uint32_t b) { return b < GP50_BLOCKS ? svc_u32_at(PRESET_IDS + 4 * b) : 0; }
uint32_t gp50_block_enabled(uint32_t b) { return b < GP50_BLOCKS ? STOCK_CALL(IO, ENABLE_GET, b) == 1 : 0; }
uint32_t gp50_block_set_enabled(uint32_t b, uint32_t on) {
    if (b >= GP50_BLOCKS || on > 1) return GP50_REFUSED;
    if (gp50_block_enabled(b) == on) return GP50_OK;
    STOCK_CALL(IO, ENABLE_SET, b, on);
    return gp50_block_enabled(b) == on ? GP50_OK : GP50_REFUSED;   /* CPU admission may refuse "on" */
}
uint32_t gp50_block_model_count(uint32_t b) { return b < GP50_BLOCKS ? STOCK_CALL(IO, MODEL_COUNT, b) & 0xffff : 0; }
uint32_t gp50_block_model_at(uint32_t b, uint32_t i) {
    return b < GP50_BLOCKS && i < gp50_block_model_count(b) ? STOCK_CALL(IO, ORDINAL_TO_ID, b, i) : 0;
}
uint32_t gp50_block_select(uint32_t b, uint32_t id) {
    if (b >= GP50_BLOCKS || !id) return GP50_REFUSED;
    uint32_t ordinal = STOCK_CALL(IO, ID_TO_ORDINAL, b, id) & 0xffff;
    if (STOCK_CALL(IO, ORDINAL_TO_ID, b, ordinal) != id) return GP50_REFUSED;   /* unknown here: never select 0 */
    if (gp50_block_model(b) == id) return GP50_OK;
    STOCK_CALL(IO, SELECT_APPLY, b, ordinal);
    return gp50_block_model(b) == id ? GP50_OK : GP50_REFUSED;
}
uint32_t gp50_block_name(uint32_t b, char *out, uint32_t capacity) {
    static const char *const label[GP50_BLOCKS] = { "NR", "PRE", "DST", "AMP", "CAB", "EQ", "MOD", "DLY", "RVB", "NS" };
    if (b >= GP50_BLOCKS || !gp50_block_model(b)) { if (out && capacity) out[0] = 0; return 0; }
    if (b == GP50_CAB || b == GP50_NS) {              /* own tables (impulse responses, gate): block label only */
        uint32_t n = 0;
        while (out && n + 1 < capacity && label[b][n]) { out[n] = label[b][n]; n++; }
        if (out && capacity) out[n] = 0;
        return n;
    }
    return svc_text(out, capacity, TEXT_MODEL, b, STOCK_CALL(IO, BLOCK_ORDINAL, b));
}

/* ---- parameters ---- */
static uint32_t svc_valid_param(uint32_t b, uint32_t p) { return b < GP50_BLOCKS && p < 8 && p < gp50_param_count(b); }
uint32_t gp50_param_count(uint32_t b) { return b < GP50_BLOCKS ? STOCK_CALL(IO, PARAM_COUNT, b) & 0xff : 0; }
uint32_t gp50_param_get(uint32_t b, uint32_t p, float *value) {
    if (!value || !svc_valid_param(b, p)) return GP50_REFUSED;
    *value = svc_as_float(STOCK_CALL_RF2(IO, PARAM_VALUE, b, p));
    return GP50_OK;
}
uint32_t gp50_param_range(uint32_t b, uint32_t p, float *min, float *max, float *step) {
    if (!svc_valid_param(b, p)) return GP50_REFUSED;
    if (min) *min = svc_as_float(STOCK_CALL_RF2(IO, PARAM_MIN, b, p));
    if (max) *max = svc_as_float(STOCK_CALL_RF2(IO, PARAM_MAX, b, p));
    if (step) *step = svc_as_float(STOCK_CALL_RF2(IO, PARAM_STEP, b, p));
    return GP50_OK;
}
uint32_t gp50_param_set(uint32_t b, uint32_t p, float value) {
    if (!svc_valid_param(b, p) || value != value) return GP50_REFUSED;   /* NaN refused */
    float step = svc_as_float(STOCK_CALL_RF2(IO, PARAM_STEP, b, p));
    if (!(step > 0.0f)) return GP50_REFUSED;          /* the setter divides by the step */
    uint32_t companion = STOCK_CALL_F3(IO, PARAM_STORE, b, p, 1, svc_as_bits(value));   /* rounds, clamps, marks modified */
    STOCK_CALL(IO, NOTIFY, 4, b & 0xffff, p & 0xffff);
    if (companion == 0xffff) { STOCK_CALL(IO, LINK_PARAM, b & 0xff, p & 0xff); return GP50_OK; }
    STOCK_CALL(IO, NOTIFY, 9, 1, 0);
    STOCK_CALL(IO, LINK_BLOCK, b & 0xff, companion & 0xff);
    STOCK_CALL(IO, RUN_MODE, 4);
    return GP50_OK;
}
uint32_t gp50_param_name(uint32_t b, uint32_t p, char *out, uint32_t capacity) {
    if (!svc_valid_param(b, p)) { if (out && capacity) out[0] = 0; return 0; }
    return svc_text(out, capacity, TEXT_PARAM, b, p);
}

/* ---- presets, time, system ---- */
uint32_t gp50_preset_number(void) { return STOCK_CALL0(IO, CURRENT_PRESET) & 0xff; }
void gp50_preset_mark_modified(void) { STOCK_CALL(IO, PRESET_MODIFIED, 1); }
uint32_t gp50_millis(void) { return *(volatile uint32_t *)(uintptr_t)TICKS; }
uint32_t gp50_dsp_load(void) { return gp50_platform_cpu_percent(); }

/* ---- host ---- */
uint32_t gp50_host_notify(const uint8_t *payload, uint32_t length) {
    uint32_t selector = gp50_features_current_selector();
    if (!payload || !selector || length > GP50_HOST_BYTES_MAX || STOCK_CALL0(IO, CONNECTION) != 2) return GP50_REFUSED;
    uint8_t frame[GP50_HOST_BYTES_MAX + 2];
    frame[0] = 0x12; frame[1] = (uint8_t)selector;
    for (uint32_t i = 0; i < length; i++) frame[2 + i] = payload[i];
    STOCK_CALL(IO, REPLY_QUEUE, (uint32_t)(uintptr_t)frame, length + 2, 1);   /* as own_assign_notify: queued copy */
    return GP50_OK;
}

/* ---- expression pedal ---- */
#define EXP_GLOBAL_MODE 0x46e80     /* () -> 0 when the pedal input is an expression pedal */
#define EXP_ENABLED 0x47bf8         /* (pedal) -> 1 when on */
#define EXP_BLOCK 0x47d58           /* (pedal, 0) -> assigned block */
#define EXP_PARAM 0x47d60           /* (pedal, 0) -> assigned parameter */
#define EXP_READING 0x480be         /* (pedal) -> filtered reading (s16) */
#define EXP_CALIBRATION 0x2001068a  /* s16 maximum at +0, s16 minimum at +4 */
uint32_t gp50_expression_get(uint32_t pedal, gp50_expression *out) {
    if (pedal != 0 || !out) return GP50_REFUSED;
    out->enabled = STOCK_CALL0(IO, EXP_GLOBAL_MODE) == 0 && STOCK_CALL(IO, EXP_ENABLED, 0) == 1;
    uint32_t block = STOCK_CALL(IO, EXP_BLOCK, 0, 0) & 0xff;
    out->block = block < GP50_BLOCKS ? (uint8_t)block : GP50_BLOCKS;
    out->param = (uint8_t)(STOCK_CALL(IO, EXP_PARAM, 0, 0) & 0xff);
    const volatile uint8_t *cal = (const volatile uint8_t *)(uintptr_t)EXP_CALIBRATION;
    int32_t high = (int16_t)(cal[0] | cal[1] << 8), low = (int16_t)(cal[4] | cal[5] << 8), span = high - low;
    out->calibrated = span >= 100;
    out->position = 0;
    if (out->calibrated) {
        int32_t at = (int16_t)STOCK_CALL(IO, EXP_READING, 0) - low;
        if (at < 0) at = 0;
        if (at > span) at = span;
        out->position = (uint16_t)((uint32_t)at * 1000u / (uint32_t)span);
    }
    return GP50_OK;
}

/* ---- audio-processor meters (the GR meter's telemetry reading, sdk/nds/ui/gr_meter.c update()) ---- */
#if __has_include("telemetry_table.h")
#include "telemetry_table.h"
#define METER_ST ((volatile uint32_t *)NDS_UI_STATE)
enum { M_REQUESTED = 0, M_VALID = 2, M_ERROR = 3, M_RX_TICK = 5, M_UI_TICK = 21, M_UI_VALID = 22, M_LEASE = 24 };
#define METER_POLL_MS 100u           /* request interval while read (the GR meter's ~10 Hz) */
#define METER_STALE_MS 1000u
static uint32_t svc_meter_snapshot(uint32_t snap[10]) {
    uint32_t valid, error, rx;
    STOCK_CALL0(IO, 0x5c0e2);
    uint32_t now = gp50_millis();
    if (!METER_ST[M_UI_VALID] || now - METER_ST[M_UI_TICK] >= METER_POLL_MS) {
        METER_ST[M_UI_TICK] = now; METER_ST[M_UI_VALID] = 1; METER_ST[M_REQUESTED] = 1;
    }
    for (uint32_t i = 0; i < 10; i++) snap[i] = METER_ST[M_LEASE + i];
    valid = METER_ST[M_VALID]; error = METER_ST[M_ERROR]; rx = METER_ST[M_RX_TICK];
    STOCK_CALL0(IO, 0x5c102);
    if (!valid) return GP50_METER_NO_DATA;
    if (error) return GP50_METER_ERROR;
    if (now - rx >= METER_STALE_MS) return GP50_METER_STALE;
    if (!snap[9]) return GP50_METER_NO_DATA;
    return GP50_METER_OK;
}

uint32_t gp50_meter_get(gp50_meter *out) {
    if (!out) return GP50_REFUSED;
    uint32_t snap[10];
    out->status = svc_meter_snapshot(snap);
    const uint8_t *lb = (const uint8_t *)snap;
    out->block = lb[32]; out->gain_reduction = 0;
    if (out->status != GP50_METER_OK) return GP50_OK;
    if (!lb[0] || lb[32] >= GP50_BLOCKS || !(lb[33] & 1u) || (lb[33] & 12u)) out->status = GP50_METER_NONE;
    else if (!(lb[33] & 2u)) out->status = GP50_METER_BYPASSED;
    else out->gain_reduction = (uint16_t)(lb[30] | lb[31] << 8);
    return GP50_OK;
}

static uint16_t svc_stock_gr_db(float gain) {
    if (gain <= 0.001f) return 6000;
    if (gain >= 1.0f) return 0;
    uint32_t bits = svc_as_bits(gain);
    int32_t exponent = (int32_t)(bits >> 23) - 127;
    float mantissa = svc_as_float((bits & 0x7fffffu) | 0x3f800000u);
    /* ln(m) = 2 atanh((m-1)/(m+1)). Here |x| <= 1/3. */
    float x = (mantissa - 1.0f) / (mantissa + 1.0f);
    float x2 = x * x;
    float log_m = 2.0f * x * (1.0f + x2 * (1.0f/3.0f + x2 * (1.0f/5.0f + x2/7.0f)));
    return (uint16_t)(-868.58896f * ((float)exponent * 0.69314718f + log_m) + 0.5f);
}

static void svc_stock_meter(uint32_t block, uint32_t model, uint32_t status,
                            const uint8_t *lease, gp50_meter *out) {
    out->block = (uint8_t)block; out->gain_reduction = 0; out->status = (uint8_t)status;
    uint32_t kind = block == GP50_NR ? model == 0x1bu : model <= 1u ? model + 1u : 0u;
    if (!kind) { out->status = GP50_METER_NONE; return; }
    if (!gp50_block_enabled(block)) { out->status = GP50_METER_BYPASSED; return; }
    if (status != GP50_METER_OK) return;
    out->status = GP50_METER_NO_DATA;
    uint32_t bits;
    if (block == GP50_NR) {
        if (!(lease[35] & 0x80u)) return;
        bits = ((uint32_t)(lease[35] & 0x7fu) << 24) | ((uint32_t)lease[34] << 16);
    } else {
        if (((lease[33] >> 2) & 3u) != kind || lease[32] != GP50_PRE) return;
        bits = ((uint32_t)lease[31] << 24) | ((uint32_t)lease[30] << 16);
    }
    if ((bits & 0x7f800000u) == 0x7f800000u) return;
    float gain = svc_as_float(bits);
    if (block == GP50_PRE) {
        if (gain < -128.0f || gain > 0.0f) return;
        gain = 1.0f + (gain * 0.1153f) * (1.0f/1024.0f);
        for (uint32_t i = 0; i < 10u; i++) gain *= gain;
    }
    out->status = GP50_METER_OK;
    out->gain_reduction = svc_stock_gr_db(gain);
}

uint32_t gp50_stock_meters_get(gp50_meter *gate, gp50_meter *pre) {
    if (!gate || !pre) return GP50_REFUSED;
    uint32_t snap[10], status = svc_meter_snapshot(snap);
    const uint8_t *lease = (const uint8_t *)snap;
    svc_stock_meter(GP50_NR, gp50_block_model(GP50_NR), status, lease, gate);
    svc_stock_meter(GP50_PRE, gp50_block_model(GP50_PRE), status, lease, pre);
    return GP50_OK;
}
#else
uint32_t gp50_meter_get(gp50_meter *out) {
    if (!out) return GP50_REFUSED;
    out->status = GP50_METER_NO_DATA; out->block = GP50_BLOCKS; out->gain_reduction = 0;
    return GP50_OK;
}

uint32_t gp50_stock_meters_get(gp50_meter *gate, gp50_meter *pre) {
    if (!gate || !pre) return GP50_REFUSED;
    *gate = (gp50_meter){ GP50_METER_NO_DATA, GP50_NR, 0 };
    *pre = (gp50_meter){ GP50_METER_NO_DATA, GP50_PRE, 0 };
    return GP50_OK;
}
#endif

/* ---- measured processor load (diagnostics load bridge, sdk/nds/own/diagnostics.c; `12 50` reads the same state) ---- */
#ifdef GP50_LOAD_BRIDGE
#include "../../own/diagnostics.h"
#define LOAD_STALE_MS 1000u
static float svc_bits_float(uint32_t bits) { union { uint32_t u; float f; } v; v.u = bits; return v.f; }
uint32_t gp50_load_get(gp50_load *out) {
    if (!out) return GP50_REFUSED;
    volatile uint32_t *st = (volatile uint32_t *)(uintptr_t)DIAG_STATE;
    STOCK_CALL0(IO, 0x5c0e2);
    uint32_t valid = st[2], reply = st[5], arm = st[7], dsp = st[8];
    st[0] = 1;                                     /* arm the next request (as a `12 50` read does) */
    STOCK_CALL0(IO, 0x5c102);
    out->arm = valid ? svc_bits_float(arm) : 0.0f; out->dsp = valid ? svc_bits_float(dsp) : 0.0f;
    out->status = !valid ? GP50_METER_NO_DATA : gp50_millis() - reply >= LOAD_STALE_MS ? GP50_METER_STALE : GP50_METER_OK;
    return GP50_OK;
}
#else
uint32_t gp50_load_get(gp50_load *out) {
    if (!out) return GP50_REFUSED;
    out->status = GP50_METER_NO_DATA; out->arm = 0.0f; out->dsp = 0.0f;
    return GP50_OK;
}
#endif

/* ---- parameter text and knob nudge, screens, pedal mode, drum ---- */
#define PARAM_TEXT 0x46c4a          /* (block, param, dst, 16): value as displayed (home knob tiles) */
#define KNOB_NUDGE 0x4772c          /* (block, param, detents): the stock knob path (firmware/reconstructed ui_knob.c) */
#define PEDAL_MODE 0x46f20          /* () -> 1 in Stomp mode */
#define WINDOW_SWITCH 0x176a6       /* (window, 0) */
#define WINDOW_CURRENT 0x17742
#define DRUM_GET 0x470c8
#define DRUM_SET 0x470c0
uint32_t gp50_param_text(uint32_t b, uint32_t p, char *out, uint32_t capacity) {
    if (!svc_valid_param(b, p)) { if (out && capacity) out[0] = 0; return 0; }
    return svc_text(out, capacity, TEXT_VALUE, b, p);
}
uint32_t gp50_param_nudge(uint32_t b, uint32_t p, int32_t steps) {
    if (!svc_valid_param(b, p)) return GP50_REFUSED;
    if (steps) STOCK_CALL(IO, KNOB_NUDGE, b, p, (uint32_t)steps);
    return GP50_OK;
}
uint32_t gp50_screen(void) {
    uint32_t w = STOCK_CALL0(IO, WINDOW_CURRENT) & 0xff;
    return w == 3 ? GP50_SCREEN_HOME : w == 4 ? GP50_SCREEN_EDITOR : w == 7 ? GP50_SCREEN_DRUM : GP50_SCREEN_OTHER;
}
uint32_t gp50_screen_open(uint32_t screen) {
    if (screen == GP50_SCREEN_HOME) STOCK_CALL(IO, WINDOW_SWITCH, 3, 0);
    else if (screen == GP50_SCREEN_DRUM) STOCK_CALL(IO, WINDOW_SWITCH, 7, 0);
    else return GP50_REFUSED;
    return GP50_OK;
}
uint32_t gp50_pedal_mode(void) { return STOCK_CALL0(IO, PEDAL_MODE) == 1 ? GP50_MODE_STOMP : GP50_MODE_PATCH; }
uint32_t gp50_drum_playing(void) { return STOCK_CALL0(IO, DRUM_GET) != 0; }
void gp50_drum_set_playing(uint32_t on) { STOCK_CALL(IO, DRUM_SET, on ? 1 : 0); }

/* ---- screen services (sdk/nds/own/assign_editor.c / assign_home.c / assign_map.c calls) ---- */
#define EDIT_GROUP 0x90u             /* editor ctx: selected block row; +0x80 + row: its block */
#define EDIT_HEADER 0xe0u            /* editor ctx: title label */
#define EDIT_PAGE 0xe4u
#define EDIT_FIRST 0x30u
#define HOME_TITLE 0x34u             /* home ctx: title label */
#define HOME_KNOBS 0x98u             /* home ctx + 4k: knob k tile */
#define OBJ_POS 0x2a46a
#define OBJ_SIZE 0x2a4ce
#define OBJ_SHOW 0x293fc
#define OBJ_CHILD 0x2da52
#define LABEL_SET_TEXT 0x3eea0
#define EDITOR_TITLE 0x1cb6c        /* (ctx): stock editor header text */
#define PRESET_NAME 0x472b8
#define BAR_RANGE 0x276da           /* (tile, min, max) */
#define BAR_VALUE 0x276b4           /* (tile, value, 0) */
#define STOCK_TEXT 0x15f0c          /* (id) */
static uint32_t svc_editor_ctx(void) { return gp50_features_ram_block->editor_ctx; }
static uint32_t svc_home_ctx(void) { return gp50_features_ram_block->home_ctx; }
static uint32_t svc_word(uint32_t a) { return svc_u32_at(a); }
static void svc_set_text(uint32_t label, const char *text) {   /* skip the LVGL call when the text is unchanged */
    const volatile char *now = (const volatile char *)(uintptr_t)svc_word(label + 0x24);
    if (now) { uint32_t i = 0; while (now[i] == text[i] && text[i]) i++; if (now[i] == text[i]) return; }
    STOCK_CALL(IO, LABEL_SET_TEXT, label, (uint32_t)(uintptr_t)text);
}
uint32_t gp50_editor_block(void) {
    const volatile uint8_t *c = (const volatile uint8_t *)(uintptr_t)svc_editor_ctx();
    if (!c || gp50_screen() != GP50_SCREEN_EDITOR || c[EDIT_GROUP] >= 10) return GP50_BLOCKS;
    return c[0x80 + c[EDIT_GROUP]] < 10 ? c[0x80 + c[EDIT_GROUP]] : GP50_BLOCKS;
}
uint32_t gp50_editor_expression_page(void) {
    const volatile uint8_t *c = (const volatile uint8_t *)(uintptr_t)svc_editor_ctx();
    return c && gp50_screen() == GP50_SCREEN_EDITOR && c[EDIT_GROUP] == GP50_BLOCKS
        && c[0xe7] != 1 ? c[EDIT_PAGE] : 0;
}
uint32_t gp50_editor_knob_param(uint32_t knob) {
    const volatile uint8_t *c = (const volatile uint8_t *)(uintptr_t)svc_editor_ctx();
    uint32_t block = gp50_editor_block();
    if (block >= GP50_BLOCKS || knob >= GP50_KNOBS) return GP50_NONE;
    int32_t k = (int32_t)knob + 1, page = c[EDIT_PAGE], first = c[EDIT_FIRST], p;
    if (page) p = k + 3 * page - 3 - first;
    else { if (first || k != 3) return GP50_NONE; p = 0; }
    return p >= 0 && (uint32_t)p < gp50_param_count(block) ? (uint32_t)p : GP50_NONE;
}
uint32_t gp50_editor_text(const char *text, uint32_t kind) {
    uint32_t c = svc_editor_ctx(), header = c ? svc_word(c + EDIT_HEADER) : 0;
    if (!header || !text || kind > GP50_TEXT_PAGE || gp50_screen() != GP50_SCREEN_EDITOR) return GP50_REFUSED;
    STOCK_CALL(IO, OBJ_POS, header, 0, 0);
    STOCK_CALL(IO, OBJ_SIZE, header, 160, kind == GP50_TEXT_PAGE ? 128 : 20);
    svc_set_text(header, text);
    STOCK_CALL(IO, OBJ_SHOW, header, 1);
    gp50_features_ram_block->editor_text = 1;
    return GP50_OK;
}
void gp50_editor_text_clear(void) {
    uint32_t c = svc_editor_ctx(), header = c ? svc_word(c + EDIT_HEADER) : 0;
    gp50_features_ram_block->editor_text = 0;
    if (!c || gp50_screen() != GP50_SCREEN_EDITOR) return;
    if (header) { STOCK_CALL(IO, OBJ_POS, header, 0, 0x57); STOCK_CALL(IO, OBJ_SIZE, header, 160, 41); }
    STOCK_CALL(IO, EDITOR_TITLE, c);
}
uint32_t gp50_home_title(const char *text) {
    uint32_t c = svc_home_ctx(), label = c ? svc_word(c + HOME_TITLE) : 0;
    if (!label || !text || gp50_screen() != GP50_SCREEN_HOME) return GP50_REFUSED;
    svc_set_text(label, text);
    return GP50_OK;
}
void gp50_home_title_restore(void) {
    uint32_t c = svc_home_ctx(), label = c ? svc_word(c + HOME_TITLE) : 0;
    if (label && gp50_screen() == GP50_SCREEN_HOME) svc_set_text(label, (const char *)(uintptr_t)STOCK_CALL0(IO, PRESET_NAME));
}
uint32_t gp50_home_knob_tile(uint32_t knob, const char *name, const char *value, uint32_t percent) {
    uint32_t c = svc_home_ctx(), tile = c && knob < GP50_KNOBS ? svc_word(c + HOME_KNOBS + 4 * knob) : 0;
    if (!tile || !name || !value || gp50_screen() != GP50_SCREEN_HOME) return GP50_REFUSED;
    svc_set_text(STOCK_CALL(IO, OBJ_CHILD, STOCK_CALL(IO, OBJ_CHILD, tile, 0), 0), name);
    svc_set_text(STOCK_CALL(IO, OBJ_CHILD, tile, 2), value);
    STOCK_CALL(IO, OBJ_SHOW, STOCK_CALL(IO, OBJ_CHILD, tile, 1), 1);
    STOCK_CALL(IO, BAR_RANGE, tile, 0, 100);
    STOCK_CALL(IO, BAR_VALUE, tile, percent > 100 ? 100 : percent, 0);
    return GP50_OK;
}
void gp50_home_knob_tile_reset(uint32_t knob) {
    uint32_t c = svc_home_ctx(), tile = c && knob < GP50_KNOBS ? svc_word(c + HOME_KNOBS + 4 * knob) : 0;
    if (!tile || gp50_screen() != GP50_SCREEN_HOME) return;
    svc_set_text(STOCK_CALL(IO, OBJ_CHILD, STOCK_CALL(IO, OBJ_CHILD, tile, 0), 0), (const char *)(uintptr_t)STOCK_CALL(IO, STOCK_TEXT, knob + 12));
    STOCK_CALL(IO, OBJ_SHOW, STOCK_CALL(IO, OBJ_CHILD, tile, 1), 1);
    STOCK_CALL(IO, BAR_RANGE, tile, knob == 1 ? 40 : 0, knob == 1 ? 260 : 100);
    if (knob == 0) STOCK_CALL(IO, 0x21ac2, c, 0);                     /* direct calls (stack audit) */
    else if (knob == 1) STOCK_CALL(IO, 0x219d0, c, 1);
    else STOCK_CALL(IO, 0x21a8c, c, 1);
}

/* ---- control assignments over the platform's live state (sdk/nds/own/assign_store.c ASSIGN_STATE knob bindings,
 * sdk/nds/footswitch_ab/fs_ab_target.c FS_AB_STATE); the platform load/stage code keeps the GPAM codec ---- */
#if __has_include("../../footswitch_ab/fs_ab_target.h")
#include "../../footswitch_ab/fs_ab_target.h"
#include "../../../footswitch_ab/host.h"
#define KNOB_LIVE(k) (0x2001f3f0 + 32u + 16u * (k))   /* ASSIGN_STATE + 32 + 16 k: valid, group, param, ordinal */
#define KNOB_OWNER (0x2001f3f0 + 80u)
#define GUARD_IN 0x5c0e2
#define GUARD_OUT 0x5c102
static float svc_f32(uint32_t u) { union { uint32_t u; float f; } x = { .u = u }; return x.f; }
static uint32_t svc_u32f(float f) { union { float f; uint32_t u; } x = { .f = f }; return x.u; }
static volatile uint32_t *svc_w(uint32_t a) { return (volatile uint32_t *)(uintptr_t)a; }
uint32_t gp50_assignments_get(gp50_assignments *out) {
    if (!out) return GP50_REFUSED;
    gp50_fs_ab_state fs;
    uint32_t live[12], owner;
    STOCK_CALL0(IO, GUARD_IN);
    for (uint32_t i = 0; i < 12; i++) live[i] = svc_w(KNOB_LIVE(0))[i];
    owner = *svc_w(KNOB_OWNER);
    {   /* byte copy: a struct assignment would call memcpy indirectly (stack audit) */
        const volatile uint8_t *from = (const volatile uint8_t *)(uintptr_t)FS_AB_STATE; uint8_t *to = (uint8_t *)&fs;
        for (uint32_t i = 0; i < sizeof fs; i++) to[i] = from[i];
    }
    STOCK_CALL0(IO, GUARD_OUT);
    uint32_t preset = gp50_preset_number();
    out->preset = owner == preset ? (uint8_t)preset : GP50_NONE;
    out->fault = fs.owner == preset && fs.metadata_fault; out->blocked = fs.owner == preset ? fs.blocked_mask & 3u : 0; out->reserved = 0;
    for (uint32_t k = 0; k < GP50_KNOBS; k++) {
        const uint32_t *m = live + 4 * k;
        uint32_t ok = owner == preset && m[0] && m[1] < GP50_BLOCKS && STOCK_CALL(IO, BLOCK_ORDINAL, m[1]) == m[3];
        out->knob[k] = (gp50_knob_binding){ (uint8_t)ok, (uint8_t)(ok ? m[1] : 0), (uint8_t)(ok ? m[2] : 0), 0,
                                            ok ? STOCK_CALL(IO, ORDINAL_TO_ID, m[1], m[3]) : 0 };
    }
    for (uint32_t i = 0; i < GP50_FOOTSWITCHES; i++) {
        const gp50_fs_ab_binding *b = &fs.binding[i];
        uint32_t ok = fs.owner == preset && b->valid;
        out->footswitch[i] = (gp50_footswitch_binding){ (uint8_t)ok, ok ? b->group : 0, ok ? b->parameter : 0,
                                                        ok ? b->flags : 0, ok ? b->model : 0, svc_f32(ok ? b->a : 0), svc_f32(ok ? b->b : 0) };
    }
    return GP50_OK;
}
uint32_t gp50_assignments_set(const gp50_assignments *in) {
    uint32_t preset = gp50_preset_number();
    if (!in || in->preset != preset) return GP50_REFUSED;
    uint32_t live[12];
    for (uint32_t k = 0; k < GP50_KNOBS; k++) {
        const gp50_knob_binding *b = &in->knob[k];
        uint32_t *m = live + 4 * k;
        m[0] = m[1] = m[2] = m[3] = 0;
        if (!b->valid) continue;
        if (b->block >= GP50_BLOCKS || b->param >= 8 || gp50_block_model(b->block) != b->model ||
            b->param >= gp50_param_count(b->block)) return GP50_REFUSED;
        m[0] = 1; m[1] = b->block; m[2] = b->param; m[3] = STOCK_CALL(IO, BLOCK_ORDINAL, b->block);
    }
    gp50_fs_ab_binding foot[2];
    for (uint32_t i = 0; i < GP50_FOOTSWITCHES; i++) {
        const gp50_footswitch_binding *b = &in->footswitch[i];
        foot[i] = (gp50_fs_ab_binding){0};
        if (!b->valid) continue;
        if (b->block >= GP50_BLOCKS || b->param >= 8 || gp50_block_model(b->block) != b->model || !(b->a == b->a) || !(b->b == b->b))
            return GP50_REFUSED;
        foot[i] = (gp50_fs_ab_binding){ 1, b->block, b->param, b->flags, b->model, svc_u32f(b->a), svc_u32f(b->b) };
    }
    STOCK_CALL0(IO, GUARD_IN);
    gp50_fs_ab_state *fs = (gp50_fs_ab_state *)(uintptr_t)FS_AB_STATE;
    uint32_t ok = fs->owner == preset && !fs->metadata_fault;
    if (ok) {
        for (uint32_t i = 0; i < 12; i++) svc_w(KNOB_LIVE(0))[i] = live[i];
        *svc_w(KNOB_OWNER) = preset;
        for (uint32_t i = 0; i < 2; i++) {               /* a changed switch is no longer blocked (as 11 74 set) */
            const uint8_t *x = (const uint8_t *)&fs->binding[i], *y = (const uint8_t *)&foot[i];
            uint32_t same = 1;
            for (uint32_t k = 0; k < sizeof foot[i]; k++) same &= x[k] == y[k];
            if (!same || foot[i].valid) fs->blocked_mask &= (uint8_t)~(1u << i);
        }
        fs->binding[0] = foot[0]; fs->binding[1] = foot[1];
    }
    STOCK_CALL0(IO, GUARD_OUT);
    return ok ? GP50_OK : GP50_REFUSED;
}
uint32_t gp50_assignments_recover(void) {
    uint32_t preset = gp50_preset_number();
    STOCK_CALL0(IO, GUARD_IN);
    gp50_fs_ab_state *fs = (gp50_fs_ab_state *)(uintptr_t)FS_AB_STATE;
    uint32_t ok = fs->owner == preset;
    if (ok) {
        for (uint32_t i = 0; i < 12; i++) svc_w(KNOB_LIVE(0))[i] = 0;
        *svc_w(KNOB_OWNER) = preset;
        fs->binding[0] = (gp50_fs_ab_binding){0}; fs->binding[1] = (gp50_fs_ab_binding){0};
        fs->blocked_mask = 0; fs->metadata_fault = 0;
    }
    STOCK_CALL0(IO, GUARD_OUT);
    if (!ok) return GP50_REFUSED;
    gp50_preset_mark_modified();
    return GP50_OK;
}
#endif
