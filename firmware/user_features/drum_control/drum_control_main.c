/* Drum control from a computer (the MOD096 `11/12 75` command, moved onto the SDK; wire format unchanged):
 *   12 75            -> 12 75 01 playing drum_screen_open
 *   11 75 01 p w     p: 0 stop / 1 play; w: 1 open the drum screen, 0 close it (only if open), 255 leave navigation
 * No toggle operation: a retried command never inverts playback twice.
 * On the pedal (MOD096): home screen DRUM toggles playback, DRUM held opens the drum screen. */
#include "gp50.h"

uint32_t drum_control_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    if (capacity < 3) return 0;
    out[0] = 1; out[1] = (uint8_t)gp50_drum_playing(); out[2] = gp50_screen() == GP50_SCREEN_DRUM;
    return 3;
}

uint32_t drum_control_set(const gp50_ctx *ctx, const uint8_t *in, uint32_t n) {
    (void)ctx;
    if (n != 3 || in[0] != 1 || in[1] > 1 || (in[2] != 0 && in[2] != 1 && in[2] != 255)) return GP50_REFUSED;
    gp50_drum_set_playing(in[1]);
    if (in[2] == 1) (void)gp50_screen_open(GP50_SCREEN_DRUM);
    else if (in[2] == 0 && gp50_screen() == GP50_SCREEN_DRUM) (void)gp50_screen_open(GP50_SCREEN_HOME);
    return GP50_OK;
}

uint32_t drum_control_event(const gp50_ctx *ctx, const gp50_event *e) {
    (void)ctx;
    if (e->screen != GP50_SCREEN_HOME) return GP50_PASS;
    if (e->kind == GP50_EVENT_DRUM) { gp50_drum_set_playing(!gp50_drum_playing()); return GP50_CONSUMED; }
    if (e->kind == GP50_EVENT_DRUM_HOLD) { (void)gp50_screen_open(GP50_SCREEN_DRUM); return GP50_CONSUMED; }
    return GP50_PASS;
}
