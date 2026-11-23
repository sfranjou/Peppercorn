#include <string.h>
#include "gp50_native.h"

void gp50_test(void) {
    /* Nothing chosen yet: the right footswitch keeps its normal job. */
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_HOME) == 0);
    GP50_CHECK(gp50_native.stock_actions == 1);
    gp50_native.stock_actions = 0; gp50_native.block[GP50_MOD].enabled = 1;
    char text[32];
    GP50_CHECK(gp50_native_status(text, sizeof text) == 0);

    /* A computer chooses the delay; the right footswitch on the home screen now toggles it instead. */
    uint8_t dly = GP50_DLY;
    GP50_CHECK(gp50_native_host_set(&dly, 1) == 0);
    GP50_CHECK(!gp50_native.block[GP50_DLY].enabled);
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_HOME) == 1);
    GP50_CHECK(gp50_native.block[GP50_DLY].enabled);
    GP50_CHECK(gp50_native.stock_actions == 0);
    GP50_CHECK(gp50_native.notify_count == 1 && gp50_native.last_notify[2] == 1);

    /* Left footswitch and other screens keep their normal behaviour. */
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_LEFT, GP50_SCREEN_HOME) == 0);
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_EDITOR) == 0);
    GP50_CHECK(gp50_native.stock_actions == 2);

    /* CPU protection refuses turning a block on: the press is still taken, nothing changes. */
    gp50_native.block[GP50_DLY].enabled = 0; gp50_native.block[GP50_DLY].refuse_enable = 1;
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_HOME) == 1 && !gp50_native.block[GP50_DLY].enabled);
    gp50_native.block[GP50_DLY].refuse_enable = 0;

    /* Host chooses the reverb; read back; bad values refused. */
    uint8_t reply[3], rvb = GP50_RVB, bad = 12, off = 0xff;
    GP50_CHECK(gp50_native_host_set(&rvb, 1) == 0 && gp50_native.modified);
    GP50_CHECK(gp50_native_host_get(reply, sizeof reply) == 3 && reply[0] == 1 && reply[1] == GP50_RVB);
    GP50_CHECK(gp50_native_host_set(&bad, 1) == 1);

    /* Status line names the block. */
    GP50_CHECK(gp50_native_status(text, sizeof text) && !strcmp(text, "FS2: RVB"));

    /* The choice is per preset: saved in preset 0, preset 1 has none (off), back to 0 restores it. */
    gp50_native_save();
    gp50_native_load(1);
    GP50_CHECK(gp50_native_host_get(reply, sizeof reply) == 3 && reply[1] == 0xff);
    GP50_CHECK(gp50_native_host_set(&off, 1) == 0);
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_HOME) == 0);   /* off: normal footswitch */
    GP50_CHECK(gp50_native_status(text, sizeof text) == 0);
    gp50_native_load(0);
    GP50_CHECK(gp50_native_host_get(reply, sizeof reply) == 3 && reply[1] == GP50_RVB);
}
