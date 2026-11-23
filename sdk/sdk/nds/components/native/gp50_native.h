#ifndef GP50_NATIVE_H
#define GP50_NATIVE_H
/* Native (computer) test platform for GP-50 feature components (ABI 3).
 *
 * It implements every gp50_* service from gp50.h over a simulated pedal, and lets a test drive your feature: press
 * footswitches, turn knobs, load presets, send host messages, advance time. Build and run with
 *
 *     python3 sdk/nds/components/native/run_native.py <component folder>
 *
 * which compiles your sources, every test_*.c in your folder, this platform and a generated callback table with the
 * computer's C compiler. A test file defines `void gp50_test(void)` and uses GP50_CHECK.
 *
 * The simulation is a model of the pedal's behaviour as documented in gp50.h, not an emulator of the firmware.
 */
#include <stdint.h>
#include <stdio.h>
#include "../gp50.h"

#define GP50_NATIVE_PRESETS 100u
#define GP50_NATIVE_PARAMS 8u
#define GP50_NATIVE_PRESET_BYTES GP50_PRESET_BYTES_MAX

typedef struct {
    char name[GP50_NAME_TEXT_MAX + 1];
    float value, min, max, step;
} gp50_native_param;

typedef struct {
    uint32_t model, enabled, refuse_enable;  /* refuse_enable: simulate CPU protection refusing "on" */
    char name[GP50_NAME_TEXT_MAX + 1];
    uint32_t param_count;
    gp50_native_param param[GP50_NATIVE_PARAMS];
} gp50_native_block;

typedef struct {
    gp50_native_block block[GP50_BLOCKS];
    uint32_t preset, modified, millis, dsp_load, host_connected;
    uint32_t stock_actions;                 /* events the pedal handled itself (nobody consumed) */
    gp50_expression expression;             /* what gp50_expression_get(0) returns */
    gp50_meter meter;                       /* what gp50_meter_get returns */
    gp50_load load;                         /* what gp50_load_get returns */
    uint32_t screen, pedal_mode, drum_playing, nudges;
    uint32_t editor_block, editor_knob_param[3];   /* what the editor shows / which parameter each knob edits */
    char editor_text[160]; uint32_t editor_text_kind, editor_text_shown;
    char home_title[40]; uint32_t home_title_custom;
    struct { char name[24], value[24]; uint32_t percent, custom; } tile[3];
    gp50_assignments assignments;           /* live bindings (preset field follows gp50_native.preset) */
    uint32_t meter_reads;
    uint8_t last_notify[GP50_HOST_BYTES_MAX];
    uint32_t last_notify_length, notify_count;
    uint8_t preset_data[GP50_NATIVE_PRESETS][GP50_NATIVE_PRESET_BYTES];
    uint32_t preset_data_length[GP50_NATIVE_PRESETS];
} gp50_native_pedal;

/* The simulated pedal; tests may read and change it directly. */
extern gp50_native_pedal gp50_native;

/* Reset the pedal to a default chain (every block filled, delay off) and run the feature's init. */
void gp50_native_boot(void);
/* Run the feature's tick `count` times, advancing the clock by `ms_per_tick` each time. */
void gp50_native_ticks(uint32_t count, uint32_t ms_per_tick);
/* Deliver events. Return 1 if the feature consumed it, 0 if the pedal handled it. */
uint32_t gp50_native_footswitch(uint32_t index, uint32_t screen);
uint32_t gp50_native_knob(uint32_t index, int32_t steps, uint32_t screen);
/* Any event (GP50_EVENT_*) on a screen; also sets gp50_native.screen. 1 = consumed. */
uint32_t gp50_native_event(uint32_t kind, uint32_t index, uint32_t screen, int32_t value);
/* Save the current preset (calls preset_save) and load preset `number` (calls preset_load, then a PRESET event). */
void gp50_native_save(void);
void gp50_native_load(uint32_t number);
/* Host messages. get returns the reply length (0 = refused) into out; set returns 0 accepted / 1 refused. */
uint32_t gp50_native_host_get(uint8_t *out, uint32_t capacity);
uint32_t gp50_native_host_set(const uint8_t *in, uint32_t length);
/* Status line and menu text (0 = none). */
uint32_t gp50_native_status(char *out, uint32_t capacity);
uint32_t gp50_native_menu_value(uint32_t item, char *out, uint32_t capacity);
uint32_t gp50_native_menu_change(uint32_t item, int32_t delta);
/* The feature's effect editor meter strip for `block` (1 = shown, s filled). */
uint32_t gp50_native_strip(uint32_t block, gp50_strip *s);
/* The feature's About page line (0 = none). */
uint32_t gp50_native_about(char *out, uint32_t capacity);

/* Test checks. */
extern uint32_t gp50_native_failures, gp50_native_checks;
#define GP50_CHECK(condition) do { gp50_native_checks++; if (!(condition)) { gp50_native_failures++; \
    printf("%s:%d: check failed: %s\n", __FILE__, __LINE__, #condition); } } while (0)
void gp50_test(void);

#endif
