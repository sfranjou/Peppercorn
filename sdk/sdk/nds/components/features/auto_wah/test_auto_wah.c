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
    uint8_t r[5];
    /* Wah on, toe: nothing happens. Heel: bypass only after 200 ms. */
    setup(1); pedal(500, 3);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    pedal(5, 15);                                                 /* 150 ms at the heel */
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    pedal(5, 10);                                                 /* past 200 ms */
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 5 && r[1] == 1 && r[2] == 1 && r[3] == 1);
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
    /* A fresh start with the wah bypassed owns it (MOD027): toe engages it. */
    gp50_native_boot(); setup(0); pedal(600, 2);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* Conditions lost while we own a bypass: the wah comes back on. */
    setup(1); pedal(0, 30);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    gp50_native.block[GP50_PRE].param[4].value = 0.0f;           /* Auto Engage switched off */
    gp50_native_ticks(1, 10);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* Not C-Wah, or pedal not on Position: never touches the block. */
    setup(1); gp50_native.block[GP50_PRE].model = 0x01000001u; pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    setup(1); gp50_native.expression.param = 2; pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    setup(1); gp50_native.expression.calibrated = 0; pedal(0, 30);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
    /* CPU protection refusing "on": not owned, retried later without crashing. */
    setup(1); pedal(0, 30); GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    gp50_native.block[GP50_PRE].refuse_enable = 1; pedal(600, 3);
    GP50_CHECK(!gp50_native.block[GP50_PRE].enabled);
    gp50_native.block[GP50_PRE].refuse_enable = 0;
    /* Preset change: state starts over for the new preset (a bypassed wah there counts as ours, as in MOD027). */
    setup(1); pedal(0, 30); gp50_native.preset = 7; pedal(0, 1);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 5 && r[1] == 1 && r[2] == 1);
    pedal(600, 1);
    GP50_CHECK(gp50_native.block[GP50_PRE].enabled);
}
