/* Native: impulse gives a decaying tail whose RT60 tracks Decay; freeze holds the tail while new input is ignored;
 * unfreeze decays again; silence in -> silence; full-scale noise stays finite/bounded; bypass untouched. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "gp50_effect.h"
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#include "fdn_verb.c"
static float buf[128];
static const uint8_t on = 1, off = 0;
static float run(float *p, float in, int blocks) {   /* returns RMS of the last block */
    float rms = 0;
    for (int b = 0; b < blocks; b++) {
        for (int f = 0; f < 64; f++) buf[2 * f] = buf[2 * f + 1] = in;
        fdn_verb_process(buf, 64, p, 0, &on, 0, 0);
        rms = 0; for (int f = 0; f < 64; f++) { assert(isfinite(buf[2 * f])); rms += buf[2 * f] * buf[2 * f]; }
        rms = sqrtf(rms / 64);
    }
    return rms;
}
static float window(float *p, float in, int blocks) {  /* RMS over many blocks */
    double e = 0;
    for (int b = 0; b < blocks; b++) { float r = run(p, in, 1); e += (double)r * r; }
    return (float)sqrt(e / blocks);
}
static float tail_after(float decay, float seconds) {
    static float s[sizeof state]; (void)s;
    memset(&state, 0, sizeof state);
    float p[8] = {100, decay, 70, 0, 0, 0, 50, 0};
    fdn_verb_init(p);
    for (int b = 0; b < 4; b++) {               /* 256-sample burst of noise */
        for (int f = 0; f < 64; f++) buf[2 * f] = buf[2 * f + 1] = ((f * 7919 + b * 31) % 200 - 100) / 200.0f;
        fdn_verb_process(buf, 64, p, 0, &on, 0, 0);
    }
    float early = run(p, 0, 20);
    float late = run(p, 0, (int)(seconds * 44100 / 64));
    return 20.0f * log10f(late / early + 1e-12f);
}
int main(void) {
    float short_db = tail_after(10, 0.5f), long_db = tail_after(80, 0.5f);
    printf("after 0.5 s: decay 10 -> %.1f dB, decay 80 -> %.1f dB\n", short_db, long_db);
    assert(short_db < long_db - 10.0f);         /* longer decay keeps more energy */
    assert(short_db < -20.0f);
    /* freeze: tail holds, new input ignored */
    memset(&state, 0, sizeof state);
    float p[8] = {100, 50, 70, 30, 0, 0, 50, 0};
    fdn_verb_init(p);
    run(p, 0.3f, 10); run(p, 0, 5);
    p[5] = 1;
    run(p, 0, 50);                                            /* let the freeze settle */
    float held1 = window(p, 0, 200), held2 = window(p, 0.0f, 200);   /* two ~0.3 s windows */
    printf("frozen rms %.4f -> %.4f\n", held1, held2);
    assert(held2 > held1 * 0.7f && held2 < held1 * 1.3f);
    float with_input = window(p, 0.5f, 100);                 /* input ignored while frozen */
    assert(with_input < held1 * 1.3f);
    p[5] = 0;
    run(p, 0, 700);
    float released = window(p, 0, 50);                        /* decays again */
    printf("after unfreeze %.5f\n", released);
    assert(released < held2 * 0.3f);
    /* A causal 2x linear reconstruction must put each odd sample halfway
     * between its adjacent even samples, including the 64-frame boundary. */
    memset(&state, 0, sizeof state); fdn_verb_init(p);
    p[0]=100; p[6]=50;
    run(p, 0.3f, 50);
    float rendered[192];
    for (unsigned b=0;b<3;b++) {
        run(p, 0, 1);
        for(unsigned f=0;f<64;f++)rendered[b*64+f]=buf[2*f];
    }
    for(unsigned f=1;f+1<192;f+=2)
        assert(fabsf(rendered[f]-(rendered[f-1]+rendered[f+1])*0.5f)<1e-6f);
    /* silence in -> silence out from a clean start */
    memset(&state, 0, sizeof state); fdn_verb_init(p);
    assert(run(p, 0, 100) == 0.0f);
    /* full-scale noise stays bounded */
    unsigned r = 1; float mx = 0;
    for (int b = 0; b < 2000; b++) {
        for (int f = 0; f < 64; f++) { r = r * 1103515245u + 12345u; buf[2 * f] = buf[2 * f + 1] = ((r >> 9) & 0xffff) / 32768.0f - 1.0f; }
        p[1] = 100; fdn_verb_process(buf, 64, p, 0, &on, 0, 0);
        for (int f = 0; f < 128; f++) { assert(isfinite(buf[f])); if (fabsf(buf[f]) > mx) mx = fabsf(buf[f]); }
    }
    printf("full-scale peak %.2f\n", mx);
    assert(mx < 6.0f);
    for (int f = 0; f < 128; f++) buf[f] = 0.3f;
    fdn_verb_process(buf, 64, p, 0, &off, 0, 0);
    for (int f = 0; f < 128; f++) assert(buf[f] == 0.3f);
    printf("state %zu bytes\n", sizeof state);
    puts("fdn_verb ok");
    return 0;
}
