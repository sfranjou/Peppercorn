#include <string.h>
#include "gp50_native.h"

static void bind(uint32_t fs, float a, float b) {
    gp50_native.assignments.footswitch[fs] = (gp50_footswitch_binding){ 1, GP50_DLY, 1, 0, gp50_native.block[GP50_DLY].model, a, b };
}
void gp50_test(void) {
    gp50_native.screen = GP50_SCREEN_HOME;
    /* Unbound: the stock toggle runs. */
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_LEFT, GP50_SCREEN_HOME) == 0 && gp50_native.stock_actions == 1);
    /* Bound: A <-> B; anything else goes to A. */
    bind(0, 20, 80); gp50_native.block[GP50_DLY].param[1].value = 33;
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_LEFT, GP50_SCREEN_HOME) == 1 && gp50_native.block[GP50_DLY].param[1].value == 20);
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_LEFT, GP50_SCREEN_EDITOR) == 1 && gp50_native.block[GP50_DLY].param[1].value == 80);
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_LEFT, GP50_SCREEN_HOME) == 1 && gp50_native.block[GP50_DLY].param[1].value == 20);
    gp50_native.screen = GP50_SCREEN_HOME; gp50_native_ticks(1, 10);
    GP50_CHECK(gp50_native.home_title_custom && !strcmp(gp50_native.home_title, "Param 2 20"));
    gp50_native_ticks(201, 10);                                     /* 2 s later: preset name back */
    GP50_CHECK(!gp50_native.home_title_custom);
    /* Another effect in the block: consumed, "FS1 RE-ASSIGN". */
    gp50_native.block[GP50_DLY].model = 0x0b000099u;
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_LEFT, GP50_SCREEN_HOME) == 1);
    gp50_native_ticks(1, 10);
    GP50_CHECK(!strcmp(gp50_native.home_title, "FS1 RE-ASSIGN"));
    gp50_native.block[GP50_DLY].model = gp50_native.assignments.footswitch[0].model;
    /* Damaged data blocking FS2: consumed, "FS2 BAD DATA". */
    gp50_native.assignments.blocked = 2;
    GP50_CHECK(gp50_native_footswitch(GP50_FOOTSWITCH_RIGHT, GP50_SCREEN_HOME) == 1);
    gp50_native_ticks(1, 10);
    GP50_CHECK(!strcmp(gp50_native.home_title, "FS2 BAD DATA"));
    gp50_native.assignments.blocked = 0;
    /* Host read: 38 payload bytes, exact layout. */
    uint8_t r[38];
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 38 && r[0] == 1 && r[1] == 0 && r[2] == 2 && r[3] == 0 &&
               r[4] == 3 && r[5] == 1 && r[6] == GP50_DLY && r[7] == 1 && r[21] == 4 && r[22] == 0);
    /* Host set FS B: DLY param 2 between 10 and 90; bad values refused; clear. */
    uint8_t m[18] = {1, 4, GP50_DLY, 1, 0, 0};
    uint32_t model = gp50_native.block[GP50_DLY].model; float va = 10, vb = 90;
    memcpy(m + 6, &model, 4); memcpy(m + 10, &va, 4); memcpy(m + 14, &vb, 4);
    GP50_CHECK(gp50_native_host_set(m, 18) == 0 && gp50_native.assignments.footswitch[1].valid && gp50_native.assignments.footswitch[1].b == 90);
    float out_of_range = 150; memcpy(m + 14, &out_of_range, 4);
    GP50_CHECK(gp50_native_host_set(m, 18) == 1);
    m[5] = 7; memcpy(m + 14, &vb, 4);                               /* wrong preset */
    GP50_CHECK(gp50_native_host_set(m, 18) == 1);
    uint8_t clear[18] = {1, 4, 255, 0, 0, 0};
    GP50_CHECK(gp50_native_host_set(clear, 18) == 0 && !gp50_native.assignments.footswitch[1].valid);
    /* Recovery only with damaged data. */
    uint8_t recover[18] = {1, 255, 255, 0, 1, 0};
    GP50_CHECK(gp50_native_host_set(recover, 18) == 1);
    gp50_native.assignments.fault = 1;
    GP50_CHECK(gp50_native_host_set(m, 18) == 1);
    m[5] = 0; GP50_CHECK(gp50_native_host_set(m, 18) == 1);          /* sets refused while damaged */
    GP50_CHECK(gp50_native_host_set(recover, 18) == 0 && !gp50_native.assignments.fault && !gp50_native.assignments.footswitch[0].valid);
}
