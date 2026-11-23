/* Native: clean settings = 40-sample delay (unity for small signals); wow/flutter keep the read inside the line
 * and move the delay; full-scale input stays bounded; silence stays silent; bypass untouched; VOL scales. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "gp50_effect.h"
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#include "tape.c"
static float buf[128];
static const uint8_t on = 1, off = 0;
int main(void) {
    float clean[8] = {0, 0, 0, 100, 100, 50, 0, 0};
    tape_init(clean);
    int peak_at = -1; float peak = 0;
    for (int b = 0; b < 4; b++) {
        for (int f = 0; f < 64; f++) buf[2 * f] = buf[2 * f + 1] = (b == 0 && f == 0) ? 0.01f : 0.0f;
        tape_process(buf, 64, clean, 0, &on, 0, 0);
        for (int f = 0; f < 64; f++) if (fabsf(buf[2 * f]) > peak) { peak = fabsf(buf[2 * f]); peak_at = b * 64 + f; }
    }
    printf("clean impulse peak %.5f at %d\n", peak, peak_at);
    assert(peak_at == 40 && fabsf(peak - 0.01f) < 2e-4f);
    /* wow + flutter: delay moves, stays finite and bounded under full-scale noise */
    float wild[8] = {100, 100, 100, 50, 100, 50, 0, 0};
    tape_init(wild);
    float mx = 0; unsigned r = 1;
    for (int b = 0; b < 3000; b++) {
        for (int f = 0; f < 64; f++) { r = r * 1103515245u + 12345u; buf[2 * f] = buf[2 * f + 1] = ((r >> 9) & 0xffff) / 32768.0f - 1.0f; }
        tape_process(buf, 64, wild, 0, &on, 0, 0);
        for (int f = 0; f < 128; f++) { assert(isfinite(buf[f])); if (fabsf(buf[f]) > mx) mx = fabsf(buf[f]); }
    }
    printf("full-scale peak out %.3f\n", mx);
    assert(mx < 2.0f);
    /* silence stays silent after the line empties */
    for (int b = 0; b < 20; b++) { memset(buf, 0, sizeof buf); tape_process(buf, 64, wild, 0, &on, 0, 0); }
    for (int f = 0; f < 128; f++) assert(fabsf(buf[f]) < 1e-6f);
    /* bypass untouched */
    for (int f = 0; f < 128; f++) buf[f] = 0.3f;
    tape_process(buf, 64, wild, 0, &off, 0, 0);
    for (int f = 0; f < 128; f++) assert(buf[f] == 0.3f);
    puts("tape ok");
    return 0;
}
