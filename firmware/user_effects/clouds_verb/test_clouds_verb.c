/* Native: tail RAM mapped to a host array filled with garbage; output stays dry until the RAM is cleared, then an
 * impulse gives a decaying tail (longer with Decay); freeze holds; only the declared region is touched;
 * full-scale noise stays finite; bypass untouched (but clearing continues). */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static int16_t tail[83264];
static uintptr_t map(uint32_t a) { assert(a >= 0x290d7580u && a < 0x290d7580u + 2u * 83264u); return (uintptr_t)tail + (a - 0x290d7580u); }
#define GP50_TAIL_PTR(a) map((uint32_t)(a))
#include "gp50_effect.h"
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#define GP50_NATIVE_TEST
#include "clouds_verb.c"
static float buf[128];
static const uint8_t on = 1, off = 0;
static float block(float *p, float in) {
    for (int f = 0; f < 64; f++) buf[2 * f] = buf[2 * f + 1] = in;
    clouds_verb_process(buf, 64, p, 0, &on, 0, 0);
    float e = 0; for (int f = 0; f < 64; f++) { assert(isfinite(buf[2 * f])); e += buf[2 * f] * buf[2 * f]; }
    return sqrtf(e / 64);
}
static float window(float *p, float in, int n) { double e = 0; for (int b = 0; b < n; b++) { float r = block(p, in); e += (double)r * r; } return (float)sqrt(e / n); }
static float decay_db(float decay) {
    memset(&state, 0, sizeof state);
    for (int i = 0; i < 83264; i++) tail[i] = (int16_t)(i * 7919);
    float p[8] = {100, decay, 62, 30, 0, 50, 0, 0};
    clouds_verb_init(p);
    for (int b = 0; b < 40; b++) assert(block(p, 0) == 0.0f);   /* clearing: dry only, garbage never heard */
    assert(state.cleared == TAIL_CELLS);
    for (int b = 0; b < 4; b++) block(p, 0.3f);
    float early = window(p, 0, 20), late = (window(p, 0, 340), window(p, 0, 20));
    return 20.0f * log10f(late / early + 1e-12f);
}
int main(void) {
    float s = decay_db(10), l = decay_db(90);
    printf("~0.5 s later: decay 10 -> %.1f dB, decay 90 -> %.1f dB\n", s, l);
    assert(s < l - 5.0f && s < -6.0f);   /* long tank (~0.44 s loop): one round trip in 0.5 s */
    for (int i = TAIL_CELLS; i < 83264; i++) assert(tail[i] == (int16_t)(i * 7919));   /* rest of the region untouched */
    /* freeze */
    float p[8] = {100, 60, 62, 30, 0, 50, 0, 0};
    block(p, 0.3f); block(p, 0.3f); window(p, 0, 10);
    p[4] = 1; window(p, 0, 50);
    float h1 = window(p, 0, 200), h2 = window(p, 0, 200);
    printf("frozen %.4f -> %.4f\n", h1, h2);
    assert(h2 > h1 * 0.7f && h2 < h1 * 1.3f);
    /* full-scale noise bounded */
    unsigned r = 1; float mx = 0; p[4] = 0; p[1] = 100;
    for (int b = 0; b < 2000; b++) {
        for (int f = 0; f < 64; f++) { r = r * 1103515245u + 12345u; buf[2 * f] = buf[2 * f + 1] = ((r >> 9) & 0xffff) / 32768.0f - 1.0f; }
        clouds_verb_process(buf, 64, p, 0, &on, 0, 0);
        for (int f = 0; f < 128; f++) { assert(isfinite(buf[f])); if (fabsf(buf[f]) > mx) mx = fabsf(buf[f]); }
    }
    printf("full-scale peak %.2f, slot state %zu bytes\n", mx, sizeof state);
    assert(mx < 6.0f);
    for (int f = 0; f < 128; f++) buf[f] = 0.3f;
    clouds_verb_process(buf, 64, p, 0, &off, 0, 0);
    for (int f = 0; f < 128; f++) assert(buf[f] == 0.3f);
    puts("clouds_verb ok");
    return 0;
}
