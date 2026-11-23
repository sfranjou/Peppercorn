#ifndef GP50_H
#define GP50_H
/* GP-50 feature SDK, ABI 3: everything a main-processor feature needs, in one header.
 *
 * A feature is a folder with component.json and C files. The platform calls your callbacks from the pedal's
 * application task (the loop that runs the screen, knobs, footswitches and USB/MIDI). You call the gp50_* services
 * below to read and change the pedal. You never see addresses, screen objects or firmware structures.
 *
 * Every callback gets `const gp50_ctx *ctx`; ctx->state is your private RAM (resources.state_bytes in the manifest),
 * zeroed at boot. Keep all your state there. Callbacks of one feature never run at the same time.
 *
 * Rules for every callback: return quickly, never wait or loop on hardware, no recursion, no allocation, do not keep
 * pointers to buffers you were given after you return. Services may be called from any callback unless noted.
 *
 * Results: services that can fail return GP50_OK (0) or GP50_REFUSED (1). Refused means nothing changed.
 *
 * See sdk/DEVELOPER_GUIDE.md section 4 for a walk-through and sdk/nds/components/native/ to run features on a
 * computer before building an image.
 */
#include <stdint.h>

#define GP50_ABI 3
#define GP50_OK 0u
#define GP50_REFUSED 1u

/* ---- Platform limits (the build checks manifests against these; use the names, not the numbers) -------------- */

#define GP50_STATE_BYTES_MAX 4088u      /* resources.state_bytes */
#define GP50_STACK_BYTES_MAX 512u       /* resources.stack_bytes */
#define GP50_HOST_SELECTOR_FIRST 0x76u  /* host.selector range for features */
#define GP50_HOST_SELECTOR_LAST 0x7eu
/* Existing own commands a feature may take over (same wire format; one feature each): */
#define GP50_HOST_SELECTOR_ASSIGN 0x71u /* knob assignment, 11/12 71 */
#define GP50_HOST_SELECTOR_AB 0x74u     /* A/B footswitches, 11/12 74 */
#define GP50_HOST_SELECTOR_DRUM 0x75u   /* drum play / drum window, 11/12 75 */
#define GP50_HOST_BYTES_MAX 40u         /* host.set_bytes and host.max_reply_bytes */
#define GP50_STATUS_TEXT_MAX 31u        /* status line characters (the buffer has room for the NUL) */
#define GP50_PRESET_BYTES_MAX 32u       /* preset_bytes per feature */
#define GP50_MENU_ITEMS_MAX 3u          /* items on a feature's Global settings tile, one per knob (knob 1 = item 1) */
#define GP50_MENU_TEXT_MAX 13u          /* characters in a menu item label or item value */
#define GP50_MENU_TITLE_MAX 9u          /* characters in the tile title (the stock tiles fit about 9 per line) */
#define GP50_MENU_TILES_MAX 1u          /* feature tiles in Global settings: the menu has one free slot (12th tile) */
#define GP50_NAME_TEXT_MAX 15u          /* characters in a model or parameter name */
#define GP50_ABOUT_LINES_MAX 2u         /* extra lines on the Global settings > About page, all features together */
#define GP50_ABOUT_TEXT_MAX 18u         /* characters in one About line (centred under the copyright text) */

/* Menu item numbers, in the order of manifest "menu.items". */
enum { GP50_MENU_ITEM_1, GP50_MENU_ITEM_2, GP50_MENU_ITEM_3 };

/* Physical controls, for gp50_event.index. */
enum { GP50_FOOTSWITCH_LEFT = 0, GP50_FOOTSWITCH_RIGHT = 1, GP50_FOOTSWITCHES = 2 };
enum { GP50_KNOB_1 = 0, GP50_KNOB_2 = 1, GP50_KNOB_3 = 2, GP50_KNOBS = 3 };

typedef struct {
    void *state;            /* your private RAM, resources.state_bytes long, zeroed at boot */
    uint32_t state_bytes;
} gp50_ctx;

/* ---- Blocks (the effect chain) -------------------------------------------------------------------------------- */

/* Block numbers, in signal order. Each block holds one model (or is empty) and can be on or off. */
enum {
    GP50_NR = 0, GP50_PRE = 1, GP50_DST = 2, GP50_AMP = 3, GP50_CAB = 4,
    GP50_EQ = 5, GP50_MOD = 6, GP50_DLY = 7, GP50_RVB = 8, GP50_NS = 9,
    GP50_BLOCKS = 10
};

/* Public model ID of the block's current model (the IDs Valeton Suite and the web editor use), 0 if empty or invalid
 * block. Compare models by ID, never by list position: positions change with the effect set. */
uint32_t gp50_block_model(uint32_t block);
/* 1 if the block is on, 0 if off or invalid. */
uint32_t gp50_block_enabled(uint32_t block);
/* Turn a block on (on = 1) or off (on = 0), exactly as its footswitch or the editor would, including CPU protection:
 * GP50_REFUSED if the block is invalid or turning it on would overload the DSP. Marks the preset modified. */
uint32_t gp50_block_set_enabled(uint32_t block, uint32_t on);
/* Select a model by public ID in a block. GP50_REFUSED if the ID is not available in that block or refused by CPU
 * protection. */
uint32_t gp50_block_select(uint32_t block, uint32_t model_id);
/* Number of models available in a block, and the public ID of model `index` (0 when out of range): for browsing. */
uint32_t gp50_block_model_count(uint32_t block);
uint32_t gp50_block_model_at(uint32_t block, uint32_t index);
/* Name of the block's current model, as on the screen. Writes at most capacity-1 characters plus a NUL and returns the
 * length (0 if empty). */
uint32_t gp50_block_name(uint32_t block, char *out, uint32_t capacity);

/* ---- Parameters of the current model in a block --------------------------------------------------------------- */

/* Values are in the parameter's own displayed unit (for example 0..100 for Gain, milliseconds for a delay time). */
uint32_t gp50_param_count(uint32_t block);
uint32_t gp50_param_get(uint32_t block, uint32_t param, float *value);
uint32_t gp50_param_range(uint32_t block, uint32_t param, float *min, float *max, float *step);
/* Set a parameter as if its knob were turned: the value is clamped to the range and rounded to the step, the sound
 * changes, the screen and connected editors are told, and the preset is marked modified. */
uint32_t gp50_param_set(uint32_t block, uint32_t param, float value);
/* Parameter name, as on the screen (same writing rules as gp50_block_name). */
uint32_t gp50_param_name(uint32_t block, uint32_t param, char *out, uint32_t capacity);

/* Value as the screen shows it (unit and rounding included), same writing rules as gp50_block_name. */
uint32_t gp50_param_text(uint32_t block, uint32_t param, char *out, uint32_t capacity);
/* Move a parameter by `steps` knob detents exactly as its knob would (stock acceleration on fast turns, stops at the
 * ends, sound/screen/editors updated, preset marked modified). */
uint32_t gp50_param_nudge(uint32_t block, uint32_t param, int32_t steps);

/* ---- Screens and pedal mode --------------------------------------------------------------------------------- */

uint32_t gp50_screen(void);                 /* GP50_SCREEN_HOME / _EDITOR / _DRUM / _OTHER */
/* Go to the home screen or the drum screen (GP50_SCREEN_HOME / GP50_SCREEN_DRUM); GP50_REFUSED otherwise. */
uint32_t gp50_screen_open(uint32_t screen);
enum { GP50_MODE_PATCH = 0, GP50_MODE_STOMP = 1 };
uint32_t gp50_pedal_mode(void);             /* GP50_MODE_STOMP when the footswitches are in Stomp mode */

/* ---- Screen services (call from event or tick callbacks; GP50_REFUSED before the screen has been seen) -------- */

#define GP50_NONE 0xffu
/* Block the effect editor shows (GP50_BLOCKS when none) and the parameter knob `knob` (GP50_KNOB_1..3) edits on its
 * current page (GP50_NONE when that knob edits nothing there). */
uint32_t gp50_editor_block(void);
uint32_t gp50_editor_knob_param(uint32_t knob);
/* EXP editor page, or 0 at the assignment page, outside EXP or behind a dialog. */
uint32_t gp50_editor_expression_page(void);
#define GP50_EXPRESSION_RELEASE_MAX 2000
enum { GP50_TEXT_PROMPT = 0, GP50_TEXT_PAGE = 1 };
/* Show text in the effect editor: PROMPT = the title strip (one or two short lines), PAGE = the whole screen (up to
 * about 8 lines, "\n" separated). gp50_editor_text_clear() gives the editor back its own title. */
uint32_t gp50_editor_text(const char *text, uint32_t kind);
void gp50_editor_text_clear(void);
/* Home screen title (normally the preset name): show text, or give back the preset name. */
uint32_t gp50_home_title(const char *text);
void gp50_home_title_restore(void);
/* Home knob tiles (GP50_KNOB_1..3): show a name, a value text and a bar at percent (0..100) instead of the stock
 * Master / BPM / P-VOL tile; reset gives the stock tile back. */
uint32_t gp50_home_knob_tile(uint32_t knob, const char *name, const char *value, uint32_t percent);
void gp50_home_knob_tile_reset(uint32_t knob);

/* ---- Drum machine -------------------------------------------------------------------------------------------- */

uint32_t gp50_drum_playing(void);           /* 1 while the drum plays */
void gp50_drum_set_playing(uint32_t on);

/* ---- Presets -------------------------------------------------------------------------------------------------- */

/* Current preset number, 0-based (the screen shows it +1). */
uint32_t gp50_preset_number(void);
/* Mark the current preset as modified (the screen shows it; Save stores it). Parameter and block services already do
 * this; call it when your own per-preset data (preset_save callback) changed. */
void gp50_preset_mark_modified(void);

/* ---- Control assignments (knob and footswitch A/B bindings, saved with each preset by the platform) ---------- */

typedef struct { uint8_t valid, block, param, reserved; uint32_t model; } gp50_knob_binding;
typedef struct { uint8_t valid, block, param, flags; uint32_t model; float a, b; } gp50_footswitch_binding;
typedef struct {
    uint8_t preset;           /* preset these bindings belong to (the current one), GP50_NONE before any load */
    uint8_t fault;            /* this preset's stored assignment data is damaged: Save is blocked until recovered */
    uint8_t blocked;          /* bit per footswitch: its stored binding was lost to damage (its presses do nothing) */
    uint8_t reserved;
    gp50_knob_binding knob[GP50_KNOBS];
    gp50_footswitch_binding footswitch[GP50_FOOTSWITCHES];
} gp50_assignments;
/* The live bindings of the current preset (what Save stores; restored on every preset load). A binding is live only
 * while its block still holds `model`. */
uint32_t gp50_assignments_get(gp50_assignments *out);
/* Replace the live bindings (preset must be the current one; fault/blocked are platform-owned and ignored). Call
 * gp50_preset_mark_modified() when the change should be saved. GP50_REFUSED on a stale preset or invalid entries. */
uint32_t gp50_assignments_set(const gp50_assignments *in);
/* Explicit recovery of damaged data: clear every knob and footswitch binding and the fault (preset marked modified). */
uint32_t gp50_assignments_recover(void);

/* ---- Time and system ------------------------------------------------------------------------------------------ */

/* Milliseconds since boot, wrapping after about 49.7 days. Subtract with gp50_elapsed_ms. */
uint32_t gp50_millis(void);
static inline uint32_t gp50_elapsed_ms(uint32_t now, uint32_t then) { return now - then; }
/* Estimated processing load of the current chain in percent (can exceed 100), the figure CPU protection uses; or
 * GP50_DSP_UNKNOWN when the platform has no estimate. */
#define GP50_DSP_UNKNOWN 0xffffffffu
uint32_t gp50_dsp_load(void);

/* ---- Audio-processor meters ------------------------------------------------------------------------------------ */

enum {
    GP50_METER_OK = 0,        /* gain_reduction is valid */
    GP50_METER_NO_DATA = 1,   /* no reading yet ("--") */
    GP50_METER_ERROR = 2,     /* the audio processor reported an error */
    GP50_METER_STALE = 3,     /* last reading older than 1 s */
    GP50_METER_NONE = 4,      /* no block reports gain reduction */
    GP50_METER_BYPASSED = 5,  /* the reporting block is off */
};
typedef struct {
    uint8_t status;           /* GP50_METER_* */
    uint8_t block;            /* block that reports gain reduction (valid with OK/BYPASSED) */
    uint16_t gain_reduction;  /* gain reduction in 0.01 dB (valid with OK) */
} gp50_meter;
/* Latest meter readings. Calling it also asks the audio processor for fresh values (about 10 per second while you
 * keep calling it), so call it only while you show them. */
uint32_t gp50_meter_get(gp50_meter *out);
/* Sampled end-of-audio-block reduction from stock Gate and COMP/COMP4. */
uint32_t gp50_stock_meters_get(gp50_meter *gate, gp50_meter *pre);

/* ---- Measured processor load (the `12 50` load bridge) -------------------------------------------------------- */

/* Latest load the audio processors report: `arm` is the main audio processor's busy fraction of an audio block
 * (1.0 = the whole block); `dsp` is the audio coprocessor's own busy ratio on the same scale (its clock is not
 * identified, so do not add it to `arm`). The figure CPU protection uses is gp50_dsp_load() (an estimate, available
 * at once). Calling this also asks for a fresh reading (at most about 10 per second while you keep calling it). */
typedef struct {
    uint8_t status;           /* GP50_METER_OK, GP50_METER_NO_DATA (none yet / not in this build) or GP50_METER_STALE */
    float arm, dsp;           /* valid with GP50_METER_OK and GP50_METER_STALE (the last reading) */
} gp50_load;
uint32_t gp50_load_get(gp50_load *out);

/* ---- Expression pedal ----------------------------------------------------------------------------------------- */

typedef struct {
    uint8_t enabled;      /* 1 when the pedal input is on and used as an expression pedal (global EXP mode) */
    uint8_t block;        /* block its assignment drives (GP50_NR..GP50_NS), or GP50_BLOCKS when none */
    uint8_t param;        /* parameter of that block's model it drives */
    uint8_t calibrated;   /* 1 when a usable calibration exists (otherwise position is 0) */
    uint16_t position;    /* calibrated position in permille: 0 = heel, 1000 = toe */
} gp50_expression;
/* Read expression pedal `pedal` (only 0 exists). GP50_REFUSED for other numbers. Cheap; call it from tick. */
uint32_t gp50_expression_get(uint32_t pedal, gp50_expression *out);

/* ---- Host (computer, phone, web page over USB/MIDI) ----------------------------------------------------------- */

/* Send an unsolicited reply on your own selector, as if the host had asked: the host receives `12 <selector>
 * <payload>`. Use it to tell an editor your state changed on the pedal. At most host.max_reply_bytes bytes.
 * GP50_REFUSED when no host is connected or the link is busy (try again on a later tick). Not from init. */
uint32_t gp50_host_notify(const uint8_t *payload, uint32_t length);

/* ---- Events (callbacks.event) --------------------------------------------------------------------------------- */

enum {
    GP50_EVENT_FOOTSWITCH = 1,  /* index: GP50_FOOTSWITCH_LEFT/RIGHT; value 1 = pressed */
    GP50_EVENT_KNOB = 2,        /* index: GP50_KNOB_1..3 (left to right); value: movement in steps (+ clockwise) */
    GP50_EVENT_PRESET = 3,      /* a preset has been loaded and is now current; index: its number */
    GP50_EVENT_ENCODER = 4,     /* the main encoder turned; value: steps (+ clockwise) */
    GP50_EVENT_BACK = 5,        /* EXIT/back pressed */
    GP50_EVENT_DRUM = 6,        /* DRUM pressed */
    GP50_EVENT_DRUM_HOLD = 7,   /* DRUM held */
    GP50_EVENT_PARA = 8,        /* PARA pressed (the editor uses it to switch pages unless a feature consumes it) */
    GP50_EVENT_SCREEN = 9,      /* the screen changed; index: the new GP50_SCREEN_* (cannot be consumed) */
};
enum { GP50_SCREEN_HOME = 0, GP50_SCREEN_EDITOR = 1, GP50_SCREEN_OTHER = 2, GP50_SCREEN_DRUM = 3 };
typedef struct {
    uint8_t kind, index, screen, reserved;
    int32_t value;
} gp50_event;
/* Where events come from on this platform version:
 *   FOOTSWITCH  every press the pedal would turn into a block toggle, on any screen, unless the switch is configured
 *               as an A/B parameter switch (that platform feature answers first);
 *   KNOB        knob turns on the home screen, unless knob assignment drives that knob (that answers first);
 *               with the SDK assignment feature present, also on the editor screen;
 *   ENCODER, BACK, DRUM, DRUM_HOLD, PAGE   on the home and editor screens when an SDK feature takes over the
 *               assignment flows (GP50_FEATURE_ASSIGNMENT builds); otherwise the platform keeps them;
 *   PRESET      after every preset load, delivered from the next service pass (never inside the load itself).
 * An event callback returns GP50_CONSUMED to take the event (the pedal's normal action does not happen) or
 * GP50_PASS to let it continue. Features see events in id order; the first one that consumes wins. PRESET events
 * cannot be consumed (the return value is ignored). If your feature is busy (another of your callbacks is running),
 * the event passes to the pedal. */
#define GP50_PASS 0u
#define GP50_CONSUMED 1u

/* ---- Effect editor meter strip (callbacks.strip) -------------------------------------------------------------- */

/* The strip at the top of the effect editor, drawn by the platform: a label on the top left, a value on
 * the top right (about 24 characters together, no wrapping) and a bar below. A feature asks for it per edited block; higher-priority owners (assignment
 * prompts, CPU refusal) still win. */
typedef struct {
    char label[16];           /* e.g. "Gain Reduction" (NUL-terminated) */
    char value[8];            /* e.g. "3.5 dB" or "--" */
    uint16_t level, level_max;   /* bar position: level out of level_max (level_max > 0) */
} gp50_strip;

/* ---- Callback signatures (names come from component.json "callbacks") ----------------------------------------- */
/*
 * void     init(const gp50_ctx *ctx);                               once at boot, before the screen and USB exist
 * void     tick(const gp50_ctx *ctx);                               repeatedly from the application loop
 * uint32_t get(const gp50_ctx *ctx, uint8_t *out, uint32_t cap);    host sent `12 <selector>`: write the reply, return
 *                                                                   its length (schema byte first), 0 = refuse
 * uint32_t set(const gp50_ctx *ctx, const uint8_t *in, uint32_t n); host sent `11 <selector> <n bytes>`: 0 = accepted
 * uint32_t event(const gp50_ctx *ctx, const gp50_event *e);         GP50_CONSUMED or GP50_PASS
 * uint32_t status(const gp50_ctx *ctx, char *out, uint32_t cap);    effect editor status line text, 0 = none; must not
 *                                                                   change state
 * uint32_t strip(const gp50_ctx *ctx, uint32_t block, gp50_strip *s); editor showing `block`: fill s and return 1 to
 *                                                                   show a meter strip, 0 for none; called about 10
 *                                                                   times a second while that editor is open
 * uint32_t preset_save(const gp50_ctx *ctx, uint8_t *out, uint32_t cap);      write your per-preset bytes, return count
 * void     preset_load(const gp50_ctx *ctx, const uint8_t *in, uint32_t n);   n = 0: the preset has none, use defaults
 * uint32_t about(const gp50_ctx *ctx, char *out, uint32_t cap);    one line for Global settings > About, under the
 *                                                                   copyright (up to GP50_ABOUT_TEXT_MAX characters, 0 =
 *                                                                   none); read when the page opens; must not
 *                                                                   change state. Features in id order share
 *                                                                   GP50_ABOUT_LINES_MAX lines.
 * uint32_t menu_value(const gp50_ctx *ctx, uint32_t item, char *out, uint32_t cap);  value text shown for a menu
 *                                                                   item (up to GP50_MENU_TEXT_MAX characters, 0 =
 *                                                                   none); read when the tile is selected and about
 *                                                                   twice a second while it stays selected; must not
 *                                                                   change state
 * uint32_t menu_change(const gp50_ctx *ctx, uint32_t item, int32_t delta);   knob `item + 1` turned while your tile is
 *                                                                   selected (delta: signed knob steps); 0 = done.
 *                                                                   Optional: without it the tile only shows values.
 *
 * Global settings tile (manifest "menu": {"title": "...", "items": ["...", ...]}): the 12th tile of Global settings,
 * after About (the stock menu has 11 tiles in 3 pages of 4, so one slot is free: GP50_MENU_TILES_MAX). Selecting it
 * with the encoder shows one centred line per item, "<item label>: <menu_value text>". Knobs 1..3 call menu_change
 * for items 1..3; the PARA press does nothing on the tile. The firmware build refuses a second feature with a menu.
 */

#endif
