#include <stdint.h>

#define PITCH_VOICES 2
#define WET_SLOT 3
#define PITCH_INIT pitch_splice_init
#define PITCH_PROCESS pitch_splice_process

/* Precomputed 1 - 2^(shift / 12) for integer control settings. */
static const float slopes[] = {
    7.5000000000e-01f, 7.3513422641e-01f, 7.1938448792e-01f, 7.0269822125e-01f,
    6.8501973753e-01f, 6.6629003646e-01f, 6.4644660941e-01f, 6.2542323078e-01f,
    6.0314973701e-01f, 5.7955179237e-01f, 5.5455064093e-01f, 5.2806284366e-01f,
    5.0000000000e-01f, 4.7026845282e-01f, 4.3876897585e-01f, 4.0539644250e-01f,
    3.7003947505e-01f, 3.3258007291e-01f, 2.9289321881e-01f, 2.5084646156e-01f,
    2.0629947402e-01f, 1.5910358475e-01f, 1.0910128186e-01f, 5.6125687318e-02f,
    0.0000000000e+00f, -5.9463094359e-02f, -1.2246204831e-01f, -1.8920711500e-01f,
    -2.5992104989e-01f, -3.3483985417e-01f, -4.1421356237e-01f, -4.9830707688e-01f,
    -5.8740105197e-01f, -6.8179283051e-01f, -7.8179743628e-01f, -8.8774862536e-01f,
    -1.0000000000e+00f, -1.1189261887e+00f, -1.2449240966e+00f, -1.3784142300e+00f,
    -1.5198420998e+00f, -1.6696797083e+00f, -1.8284271247e+00f, -1.9966141538e+00f,
    -2.1748021039e+00f, -2.3635856610e+00f, -2.5635948726e+00f, -2.7754972507e+00f,
    -3.0000000000e+00f,
};

static float requested_slope(const float *params, uint32_t voice) {
    const float setting = params[voice];
    if (!(setting >= -24.0f && setting <= 24.0f)) return 0.0f;
    return slopes[(int32_t)setting + 24];
}

#include "pitch_splice.c"
