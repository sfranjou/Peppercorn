#include <string.h>
#include "gp50_native.h"

void gp50_test(void) {
    char value[32];
    uint8_t reply[3];
    gp50_native.dsp_load = 47;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_1, value, sizeof value) == 3 && !strcmp(value, "47%"));
    GP50_CHECK(gp50_native_host_get(reply, sizeof reply) == 3 && reply[0] == 1 && reply[1] == 47 && reply[2] == 0);
    gp50_native.dsp_load = 107;   /* over 100 when the chain is too heavy */
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_1, value, sizeof value) && !strcmp(value, "107%"));
    gp50_native.dsp_load = 0;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_1, value, sizeof value) && !strcmp(value, "0%"));
    gp50_native.dsp_load = GP50_DSP_UNKNOWN;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_1, value, sizeof value) && !strcmp(value, "--"));
    GP50_CHECK(gp50_native_host_get(reply, sizeof reply) == 3 && reply[1] == 0xff && reply[2] == 0xff);
    gp50_native.dsp_load = 5000;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_1, value, sizeof value) && !strcmp(value, "999%") && strlen(value) <= GP50_MENU_TEXT_MAX);
    /* Measured lines: "--" until a reading, then percent of the block; stale readings show "--". */
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_2, value, sizeof value) == 2 && !strcmp(value, "--"));
    gp50_native.load.status = GP50_METER_OK; gp50_native.load.arm = 0.614f; gp50_native.load.dsp = 0.38f;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_2, value, sizeof value) && !strcmp(value, "61%"));
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_3, value, sizeof value) && !strcmp(value, "38%"));
    gp50_native.load.arm = 1.07f;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_2, value, sizeof value) && !strcmp(value, "107%"));
    gp50_native.load.arm = -1.0f;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_2, value, sizeof value) && !strcmp(value, "--"));
    gp50_native.load.status = GP50_METER_STALE;
    GP50_CHECK(gp50_native_menu_value(GP50_MENU_ITEM_3, value, sizeof value) && !strcmp(value, "--"));
    /* Read-only tile: no knob action, no About line, and the pedal state is untouched. */
    GP50_CHECK(gp50_native_menu_change(GP50_MENU_ITEM_1, 1) == 1);
    GP50_CHECK(gp50_native_about(value, sizeof value) == 0);
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_HOME) == 0);
    GP50_CHECK(!gp50_native.modified && gp50_native.notify_count == 0);
}
