#include "gp50_native.h"

static void setup(uint32_t engaged) {
    gp50_native.block[GP50_PRE].model = 0x05000008u;              /* C-Wah */
    gp50_native.block[GP50_PRE].param_count = 5;
    gp50_native.block[GP50_PRE].param[4].min = 0; gp50_native.block[GP50_PRE].param[4].max = 1;
    gp50_native.block[GP50_PRE].param[4].step = 1; gp50_native.block[GP50_PRE].param[4].value = 1.0f;
    gp50_native.block[GP50_PRE].enabled = engaged;
    gp50_native.expression = (gp50_expression){1, GP50_PRE, 3, 1, 500};
}
static void pedal(uint32_t permille, uint32_t ticks) { gp50_native.expression.position = (uint16_t)permille; gp50_native_ticks(ticks, 10); }

void gp50_test(void) {
    uint8_t r[8];
    /* Wah on, toe: nothing happens. Heel: bypass only after 200 ms. */
    setup(1); pedal(5, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);  /* old C-Wah byte is ignored */
    uint8_t config[] = {0, 255, 255};
    GP50_CHECK(gp50_native_host_set(config, 1) == GP50_REFUSED);
    config[0] = 2;
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    pedal(500, 3);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    pedal(5, 15);                                                 /* 150 ms at the heel */
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    pedal(5, 10);                                                 /* past 200 ms */
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[1] == 1 && r[2] == 1 && r[3] == 1);
    /* Hysteresis: 1.5 % keeps it bypassed; 2 % or more turns it back on. */
    pedal(15, 5);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    pedal(25, 1);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* A short heel visit (< 200 ms) does not bypass. */
    pedal(0, 10); pedal(300, 1);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* A bypass the player made while running (wah switched off at the toe) is left alone. */
    pedal(600, 2); gp50_native.block[GP50_PRE].enabled = 0; pedal(600, 3);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    /* A fresh start with the wah bypassed can engage immediately off heel. */
    gp50_native_boot(); setup(0);
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    pedal(600, 2);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* Conditions lost while we own a bypass: the wah comes back on. */
    setup(1); pedal(0, 30);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    config[0] = 1;
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    gp50_native_ticks(1, 10);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    config[0] = 2;
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    setup(1); gp50_native.expression.param = 5; pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    setup(1); gp50_native.expression.calibrated = 0; pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* CPU protection refusal can be retried on the next sweep. */
    setup(1); pedal(0, 30); GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    gp50_native.block[GP50_PRE].refuse_enable = 1; pedal(600, 3);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    gp50_native.block[GP50_PRE].refuse_enable = 0;
    pedal(600, 3);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    pedal(5, 1); pedal(600, 1);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* Preset change re-arms even when the new preset has the block bypassed. */
    setup(1); pedal(0, 30); gp50_native.preset = 7; pedal(0, 1);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[1] == 1 && r[2] == 0);
    pedal(600, 1);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);

    /* EXP follows the assigned block and preserves the status reply. */
    gp50_native_boot();
    setup(1);
    gp50_native.block[GP50_DST].model = 0x03000001u;
    gp50_native.block[GP50_DST].param_count = 2;
    gp50_native.block[GP50_DST].enabled = 1;
    gp50_native.expression.block = GP50_DST;
    gp50_native.expression.param = 1;
    config[0] = 3;
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_REFUSED);
    config[0] = 2;
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    gp50_native.block[GP50_DST].enabled = 0;
    pedal(5, 1); pedal(15, 1);
    GP50_CHECK(!gp50_native.block[GP50_DST].enabled);
    pedal(20, 1);
    GP50_CHECK(gp50_native.block[GP50_DST].enabled);
    pedal(5, 30);
    GP50_CHECK(!gp50_native.block[GP50_DST].enabled && gp50_native.block[GP50_PRE].enabled);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[0] == 2 && r[1] == 1 && r[2] == 1);
    gp50_native.expression.block = GP50_PRE;
    gp50_native.expression.param = 3;
    pedal(600, 1);
    GP50_CHECK(gp50_native.block[GP50_DST].enabled);
    pedal(0, 30);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    config[0] = 1;
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    gp50_native_save();
    gp50_native_load(9);
    pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled); /* no record defaults to Off */
    gp50_native.block[GP50_PRE].enabled = 1;
    gp50_native_load(0);
    pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled); /* explicit OFF survives normal save and load */

    /* Only knob 3 on the EXP range page can change the setting. VOL keeps PRE/Post. */
    char text[GP50_STATUS_TEXT_MAX + 1];
    uint32_t editor = GP50_SCREEN_EDITOR;
    GP50_CHECK(!gp50_native_knob(GP50_KNOB_3, 1, editor));
    gp50_native.editor_expression_page = 1;
    GP50_CHECK(!gp50_native_knob(GP50_KNOB_2, 1, editor));
    GP50_CHECK(gp50_native_knob(GP50_KNOB_3, 1, editor) == GP50_CONSUMED);
    GP50_CHECK(!gp50_native_status(text, sizeof text));
    gp50_native_save();
    gp50_native_load(9);
    gp50_native_load(0);
    pedal(5, 30);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled); /* On survives normal save and load */
    gp50_native.expression.block = GP50_BLOCKS;
    GP50_CHECK(!gp50_native_knob(GP50_KNOB_3, -1, editor));
    GP50_CHECK(!gp50_native_status(text, sizeof text));
    gp50_native_boot();
    setup(1);
    gp50_native.preset_data[0][0] = 2;
    gp50_native.preset_data_length[0] = 1;
    gp50_native_load(0);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[5] == 1 && r[6] == 200 && r[7] == 0);
    const uint8_t short_release[] = {0, 50, 0};
    GP50_CHECK(gp50_native_host_set(short_release, sizeof short_release) == GP50_OK);
    pedal(0, 5);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    pedal(0, 1);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    pedal(500, 1);
    gp50_native.editor_expression_page = 2;
    GP50_CHECK(!gp50_native_knob(GP50_KNOB_3, 2, editor));
    GP50_CHECK(gp50_native_knob(GP50_KNOB_1, 2, editor) == GP50_CONSUMED);
    gp50_native_save();
    gp50_native_load(9);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[5] == 0 && r[6] == 200);
    gp50_native_load(0);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[5] == 1 && r[6] == 70);
    const uint8_t invalid[] = {1, 209, 7};
    GP50_CHECK(gp50_native_host_set(invalid, sizeof invalid) == GP50_REFUSED);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 8 && r[5] == 1 && r[6] == 70);
    GP50_CHECK(gp50_native_knob(GP50_KNOB_1, INT32_MIN, editor) == GP50_CONSUMED);
    pedal(0, 1);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);

    /* Disabling or retargeting before the first sweep leaves the old block off. */
    gp50_native_boot();
    setup(0);
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    pedal(0, 1);
    const uint8_t off[] = {1, 255, 255};
    GP50_CHECK(gp50_native_host_set(off, sizeof off) == GP50_OK);
    pedal(600, 1);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    GP50_CHECK(gp50_native_host_set(config, sizeof config) == GP50_OK);
    pedal(0, 1);
    gp50_native.block[GP50_DST].model = 0x03000001u;
    gp50_native.block[GP50_DST].param_count = 2;
    gp50_native.expression.block = GP50_DST;
    gp50_native.expression.param = 1;
    pedal(0, 1); pedal(20, 1);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled && gp50_native.block[GP50_DST].enabled);
}
