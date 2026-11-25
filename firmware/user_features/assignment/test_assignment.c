#include <string.h>
#include "gp50_native.h"

#define ED GP50_SCREEN_EDITOR
#define HOME GP50_SCREEN_HOME
static uint32_t ev(uint32_t kind, uint32_t index, uint32_t screen, int32_t value) { return gp50_native_event(kind, index, screen, value); }
static uint32_t text(const char *s) { return gp50_native.editor_text_shown && strstr(gp50_native.editor_text, s) != 0; }

void gp50_test(void) {
    gp50_native.pedal_mode = GP50_MODE_STOMP;
    gp50_native.editor_block = GP50_AMP;
    gp50_native.editor_knob_param[0] = 2;                          /* knob 1 edits AMP parameter 3 on this page */
    /* Idle: editor inputs pass. */
    GP50_CHECK(ev(GP50_EVENT_KNOB, 0, ED, 1) == 0 && ev(GP50_EVENT_DRUM, 0, ED, 1) == 0 && ev(GP50_EVENT_PARA, 0, ED, 1) == 0);
    /* Assign AMP parameter 3 to Stomp knob 2 through the menu. */
    GP50_CHECK(ev(GP50_EVENT_DRUM_HOLD, 0, ED, 1) == 1 && text("> Assign control") && gp50_native.editor_text_kind == GP50_TEXT_PAGE);
    GP50_CHECK(ev(GP50_EVENT_PARA, 0, ED, 1) == 1 && text("Turn parameter knob") && gp50_native.editor_text_kind == GP50_TEXT_PROMPT);
    GP50_CHECK(ev(GP50_EVENT_KNOB, 0, ED, 1) == 1 && text("Selected; DRUM next"));
    GP50_CHECK(ev(GP50_EVENT_DRUM, 0, ED, 1) == 1 && text("Turn destination knob"));
    GP50_CHECK(ev(GP50_EVENT_KNOB, 1, ED, -1) == 1 && text("DRUM or EXIT assigns"));
    GP50_CHECK(ev(GP50_EVENT_BACK, 0, ED, 1) == GP50_PASS && !gp50_native.editor_text_shown);
    GP50_CHECK(gp50_native.assignments.knob[1].valid && gp50_native.assignments.knob[1].block == GP50_AMP &&
               gp50_native.assignments.knob[1].param == 2 && gp50_native.modified && gp50_native.notify_count == 1);   /* 12 71 notice */
    /* Home: knob 2 drives AMP parameter 3; its tile shows name, value and position. */
    float before = gp50_native.block[GP50_AMP].param[2].value;
    GP50_CHECK(ev(GP50_EVENT_KNOB, 1, HOME, 3) == 1 && gp50_native.block[GP50_AMP].param[2].value == before + 3);
    gp50_native_ticks(1, 10);
    GP50_CHECK(gp50_native.tile[1].custom && !strcmp(gp50_native.tile[1].name, "AMP Param 3") &&
               !strcmp(gp50_native.tile[1].value, "53") && gp50_native.tile[1].percent == 52);   /* truncation, as assign_percent */
    GP50_CHECK(ev(GP50_EVENT_KNOB, 0, HOME, 1) == 0);                /* unassigned knob 1: stock Master */
    /* Change to a preset without the binding: the tile goes back to stock on the next tick. */
    gp50_assignments saved = gp50_native.assignments;
    gp50_native.assignments.knob[1].valid = 0;                         /* what the platform restores for preset 5 */
    gp50_native_load(5); gp50_native.screen = HOME; gp50_native_ticks(1, 10);
    GP50_CHECK(!gp50_native.tile[1].custom);
    gp50_native.assignments = saved; gp50_native_load(0); gp50_native.screen = HOME; gp50_native_ticks(1, 10);
    GP50_CHECK(gp50_native.tile[1].custom);                            /* and back: assigned tile again */
    gp50_native.pedal_mode = GP50_MODE_PATCH;                         /* Patch mode: stock knobs, stock tiles */
    GP50_CHECK(ev(GP50_EVENT_KNOB, 1, HOME, 1) == 0);
    gp50_native_ticks(1, 10);
    GP50_CHECK(!gp50_native.tile[1].custom);
    gp50_native.pedal_mode = GP50_MODE_STOMP;
    /* Host: 12 71 lists it; 11 71 assigns knob 1 to DLY parameter 1, then clears it. */
    uint8_t r[25];
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 9 && r[0] == 1 && r[1] == 1 && r[2] == GP50_AMP && r[3] == 2);
    const uint8_t set_dly[4] = {0, GP50_DLY, 0, 0}, clear0[4] = {0, 0xff, 0, 0}, bad[4] = {3, GP50_DLY, 0, 0};
    uint32_t notices = gp50_native.notify_count;
    GP50_CHECK(gp50_native_host_set(set_dly, 4) == 0 && gp50_native.assignments.knob[0].valid && gp50_native.notify_count == notices + 1);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 17 && r[0] == 2);
    GP50_CHECK(gp50_native_host_set(clear0, 4) == 0 && !gp50_native.assignments.knob[0].valid);
    GP50_CHECK(gp50_native_host_set(bad, 4) == 1);
    /* Clear knob 2 through the menu. */
    GP50_CHECK(ev(GP50_EVENT_DRUM_HOLD, 0, ED, 1) == 1 && ev(GP50_EVENT_ENCODER, 0, ED, 1) == 1 && text("> Clear assignment"));
    GP50_CHECK(ev(GP50_EVENT_PARA, 0, ED, 1) == 1 && text("Turn Stomp knob"));
    GP50_CHECK(ev(GP50_EVENT_KNOB, 1, ED, 1) == 1 && text("Stomp knob 2") && text("AMP: Param 3"));
    GP50_CHECK(ev(GP50_EVENT_PARA, 0, ED, 1) == 1 && text("Assignment cleared") && !gp50_native.assignments.knob[1].valid);
    GP50_CHECK(ev(GP50_EVENT_BACK, 0, ED, 1) == 1 && !gp50_native.editor_text_shown);
    /* Footswitch A/B: value A = current, set B with the knob, press the same footswitch again. */
    gp50_native.block[GP50_AMP].param[2].value = 50;
    ev(GP50_EVENT_DRUM_HOLD, 0, ED, 1); ev(GP50_EVENT_PARA, 0, ED, 1); ev(GP50_EVENT_KNOB, 0, ED, 1);
    GP50_CHECK(ev(GP50_EVENT_FOOTSWITCH, GP50_FOOTSWITCH_LEFT, ED, 1) == 1 && text("Set B, FS1 again"));
    GP50_CHECK(ev(GP50_EVENT_KNOB, 0, ED, 1) == 0);                   /* knobs set B: passes to the editor */
    gp50_native.block[GP50_AMP].param[2].value = 80;
    GP50_CHECK(ev(GP50_EVENT_FOOTSWITCH, GP50_FOOTSWITCH_RIGHT, ED, 1) == 1 && text("Set B, FS1 again"));   /* other switch: ignored */
    GP50_CHECK(ev(GP50_EVENT_FOOTSWITCH, GP50_FOOTSWITCH_LEFT, ED, 1) == 1 && text("Assigned") && !text("SAVE preset"));
    GP50_CHECK(gp50_native.assignments.footswitch[0].valid && gp50_native.assignments.footswitch[0].a == 50 &&
               gp50_native.assignments.footswitch[0].b == 80);
    ev(GP50_EVENT_BACK, 0, ED, 1);
    /* Binary Freeze-style parameter: bind immediately, preserve current audio
     * value, support either starting state and arbitrary two-endpoint ranges. */
    for (unsigned j = 0; j < 4; j++) {
        gp50_native_param *v = &gp50_native.block[GP50_AMP].param[2];
        v->min = j < 2 ? 0 : -2; v->max = j < 2 ? 1 : 2;
        v->step = v->max - v->min; v->value = j & 1 ? v->max : v->min;
        float current = v->value;
        ev(GP50_EVENT_DRUM_HOLD, 0, ED, 1); ev(GP50_EVENT_PARA, 0, ED, 1); ev(GP50_EVENT_KNOB, 0, ED, 1);
        unsigned fs = j & 1;
        GP50_CHECK(ev(GP50_EVENT_FOOTSWITCH, fs, ED, 1) == 1 && text("Assigned") && !text("SAVE preset"));
        GP50_CHECK(gp50_native.assignments.footswitch[fs].a == current &&
                   gp50_native.assignments.footswitch[fs].b == (current == v->min ? v->max : v->min));
        GP50_CHECK(v->value == current);
        ev(GP50_EVENT_BACK, 0, ED, 1);
    }
    /* Damaged data: menu offers Clear all; host and assign refused; recovery clears everything. */
    gp50_native.assignments.fault = 1;
    GP50_CHECK(gp50_native_host_set(set_dly, 4) == 1);
    ev(GP50_EVENT_DRUM_HOLD, 0, ED, 1);
    GP50_CHECK(text("Clear all (bad data)"));
    ev(GP50_EVENT_ENCODER, 0, ED, 1); ev(GP50_EVENT_ENCODER, 0, ED, 1);
    GP50_CHECK(text("> Clear all"));
    GP50_CHECK(ev(GP50_EVENT_PARA, 0, ED, 1) == 1 && text("Clear ALL assignments?"));
    GP50_CHECK(ev(GP50_EVENT_PARA, 0, ED, 1) == 1 && text("Assignment cleared") && !gp50_native.assignments.fault &&
               !gp50_native.assignments.footswitch[0].valid);
    /* Leaving the editor or loading a preset cancels any flow. */
    ev(GP50_EVENT_DRUM_HOLD, 0, ED, 1);
    gp50_native_load(4);
    GP50_CHECK(ev(GP50_EVENT_PARA, 0, ED, 1) == 0);
}
