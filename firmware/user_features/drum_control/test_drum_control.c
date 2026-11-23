#include "gp50_native.h"

void gp50_test(void) {
    uint8_t r[3];
    gp50_native.screen = GP50_SCREEN_HOME;
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 3 && r[0] == 1 && r[1] == 0 && r[2] == 0);
    const uint8_t play_open[3] = {1, 1, 1}, stop_keep[3] = {1, 0, 255}, close[3] = {1, 1, 0};
    GP50_CHECK(gp50_native_host_set(play_open, 3) == 0 && gp50_native.drum_playing && gp50_native.screen == GP50_SCREEN_DRUM);
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 3 && r[1] == 1 && r[2] == 1);
    GP50_CHECK(gp50_native_host_set(play_open, 3) == 0 && gp50_native.drum_playing);   /* retry: no inversion */
    GP50_CHECK(gp50_native_host_set(stop_keep, 3) == 0 && !gp50_native.drum_playing && gp50_native.screen == GP50_SCREEN_DRUM);
    GP50_CHECK(gp50_native_host_set(close, 3) == 0 && gp50_native.screen == GP50_SCREEN_HOME);
    gp50_native.screen = GP50_SCREEN_EDITOR;                       /* close only closes an open drum screen */
    GP50_CHECK(gp50_native_host_set(close, 3) == 0 && gp50_native.screen == GP50_SCREEN_EDITOR);
    /* Home DRUM toggles playback, DRUM held opens the drum screen; the editor keeps its own DRUM. */
    gp50_native.drum_playing = 0;
    GP50_CHECK(gp50_native_event(GP50_EVENT_DRUM, 0, GP50_SCREEN_HOME, 1) == 1 && gp50_native.drum_playing);
    GP50_CHECK(gp50_native_event(GP50_EVENT_DRUM, 0, GP50_SCREEN_HOME, 1) == 1 && !gp50_native.drum_playing);
    GP50_CHECK(gp50_native_event(GP50_EVENT_DRUM_HOLD, 0, GP50_SCREEN_HOME, 1) == 1 && gp50_native.screen == GP50_SCREEN_DRUM);
    GP50_CHECK(gp50_native_event(GP50_EVENT_DRUM, 0, GP50_SCREEN_EDITOR, 1) == 0);
    const uint8_t bad1[3] = {2, 1, 1}, bad2[3] = {1, 2, 1}, bad3[3] = {1, 1, 7};
    GP50_CHECK(gp50_native_host_set(bad1, 3) == 1 && gp50_native_host_set(bad2, 3) == 1 && gp50_native_host_set(bad3, 3) == 1);
}
