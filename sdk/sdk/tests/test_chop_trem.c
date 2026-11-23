/* Standalone author smoke test. Run with the command in sdk/README.md. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "gp50_effect.h"
/* Native hosts do not use the firmware ELF section names. */
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#include "chop_trem.c"

static void fill(float *samples) {
    for (unsigned i = 0; i < GP50_BLOCK_FRAMES; ++i) {
        samples[2*i] = i & 1 ? -0.25f : 0.25f;
        samples[2*i+1] = 0.75f;
    }
}

int main(void) {
    float samples[2*GP50_BLOCK_FRAMES], original[2*GP50_BLOCK_FRAMES];
    float reference[2*GP50_BLOCK_FRAMES];
    float params[8] = {0.0f, 10.0f, 50.0f};
    uint8_t enabled = 1;
    uint32_t beat = 500;
    fill(samples);
    memcpy(original, samples, sizeof samples);
    chop_trem_init(params);
    chop_trem_process(samples, GP50_BLOCK_FRAMES, params, 0, &enabled, &beat, NULL);
    for (unsigned i = 0; i < GP50_BLOCK_FRAMES; ++i) {
        assert(samples[2*i] == original[2*i]); /* zero depth, unity volume */
        assert(samples[2*i+1] == samples[2*i]); /* documented mono output */
    }

    params[0] = 100.0f;
    chop_trem_init(params);
    fill(reference);
    chop_trem_process(reference, GP50_BLOCK_FRAMES, params, 0, &enabled, &beat, NULL);
    chop_trem_init(params);
    fill(samples);
    enabled = 0;
    chop_trem_process(samples, GP50_BLOCK_FRAMES, params, 0, &enabled, &beat, NULL);
    assert(memcmp(samples, original, sizeof samples) == 0); /* bypass is untouched */
    enabled = 1;
    chop_trem_process(samples, GP50_BLOCK_FRAMES, params, 0, &enabled, &beat, NULL);
    assert(memcmp(samples, reference, sizeof samples) == 0); /* bypass did not advance */

    float minimum = 1.0f, maximum = 0.0f;
    chop_trem_init(params);
    for (unsigned block = 0; block < 110; ++block) {
        fill(samples);
        chop_trem_process(samples, GP50_BLOCK_FRAMES, params, 0, &enabled, &beat, NULL);
        for (unsigned i = 0; i < GP50_BLOCK_FRAMES; ++i) {
            const float magnitude = fabsf(samples[2*i]);
            assert(isfinite(magnitude) && magnitude <= 0.250001f);
            assert(samples[2*i] * original[2*i] >= 0.0f);
            assert(samples[2*i+1] == samples[2*i]);
            if (magnitude < minimum) minimum = magnitude;
            if (magnitude > maximum) maximum = magnitude;
        }
    }
    assert(minimum < 0.005f && maximum > 0.24f); /* audible chop, valid gain */
    params[2] = 0.0f;
    fill(samples);
    chop_trem_process(samples, GP50_BLOCK_FRAMES, params, 0, &enabled, &beat, NULL);
    for (unsigned i = 0; i < 2*GP50_BLOCK_FRAMES; ++i) assert(samples[i] == 0.0f);
    puts("PASS: unity, mono, bypass, state continuity, bounded chop, mute");
    return 0;
}
