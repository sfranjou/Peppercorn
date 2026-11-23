#ifndef GP_CAPTURE_SPLINE_H
#define GP_CAPTURE_SPLINE_H
#include <stddef.h>
#include <stdint.h>
/* Portable binary32 reference of the GPTS v1 two-spline capture (sdk/tone_core/spline_record.py has the
 * evaluation contract). Causal mono, 44100 Hz. Tap zero is newest. Compile without FMA contraction. */
#define SPLINE_PRE 32u
#define SPLINE_INTER 16u
#define SPLINE_POST 256u
#define SPLINE_LPF 40u
#define SPLINE_KNOTS 33u
typedef struct {
 float pre[SPLINE_PRE], inter[SPLINE_INTER], v[2][SPLINE_KNOTS], post[SPLINE_POST];
 float lpf[SPLINE_LPF], biquad[5], input_gain, output_gain;
} spline_model;
typedef struct {
 const spline_model *model;
 float a[2][SPLINE_KNOTS - 1], b[2][SPLINE_KNOTS - 1];
 float pre[SPLINE_PRE], inter[SPLINE_INTER], post[SPLINE_POST], lpf[SPLINE_LPF], previous, x1, x2, y1, y2;
 uint32_t pre_pos, inter_pos, post_pos, lpf_pos;
} spline_state;
/* Builds the per-segment line coefficients exactly as the pedal's ARM init. Returns -1 on a non-finite model. */
int spline_init(spline_state *state, const spline_model *model);
float spline_eval(const float *a, const float *b, float z);
void spline_process(spline_state *state, const float *in, float *out, size_t n);
#endif
