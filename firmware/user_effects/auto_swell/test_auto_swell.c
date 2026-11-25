/* Native: a pick after silence starts at 0 gain and reaches full level after Attack;
 * a held note stays at full level; a new pick after a dip retriggers; bypass is untouched. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "gp50_effect.h"
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#include "auto_swell.c"
static float buf[128];
static const uint8_t on = 1, off = 0;
static float block(float amp, const float *p, const uint8_t *en) {
    for (int f = 0; f < 64; f++) buf[2 * f] = buf[2 * f + 1] = (f & 1) ? amp : -amp;
    auto_swell_process(buf, 64, p, 0, en, 0, 0);
    float m = 0; for (int f = 0; f < 64; f++) if (fabsf(buf[2 * f]) > m) m = fabsf(buf[2 * f]);
    return m;
}
int main(void) {
    float p[8] = {100, 50, 0, 50, 0, 0, 0, 0};   /* 100 ms linear, unity */
    auto_swell_init(p);
    for (int b = 0; b < 50; b++) assert(block(0.0f, p, &on) == 0.0f);   /* silence stays silent */
    float first = block(0.5f, p, &on);
    assert(first < 0.05f);                                                 /* starts near zero */
    int blocks = 1; float m = first;
    while (m < 0.499f && blocks < 200) { m = block(0.5f, p, &on); blocks++; }
    printf("full after %d blocks (%.1f ms)\n", blocks, blocks * 64 / 44.1);
    assert(blocks >= 66 && blocks <= 72);                                  /* ~100 ms = 69 blocks */
    for (int b = 0; b < 100; b++) assert(block(0.5f, p, &on) > 0.499f);    /* held note stays full */
    for (int b = 0; b < 700; b++) block(0.0f, p, &on);                     /* silence: re-arm */
    assert(block(0.5f, p, &on) < 0.05f);                                   /* new pick retriggers */
    /* A decaying note must cross the old Sens-dependent release level without
     * losing sustain. Cover sensitive and insensitive onset settings. */
    for (int sensitivity = 0; sensitivity <= 100; sensitivity += 50) {
        p[1] = (float)sensitivity; auto_swell_init(p);
        for (int b = 0; b < 180; b++) block(0.5f, p, &on);
        for (int b = 0; b < 2200; b++) {
            const float amp = 0.5f * expf(-b * (64.0f / 44100.0f) / 0.45f);
            const float out = block(amp, p, &on);
            assert(fabsf(out / amp - 1.0f) < 1e-5f);
        }
        for (int b = 0; b < 500; b++) block(0.0f, p, &on);
        assert(block(0.5f, p, &on) < 0.05f);
    }
    /* Reattack over a tail well above the released silence gate. */
    p[1] = 50;
    auto_swell_init(p);
    for (int b = 0; b < 200; b++) block(0.5f, p, &on);
    for (int b = 0; b < 100; b++) assert(fabsf(block(0.015f, p, &on) - 0.015f) < 1e-5f);
    assert(block(0.2f, p, &on) < 0.01f);
    /* Quieter input now triggers at medium Sens, but not at minimum Sens. */
    const float quiet_pick = 0.010f;
    auto_swell_init(p);
    for (int b = 0; b < 100; b++) m = block(quiet_pick, p, &on);
    assert(fabsf(m - quiet_pick) < 1e-5f);
    p[1] = 0;
    auto_swell_init(p);
    for (int b = 0; b < 100; b++) assert(block(quiet_pick, p, &on) == 0.0f);
    /* Asymmetric bypass is bit for bit unchanged; switching back rearms. */
    for (int b = 0; b < 100; b++) block(0.5f, p, &on);
    float dry[128];
    for (int f = 0; f < 128; f++) dry[f] = buf[f] = f & 1 ? 0.3f : -0.25f;
    auto_swell_process(buf, 64, p, 0, &off, 0, 0);
    assert(memcmp(dry, buf, sizeof dry) == 0);
    assert(block(0.5f, p, &on) < 0.05f);
    /* VOL 100 doubles */
    float q[8] = {10, 50, 0, 100, 0, 0, 0, 0};
    auto_swell_init(q);
    for (int b = 0; b < 50; b++) m = block(0.25f, q, &on);
    assert(fabsf(m - 0.5f) < 1e-4f);
    puts("auto_swell ok");
    return 0;
}
