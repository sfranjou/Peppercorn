#ifndef GP50_FEATURES_H
#define GP50_FEATURES_H
/* Platform dispatch for ABI 3 feature components (sdk/nds/components/gp50.h). Platform-internal: authors never
 * include this. The generated registry (component_registry.h) defines gp50_feature_table / GP50_FEATURE_COUNT and the
 * RAM block GP50_FEATURES_RAM; hooks in the platform call the gp50_features_* entry points below.
 *
 * Ownership: each feature has a gate word (0 not started, 1 ready, 2 a callback is running), claimed and released
 * under the stock interrupt guard like experimental ABI 2. A callback never runs while another callback of the same
 * feature runs; a busy feature is skipped (events pass to the pedal, host requests are refused, ticks are skipped).
 * All entry points run in the application task.
 */
#include <stdint.h>
#include "../gp50.h"

typedef struct {
    gp50_ctx ctx;
    const char *id;            /* manifest id: key of this feature's record in the per-preset area */
    volatile uint32_t *gate;
    uint32_t selector, set_bytes, max_reply_bytes, preset_bytes;
    void (*init)(const gp50_ctx *);
    void (*tick)(const gp50_ctx *);
    uint32_t (*get)(const gp50_ctx *, uint8_t *, uint32_t);
    uint32_t (*set)(const gp50_ctx *, const uint8_t *, uint32_t);
    uint32_t (*event)(const gp50_ctx *, const gp50_event *);
    uint32_t (*status)(const gp50_ctx *, char *, uint32_t);
    uint32_t (*preset_save)(const gp50_ctx *, uint8_t *, uint32_t);
    void (*preset_load)(const gp50_ctx *, const uint8_t *, uint32_t);
    uint32_t (*menu_value)(const gp50_ctx *, uint32_t, char *, uint32_t);
    uint32_t (*menu_change)(const gp50_ctx *, uint32_t, int32_t);
    uint32_t (*about)(const gp50_ctx *, char *, uint32_t);
    uint32_t (*strip)(const gp50_ctx *, uint32_t, gp50_strip *);
    const char *menu_title;                       /* manifest menu (Global settings tile), 0 = none */
    const char *menu_items[GP50_MENU_ITEMS_MAX];
    uint32_t menu_count;
} gp50_feature_entry;

/* Per-preset area: preset slot k (1 KiB at flash (k + 1500) << 10) bytes +576..+1023, blank (FF) in every slot on the
 * test pedal before first use (work/sdk_abi3_hw/preset_area_*). Format "GPFX" v1, little endian:
 *   +0 u32 magic 0x58465047 ("GPFX")  +4 u16 version 1  +6 u16 used (record bytes)
 *   +8 u32 CRC32 of the slot's 426-byte stock record (binds the area to its record, as GPAM does)
 *   +12 records {u8 id length, u8 payload length, id, payload} (used bytes), then u32 CRC32 of [+0, +12 + used);
 *   the rest stays FF. A record whose feature is absent from the image is dropped at the next save. */
#define GP50_AREA_OFFSET 576u
#define GP50_AREA_BYTES 448u
#define GP50_AREA_MAGIC 0x58465047u
#define GP50_AREA_RECORDS (GP50_AREA_BYTES - 16u)

/* Platform RAM (GP50_FEATURES_RAM, zeroed by init): */
typedef struct {
    uint32_t current;          /* feature index + 1 while one of its callbacks runs, else 0 (gp50_host_notify) */
    uint32_t preset_loads;     /* incremented by the preset-load hooks */
    uint32_t preset_seen;      /* loads already delivered as PRESET events */
    uint32_t load_valid;       /* load_area holds a validated area of the loaded preset */
    uint32_t save_owner;       /* preset the save snapshot belongs to + 1 (0 = none / being rebuilt) */
    uint32_t save_used;        /* record bytes in save_records */
    uint32_t home_ctx;         /* last home window context seen by a home handler (screen services), 0 = none */
    uint32_t editor_ctx;       /* last effect editor window context, 0 = none */
    uint32_t last_screen;      /* screen seen by the last service pass + 1 (SCREEN notices) */
    uint32_t editor_text;      /* 1 while a feature shows editor prompt/page text (other strip owners stand aside) */
    uint32_t settings_ctx;     /* Global settings window context while the feature tile is selected, else 0 */
    uint32_t settings_label;   /* label the platform made on that tile's panel (deleted with the panel), else 0 */
    uint32_t settings_ms;      /* gp50_millis() of the last tile panel refresh */
    uint8_t load_area[GP50_AREA_BYTES];
    uint8_t save_records[GP50_AREA_RECORDS];
} gp50_features_ram;

/* Called from the generated registry wrappers (one per feature and role). */
void gp50_feature_init(const gp50_feature_entry *);
void gp50_feature_tick(const gp50_feature_entry *);
uint32_t gp50_feature_get(const gp50_feature_entry *, uint8_t *, uint32_t);
uint32_t gp50_feature_set(const gp50_feature_entry *, const uint8_t *, uint32_t);
uint32_t gp50_feature_status(const gp50_feature_entry *, char *, uint32_t);

/* Called from platform hooks. Return 1 when a feature consumed the event (the pedal must not act on it). */
uint32_t gp50_features_footswitch(uint32_t index);
uint32_t gp50_features_knob(uint32_t index, int32_t steps);
/* A preset load replaced the active preset (called inside the load; delivery is deferred to the next tick). */
void gp50_features_preset_loaded(void);
/* Before the first feature tick of each GUI service pass: deliver pending PRESET events (with stored preset bytes),
 * then refresh the save snapshot. */
void gp50_features_service(void);
/* Preset read hook (active record only): read and validate the slot's area into load_area. */
void gp50_features_preset_read(uint32_t record, uint32_t index);
/* Sector staging hook: write the area for a 426-byte record staged at `destination` (1 KiB quarter). */
void gp50_features_stage(uint8_t *destination, const uint8_t *record, uint32_t active);

/* About page hook (stock 0x1f088, the last bounded strcat building the Global settings About text): appends the
 * stock text, then one line per feature `about` callback while it fits the 100-byte buffer. */
char *gp50_about_append(char *dst, const char *src, uint32_t capacity);

/* Global settings feature tile (GP50_FEATURES_MENU: one ABI 3 feature has a manifest menu). Stock window 9 has 11 tiles
 * in 3 pages of 4; the platform fills the free 12th slot (page 3, slot 4):
 *   gp50_settings_open   hook of the window-9 open's handler-table registration (0x1f23c, jal 0x177aa): forgets the
 *                        previous tile panel, registers gp50_settings_table (the stock table with the encoder, knob
 *                        and PARA entries wrapped);
 *   gp50_settings_label  hook of the tile label fetch in the item loop (0x1f812, jal 0x15f0c): the 12th label (UI
 *                        text id 0x4e, which stock never asks for: the loop skipped the slot) is the menu title;
 *   0x1f60e j 0x1f808    the item loop builds 4 items on every page (stock skipped page 3 slot 4). */
uint32_t gp50_settings_open(uint32_t table, uint32_t window);
const char *gp50_settings_label(uint32_t text_id);
uint32_t gp50_settings_encoder(uint8_t *ctx, uint8_t *event);
uint32_t gp50_settings_knob(uint8_t *ctx, uint8_t *event);
uint32_t gp50_settings_press(uint8_t *ctx, uint8_t *event);
extern const uint32_t gp50_settings_table[18];

/* Effect editor strip: first feature (id order) that wants a meter strip for `block`; 1 = s filled (validated). */
uint32_t gp50_features_strip(uint32_t block, gp50_strip *s);

/* Window-table dispatch (legacy_ui tables with GP50_FEATURE_ASSIGNMENT): offer the key/encoder message `word` on
 * `screen` (window context ctx, message event) to features; 1 = consumed. */
uint32_t gp50_features_ui(uint32_t screen, uint32_t word, uint32_t ctx, uint32_t event);
/* 1 while a feature shows text in the editor (gr_meter.c / admission give the strip way). */
uint32_t gp50_features_editor_text_active(void);
/* Editor/home tick hooks: remember the window context for the screen services. */
void gp50_features_screen_ctx(uint32_t screen, uint32_t ctx);
uint32_t gp50_ui_home_tick(uint32_t ctx, uint32_t event);

/* For gp50_services.c. */
uint32_t gp50_features_current_selector(void);
uint32_t gp50_platform_cpu_percent(void);

#endif
