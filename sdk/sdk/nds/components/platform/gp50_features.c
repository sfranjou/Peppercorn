/* ABI 3 feature dispatch (see gp50_features.h). */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#pragma GCC optimize("no-function-cse")   /* stock calls stay direct jal: the callback stack audit refuses indirect calls */
#include "gp50_features.h"
#include "../../own/stock_io.h"
_Static_assert(sizeof(gp50_features_ram) == 932, "keep FEATURES_BYTES in scripts/nds_ui/component_ram.py in step");

extern const gp50_feature_entry gp50_feature_table[];
extern const uint32_t gp50_feature_count;
extern gp50_features_ram *const gp50_features_ram_block;
#define RAM gp50_features_ram_block

static const StockIo direct_io;
#define IO (&direct_io)
#define GUARD_ENTER 0x5c0e2
#define GUARD_LEAVE 0x5c102
#define WINDOW_CURRENT 0x17742      /* () -> current window id */
#define WINDOW_HOME 3u
#define WINDOW_EDITOR 4u

static uint32_t fx_index_of(const gp50_feature_entry *f) { return (uint32_t)(f - gp50_feature_table); }

static uint32_t fx_claim(const gp50_feature_entry *f, uint32_t expected) {
    STOCK_CALL0(IO, GUARD_ENTER);
    uint32_t ok = *f->gate == expected;
    if (ok) { *f->gate = 2; RAM->current = fx_index_of(f) + 1; }
    __asm__ volatile ("" ::: "memory");
    STOCK_CALL0(IO, GUARD_LEAVE);
    return ok;
}
static void fx_release(const gp50_feature_entry *f) {
    STOCK_CALL0(IO, GUARD_ENTER);
    __asm__ volatile ("" ::: "memory");
    RAM->current = 0; *f->gate = 1;
    STOCK_CALL0(IO, GUARD_LEAVE);
}

#ifdef GP50_FEATURE_AUTO_WAH
uint32_t auto_wah_config(const gp50_ctx *);
uint32_t auto_wah_get(const gp50_ctx *, uint8_t *, uint32_t);

int32_t gp50_features_expression_config(void) {
    for (uint32_t i = 0; i < gp50_feature_count; ++i) {
        const gp50_feature_entry *f = &gp50_feature_table[i];
        if (f->get != auto_wah_get || !fx_claim(f, 1)) continue;
        const uint32_t config = auto_wah_config(&f->ctx);
        fx_release(f);
        return (int32_t)config;
    }
    return -1;
}
#endif

static void fx_fill(uint8_t *p, uint8_t v, uint32_t n) { while (n--) *p++ = v; }
static void fx_copy(uint8_t *d, const uint8_t *s, uint32_t n) { while (n--) *d++ = *s++; }

/* The platform RAM block lies in the component arena, which the startup clear zeroes (integrity check:
 * startup_clear_end covers the arena). Not cleared here: a preset read may already have filled load_area. */
void gp50_feature_init(const gp50_feature_entry *f) {
    if (!fx_claim(f, 0)) return;
    uint8_t *p = f->ctx.state;
    for (uint32_t i = 0; i < f->ctx.state_bytes; i++) p[i] = 0;
    if (f->init) f->init(&f->ctx);
    if (f->preset_load) f->preset_load(&f->ctx, 0, 0);   /* defaults until the first preset load */
    fx_release(f);
}
void gp50_feature_tick(const gp50_feature_entry *f) {
    if (!f->tick || !fx_claim(f, 1)) return;
    f->tick(&f->ctx);
    fx_release(f);
}
uint32_t gp50_feature_get(const gp50_feature_entry *f, uint8_t *out, uint32_t capacity) {
    if (!f->get || !out || capacity < f->max_reply_bytes || !fx_claim(f, 1)) return 0;
    uint32_t n = f->get(&f->ctx, out, f->max_reply_bytes);
    fx_release(f);
    return n <= f->max_reply_bytes ? n : 0;
}
uint32_t gp50_feature_set(const gp50_feature_entry *f, const uint8_t *in, uint32_t length) {
    if (!f->set || !in || length != f->set_bytes || !fx_claim(f, 1)) return 1;
    uint32_t r = f->set(&f->ctx, in, length);
    fx_release(f);
    return r ? 1 : 0;
}
uint32_t gp50_feature_status(const gp50_feature_entry *f, char *out, uint32_t capacity) {
    if (!f->status || !out || capacity <= GP50_STATUS_TEXT_MAX || !fx_claim(f, 1)) return 0;
    uint32_t n = f->status(&f->ctx, out, GP50_STATUS_TEXT_MAX + 1);
    fx_release(f);
    return n <= GP50_STATUS_TEXT_MAX ? n : 0;
}

static uint32_t fx_screen(void) {
    uint32_t w = STOCK_CALL0(IO, WINDOW_CURRENT) & 0xff;
    return w == WINDOW_HOME ? GP50_SCREEN_HOME : w == WINDOW_EDITOR ? GP50_SCREEN_EDITOR : w == 7u ? GP50_SCREEN_DRUM : GP50_SCREEN_OTHER;
}
static uint32_t fx_deliver(uint32_t kind, uint32_t index, int32_t value) {
    gp50_event e = { (uint8_t)kind, (uint8_t)index, (uint8_t)fx_screen(), 0, value };
    for (uint32_t i = 0; i < gp50_feature_count; i++) {
        const gp50_feature_entry *f = &gp50_feature_table[i];
        if (!f->event || !fx_claim(f, 1)) continue;          /* busy or not started: the event passes */
        uint32_t r = f->event(&f->ctx, &e);
        fx_release(f);
        if (r == GP50_CONSUMED && kind != GP50_EVENT_PRESET) return 1;
    }
    return 0;
}
static uint32_t fx_deliver_on(uint32_t kind, uint32_t index, uint32_t on_screen, int32_t value) {
    gp50_event e = { (uint8_t)kind, (uint8_t)index, (uint8_t)on_screen, 0, value };
    for (uint32_t i = 0; i < gp50_feature_count; i++) {
        const gp50_feature_entry *f = &gp50_feature_table[i];
        if (!f->event || !fx_claim(f, 1)) continue;
        uint32_t r = f->event(&f->ctx, &e);
        fx_release(f);
        if (r == GP50_CONSUMED && kind != GP50_EVENT_PRESET && kind != GP50_EVENT_SCREEN) return 1;
    }
    return 0;
}
/* Window message ids: type | sub << 8 | param << 16. Type 3 = rotary (sub 0 encoder, 1..3 knobs; movement s32 at
 * message +4); type 2 = key (sub = gesture code, param = key). Roles from the MOD026/029/096 handlers: key 3 code 3
 * EXIT/back, key 3 code 6 DRUM, key 4 code 6 DRUM hold, key 3 code 2 PARA press (assignment_menu.c input map). */
uint32_t gp50_features_ui(uint32_t on_screen, uint32_t word, uint32_t ctx, uint32_t event) {
    if (on_screen == GP50_SCREEN_HOME) RAM->home_ctx = ctx; else if (on_screen == GP50_SCREEN_EDITOR) RAM->editor_ctx = ctx;
    uint32_t type = word & 0xff, sub = word >> 8 & 0xff, key = word >> 16 & 0xff;
    int32_t move = event ? *(volatile int32_t *)(uintptr_t)(event + 4) : 0;
    if (type == 3) {
        if (!move) return 0;
        return sub ? fx_deliver_on(GP50_EVENT_KNOB, sub - 1, on_screen, move) : fx_deliver_on(GP50_EVENT_ENCODER, 0, on_screen, move);
    }
    if (type != 2) return 0;
    if (key == 3 && sub == 3) return fx_deliver_on(GP50_EVENT_BACK, 0, on_screen, 1);
    if (key == 3 && sub == 6) return fx_deliver_on(GP50_EVENT_DRUM, 0, on_screen, 1);
    if (key == 4 && sub == 6) return fx_deliver_on(GP50_EVENT_DRUM_HOLD, 0, on_screen, 1);
    if (key == 3 && sub == 2) return fx_deliver_on(GP50_EVENT_PARA, 0, on_screen, 1);
    return 0;
}

uint32_t gp50_features_footswitch(uint32_t index) {
    return index < GP50_FOOTSWITCHES ? fx_deliver(GP50_EVENT_FOOTSWITCH, index, 1) : 0;
}
uint32_t gp50_features_knob(uint32_t index, int32_t steps) {
    return index < GP50_KNOBS && steps ? fx_deliver(GP50_EVENT_KNOB, index, steps) : 0;
}
void gp50_features_preset_loaded(void) {
    STOCK_CALL0(IO, GUARD_ENTER); RAM->preset_loads++; STOCK_CALL0(IO, GUARD_LEAVE);
}
#define CURRENT_PRESET 0x471d6
#define FLASH_READ 0x10f9e          /* (address, buffer, length, retries) -> 0 when done (the GPAM tail read) */
#define RECORD_BYTES 426u

static uint32_t fx_crc32(const uint8_t *p, uint32_t n) {
    uint32_t crc = 0xffffffff;
    while (n--) { crc ^= *p++; for (int k = 0; k < 8; k++) crc = crc & 1u ? crc >> 1 ^ 0xedb88320 : crc >> 1; }
    return ~crc;
}
static uint32_t fx_le32(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static void fx_put32(uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }
static uint32_t fx_id_length(const char *id) {   /* volatile: GCC would turn the loop into strlen (no libc here) */
    const volatile char *p = id; uint32_t n = 0; while (p[n]) n++; return n;
}

/* Records of a validated area: payload of feature `id`, or 0 (n = 0). */
static const uint8_t *fx_find_record(const uint8_t *area, const char *id, uint32_t *n) {
    uint32_t used = area[6] | (uint32_t)area[7] << 8, at = 12, len = fx_id_length(id);
    while (at + 2 <= 12 + used) {
        uint32_t k = area[at], m = area[at + 1];
        if (at + 2 + k + m > 12 + used) break;
        uint32_t same = k == len;
        for (uint32_t i = 0; same && i < k; i++) same = area[at + 2 + i] == (uint8_t)id[i];
        if (same) { *n = m; return area + at + 2 + k; }
        at += 2 + k + m;
    }
    *n = 0;
    return 0;
}
static uint32_t fx_area_valid(const uint8_t *area, const uint8_t *record) {
    uint32_t used = area[6] | (uint32_t)area[7] << 8;
    return fx_le32(area) == GP50_AREA_MAGIC && area[4] == 1 && area[5] == 0 && used <= GP50_AREA_RECORDS
        && fx_le32(area + 8) == fx_crc32(record, RECORD_BYTES) && fx_le32(area + 12 + used) == fx_crc32(area, 12 + used);
}

void gp50_features_preset_read(uint32_t record, uint32_t index) {
    STOCK_CALL0(IO, GUARD_ENTER); RAM->load_valid = 0; STOCK_CALL0(IO, GUARD_LEAVE);
    if (index >= 100) return;
    if (STOCK_CALL(IO, FLASH_READ, ((index + 1500u) << 10) + GP50_AREA_OFFSET, (uint32_t)(uintptr_t)RAM->load_area,
                   GP50_AREA_BYTES, 10)) return;
    uint32_t ok = fx_area_valid(RAM->load_area, (const uint8_t *)(uintptr_t)record);
    STOCK_CALL0(IO, GUARD_ENTER); RAM->load_valid = ok; STOCK_CALL0(IO, GUARD_LEAVE);
}

/* Application task, each service pass: rebuild the save snapshot from every feature's preset_save. */
static void fx_snapshot(void) {
    uint32_t owner = (STOCK_CALL0(IO, CURRENT_PRESET) & 0xff) + 1, used = 0;
    STOCK_CALL0(IO, GUARD_ENTER); RAM->save_owner = 0; STOCK_CALL0(IO, GUARD_LEAVE);
    for (uint32_t i = 0; i < gp50_feature_count; i++) {
        const gp50_feature_entry *f = &gp50_feature_table[i];
        if (!f->preset_save || !f->preset_bytes) continue;
        uint32_t k = fx_id_length(f->id);
        if (used + 2 + k + f->preset_bytes > GP50_AREA_RECORDS) continue;   /* the build checks the total */
        if (!fx_claim(f, 1)) {                                    /* busy: keep this feature's stored record */
            uint32_t n; const uint8_t *old = RAM->load_valid ? fx_find_record(RAM->load_area, f->id, &n) : 0;
            if (!old || n > f->preset_bytes) continue;
            uint8_t *r = RAM->save_records + used; r[0] = k; r[1] = n;
            fx_copy(r + 2, (const uint8_t *)f->id, k); fx_copy(r + 2 + k, old, n); used += 2 + k + n;
            continue;
        }
        uint8_t *r = RAM->save_records + used;
        uint32_t n = f->preset_save(&f->ctx, r + 2 + k, f->preset_bytes);
        fx_release(f);
        if (!n || n > f->preset_bytes) continue;
        r[0] = k; r[1] = n; fx_copy(r + 2, (const uint8_t *)f->id, k);   /* payload already written after the id */
        used += 2 + k + n;
    }
    STOCK_CALL0(IO, GUARD_ENTER); RAM->save_used = used; RAM->save_owner = owner; STOCK_CALL0(IO, GUARD_LEAVE);
}

/* Sector staging (any task): area for the staged record. Active record: the snapshot when it belongs to the current
 * preset and no load is pending, else the loaded preset's stored records; other records: blank. */
void gp50_features_stage(uint8_t *d, const uint8_t *record, uint32_t active) {
    uint8_t *area = d + GP50_AREA_OFFSET;
    fx_fill(area, 0xff, GP50_AREA_BYTES);
    if (!active) return;
    uint32_t owner = (STOCK_CALL0(IO, CURRENT_PRESET) & 0xff) + 1, used = 0;
    STOCK_CALL0(IO, GUARD_ENTER);
    if (RAM->save_owner == owner && RAM->preset_loads == RAM->preset_seen) {
        used = RAM->save_used; fx_copy(area + 12, RAM->save_records, used);
    } else if (RAM->load_valid) {
        used = RAM->load_area[6] | (uint32_t)RAM->load_area[7] << 8; fx_copy(area + 12, RAM->load_area + 12, used);
    }
    STOCK_CALL0(IO, GUARD_LEAVE);
    if (!used) return;                                         /* nothing to store: the area stays blank */
    fx_put32(area, GP50_AREA_MAGIC); area[4] = 1; area[5] = 0; area[6] = used; area[7] = used >> 8;
    fx_put32(area + 8, fx_crc32(record, RECORD_BYTES));
    fx_put32(area + 12 + used, fx_crc32(area, 12 + used));
}

static void fx_screen_notice(void);
#ifdef GP50_FEATURES_MENU
static uint32_t fx_printable(const char *p, uint32_t cap);
/* ---- Global settings feature tile (see gp50_features.h) ----
 * Window-9 context bytes (stock 0x1f0e4 / 0x1f1ba / 0x1db4c): +0x3c page 0..2, +0x3d slot 0..3, +0x3e item sub-state,
 * +0x28 the item panel (lv_obj, unaligned word). Stock tiles: page*4 + slot = 0..10; the feature tile is page 2 slot 3. */
#define SET_WINDOW 9u
#define SET_PAGE 0x3c
#define SET_SLOT 0x3d
#define SET_SUB 0x3e
#define SET_PANEL 0x28
#define SET_TILE_PAGE 2
#define SET_TILE_SLOT 3
#define SET_TILE_TEXT (0x43u + 11u)    /* UI text id the item loop asks for the 12th tile (0x43 = first tile label) */
#define SET_REFRESH_MS 500u
#define SET_WINDOW_REGISTER 0x177aa   /* (table, entries): window message handlers (stock window-9 open 0x1f23c) */
#define SET_ENCODER 0x1f0e4           /* stock window-9 handlers (table 0xd5b50) */
#define SET_KNOB 0x1e2bc
#define SET_PRESS 0x1f1ba
#define SET_BACK 0x1d8b4
#define SET_CHANGED 0x1e2b0
#define SET_SUB_FLAGS 0x1d8c2         /* the stock encoder handler's refresh sequence, 0x1f164..0x1f186 */
#define SET_PANEL_CLEAR 0x1d90a       /* deletes every child of the item panel */
#define SET_PANEL_BUILD 0x1e6a8
#define SET_VALUES 0x1db4c
#define SET_PAGE_MARKS 0x1daa6
#define SET_HIGHLIGHT 0x1d966
#define UI_TEXT 0x15f0c               /* (id) -> UI string in the current language */
#define UI_FONT 0x15f22               /* (1) -> the font the About panel uses */
#define LABEL_CREATE 0x3e78e          /* lv_label_create(parent) */
#define LABEL_SET_TEXT 0x3eea0        /* lv_label_set_text(label, text): copies */
#define ABOUT_STYLE_A 0x2d9a2         /* the About panel label setup, stock 0x1f0a2..0x1f0dc, same arguments */
#define ABOUT_COLOUR 0x2d968
#define ABOUT_FONT 0x2d97a
#define ABOUT_STYLE_B 0x2d98e
#define OBJ_ALIGN 0x2a57a             /* (obj, 9 = centre, x, y) */
#define ABOUT_COLOUR_WORD 0xffff9fe7u /* movi a1,-24601 at 0x1f0ac */

const uint32_t gp50_settings_table[18] = {
    0x3u, (uint32_t)gp50_settings_encoder, 0x103u, (uint32_t)gp50_settings_knob, 0x203u, (uint32_t)gp50_settings_knob,
    0x303u, (uint32_t)gp50_settings_knob, 0x30202u, (uint32_t)gp50_settings_press, 0x30302u, SET_BACK,
    0x6u, SET_CHANGED, 0x30002u, SET_BACK, 0x30102u, SET_BACK };

static const gp50_feature_entry *fx_menu_owner(void) {
    for (uint32_t i = 0; i < gp50_feature_count; i++)
        if (gp50_feature_table[i].menu_title) return &gp50_feature_table[i];
    return 0;
}
static uint32_t fx_tile_selected(const uint8_t *ctx) {
    return (int8_t)ctx[SET_PAGE] == SET_TILE_PAGE && (int8_t)ctx[SET_SLOT] == SET_TILE_SLOT;
}
static void fx_settings_forget(void) { RAM->settings_ctx = 0; RAM->settings_label = 0; }

/* One line per item, "<label>: <value>" ("--" when the feature gives no value or is busy). */
static void fx_settings_render(void) {
    const gp50_feature_entry *f = fx_menu_owner();
    if (!f || !RAM->settings_label) return;
    char buffer[GP50_MENU_ITEMS_MAX * (2u * GP50_MENU_TEXT_MAX + 3u) + 1u];
    char value[GP50_MENU_TEXT_MAX + 1u];
    volatile char *text = buffer;                 /* volatile: GCC would turn the copy loops into memcpy (no libc) */
    uint32_t n = 0;
    for (uint32_t i = 0; i < f->menu_count && i < GP50_MENU_ITEMS_MAX; i++) {
        if (i) text[n++] = '\n';
        const char *s = f->menu_items[i];
        for (uint32_t k = 0; s && s[k] && k < GP50_MENU_TEXT_MAX; k++) text[n++] = s[k];
        text[n++] = ':'; text[n++] = ' ';
        uint32_t v = 0;
        if (f->menu_value && fx_claim(f, 1)) {
            for (uint32_t k = 0; k < sizeof value; k++) value[k] = 0;
            v = f->menu_value(&f->ctx, i, value, sizeof value);
            fx_release(f);
        }
        if (!v || v > GP50_MENU_TEXT_MAX || !fx_printable(value, sizeof value)) { value[0] = '-'; value[1] = '-'; v = 2; }
        for (uint32_t k = 0; k < v; k++) text[n++] = value[k];
    }
    text[n] = 0;
    STOCK_CALL(IO, LABEL_SET_TEXT, RAM->settings_label, buffer);
    RAM->settings_ms = gp50_millis();
}
/* The tile became selected: one centred label on the (just cleared) item panel, styled like the About panel. */
static void fx_settings_enter(uint8_t *ctx) {
    uint32_t panel = ctx[SET_PANEL] | (uint32_t)ctx[SET_PANEL + 1] << 8 | (uint32_t)ctx[SET_PANEL + 2] << 16 |
                     (uint32_t)ctx[SET_PANEL + 3] << 24;
    fx_settings_forget();
    if (!panel) return;
    uint32_t label = STOCK_CALL(IO, LABEL_CREATE, panel);
    if (!label) return;
    STOCK_CALL(IO, ABOUT_STYLE_A, label, 2u, 0u);
    STOCK_CALL(IO, ABOUT_COLOUR, label, ABOUT_COLOUR_WORD, 0u);
    STOCK_CALL(IO, ABOUT_FONT, label, STOCK_CALL(IO, UI_FONT, 1u), 0u);
    STOCK_CALL(IO, ABOUT_STYLE_B, label, 2u, 0u);
    STOCK_CALL(IO, OBJ_ALIGN, label, 9u, 0u, 0u);
    RAM->settings_ctx = (uint32_t)ctx; RAM->settings_label = label;
    fx_settings_render();
}
static void fx_settings_service(void) {
    if (!RAM->settings_label) return;
    if ((STOCK_CALL0(IO, WINDOW_CURRENT) & 0xff) != SET_WINDOW || !fx_tile_selected((const uint8_t *)RAM->settings_ctx)) {
        fx_settings_forget(); return;
    }
    if (gp50_elapsed_ms(gp50_millis(), RAM->settings_ms) >= SET_REFRESH_MS) fx_settings_render();
}

uint32_t gp50_settings_open(uint32_t table, uint32_t window) {
    (void)table;
    fx_settings_forget();
    return STOCK_CALL(IO, SET_WINDOW_REGISTER, (uint32_t)gp50_settings_table, window);
}
const char *gp50_settings_label(uint32_t text_id) {
    const gp50_feature_entry *f = fx_menu_owner();
    if ((text_id & 0xff) == SET_TILE_TEXT && f) return f->menu_title;
    return (const char *)STOCK_CALL(IO, UI_TEXT, text_id);
}
uint32_t gp50_settings_encoder(uint8_t *ctx, uint8_t *event) {
    int32_t move = *(volatile int32_t *)(event + 4);
    if (fx_tile_selected(ctx)) {
        if (move > 0) return 0;                       /* last tile: stock would step past the end */
        fx_settings_forget();                          /* the stock refresh deletes the panel's children */
        return STOCK_CALL(IO, SET_ENCODER, ctx, event);
    }
    if ((int8_t)ctx[SET_PAGE] == SET_TILE_PAGE && (int8_t)ctx[SET_SLOT] == SET_TILE_SLOT - 1 && move > 0 && fx_menu_owner()) {
        ctx[SET_SLOT] = SET_TILE_SLOT; ctx[SET_SUB] = 0;   /* About -> the feature tile (stock stops at About) */
        STOCK_CALL(IO, SET_PANEL_CLEAR, ctx); STOCK_CALL(IO, SET_PANEL_BUILD, ctx); STOCK_CALL(IO, SET_VALUES, ctx);
        STOCK_CALL(IO, SET_PAGE_MARKS, ctx); STOCK_CALL(IO, SET_HIGHLIGHT, ctx); STOCK_CALL(IO, SET_SUB_FLAGS, ctx);
        fx_settings_enter(ctx);
        return 0;
    }
    return STOCK_CALL(IO, SET_ENCODER, ctx, event);
}
uint32_t gp50_settings_knob(uint8_t *ctx, uint8_t *event) {
    if (!fx_tile_selected(ctx)) return STOCK_CALL(IO, SET_KNOB, ctx, event);
    const gp50_feature_entry *f = fx_menu_owner();
    uint32_t item = (uint32_t)event[1] - 1u;          /* knob 1..3 -> item 0..2 */
    int32_t move = *(volatile int32_t *)(event + 4);
    if (f && f->menu_change && item < f->menu_count && move && fx_claim(f, 1)) {
        f->menu_change(&f->ctx, item, move);
        fx_release(f);
    }
    fx_settings_render();
    return 0;
}
uint32_t gp50_settings_press(uint8_t *ctx, uint8_t *event) {
    if (fx_tile_selected(ctx)) return 0;              /* nothing to open on the feature tile */
    return STOCK_CALL(IO, SET_PRESS, ctx, event);
}
#endif

void gp50_features_service(void) {
    fx_screen_notice();
    STOCK_CALL0(IO, GUARD_ENTER);
    uint32_t pending = RAM->preset_loads != RAM->preset_seen;
    RAM->preset_seen = RAM->preset_loads;
    STOCK_CALL0(IO, GUARD_LEAVE);
    if (pending) {
        uint32_t number = STOCK_CALL0(IO, CURRENT_PRESET) & 0xff;
        for (uint32_t i = 0; i < gp50_feature_count; i++) {
            const gp50_feature_entry *f = &gp50_feature_table[i];
            if (!f->preset_load || !fx_claim(f, 1)) continue;
            uint32_t n = 0;
            const uint8_t *p = RAM->load_valid ? fx_find_record(RAM->load_area, f->id, &n) : 0;
            if (n > f->preset_bytes) { p = 0; n = 0; }
            f->preset_load(&f->ctx, p, n);
            fx_release(f);
        }
        fx_deliver(GP50_EVENT_PRESET, number, 0);
    }
    fx_snapshot();
#ifdef GP50_FEATURES_MENU
    fx_settings_service();
#endif
}

uint32_t gp50_features_current_selector(void) {
    uint32_t c = RAM->current;
    return c && c <= gp50_feature_count ? gp50_feature_table[c - 1].selector : 0;
}

uint32_t nds_cpu_estimate_percent(void) __attribute__((weak));
uint32_t gp50_platform_cpu_percent(void) { return nds_cpu_estimate_percent ? nds_cpu_estimate_percent() : GP50_DSP_UNKNOWN; }

/* ---- Global settings > About page lines ---- */
#define ABOUT_STRCAT 0xd0da4        /* bounded strcat(dst, src, capacity) the stock About page uses */

/* Stock 0x1f088: the last strcat of the About text (Firmware Version + version + copyright, 100-byte buffer).
 * Same append, then one "\n<line>" per feature `about` callback while it fits (the page centres a single label). */
char *gp50_about_append(char *dst, const char *src, uint32_t capacity) {
    char *r = ((char *(*)(char *, const char *, uint32_t))(uintptr_t)ABOUT_STRCAT)(dst, src, capacity);
    if (!dst || capacity < 2) return r;
    volatile char *d = dst;                        /* volatile: no strlen/libc calls on this target */
    uint32_t len = 0, lines = 0;
    while (len < capacity && d[len]) len++;
    for (uint32_t i = 0; i < gp50_feature_count && lines < GP50_ABOUT_LINES_MAX; i++) {
        const gp50_feature_entry *f = &gp50_feature_table[i];
        if (!f->about || !fx_claim(f, 1)) continue;
        char line[GP50_ABOUT_TEXT_MAX + 1];
        uint32_t n = f->about(&f->ctx, line, sizeof line);
        fx_release(f);
        if (!n || n > GP50_ABOUT_TEXT_MAX || len + 1 + n + 1 > capacity) continue;
        uint32_t ok = 1;
        for (uint32_t k = 0; k < n; k++) ok &= (uint8_t)line[k] >= 32 && (uint8_t)line[k] <= 126;
        if (!ok) continue;
        d[len++] = '\n';
        for (uint32_t k = 0; k < n; k++) d[len++] = line[k];
        d[len] = 0;
        lines++;
    }
    return r;
}

/* ---- effect editor meter strip ---- */
static uint32_t fx_printable(const char *p, uint32_t cap) {
    uint32_t n = 0;
    while (n < cap && p[n]) { if ((uint8_t)p[n] < 32 || (uint8_t)p[n] > 126) return 0; n++; }
    return n < cap;                                   /* NUL-terminated inside its field */
}
uint32_t gp50_features_strip(uint32_t block, gp50_strip *s) {
    for (uint32_t i = 0; i < gp50_feature_count; i++) {
        const gp50_feature_entry *f = &gp50_feature_table[i];
        if (!f->strip || !fx_claim(f, 1)) continue;
        gp50_strip t;
        uint8_t *p = (uint8_t *)&t;
        for (uint32_t k = 0; k < sizeof t; k++) p[k] = 0;
        uint32_t want = f->strip(&f->ctx, block, &t);
        fx_release(f);
        if (want != 1 || !t.level_max || !fx_printable(t.label, sizeof t.label) || !fx_printable(t.value, sizeof t.value)) continue;
        if (t.level > t.level_max) t.level = t.level_max;
        *s = t;
        return 1;
    }
    return 0;
}

/* ---- screen contexts and screen-change notice ---- */
void gp50_features_screen_ctx(uint32_t on_screen, uint32_t ctx) {
    if (on_screen == GP50_SCREEN_HOME) RAM->home_ctx = ctx; else if (on_screen == GP50_SCREEN_EDITOR) RAM->editor_ctx = ctx;
}
/* Home tick (hook_legacy_home_tick with GP50_FEATURE_ASSIGNMENT): remember the home context, then the stock home tick
 * through the legacy_ui prologue-replay stub. */
uint32_t legacy_home_tick_stock(uint32_t ctx, uint32_t event);
uint32_t gp50_ui_home_tick(uint32_t ctx, uint32_t event) {
    RAM->home_ctx = ctx;
    return legacy_home_tick_stock(ctx, event);
}
uint32_t gp50_features_editor_text_active(void) { return RAM->editor_text; }
static void fx_screen_notice(void) {
    uint32_t now = fx_screen() + 1;
    if (now == RAM->last_screen) return;
    RAM->last_screen = now; RAM->editor_text = 0;
    fx_deliver_on(GP50_EVENT_SCREEN, now - 1, now - 1, 0);
}
