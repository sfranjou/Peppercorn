/* Native: Para EQ designs vs a double-precision RBJ reference (error beyond float32's own rounding
 * of the exact design < 0.04 dB, absolute < 0.06 dB; worst at 20 Hz under low shelves, see below) (magnitude response, 24 points per
 * band setting over 20 Hz..20 kHz), cell layout (a0 = 1, flag last, states cleared at init). */
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define COPRO_CELL_ENABLE 0xf9cu
#define COPRO_CELL_BAND0 0xf9du
#define COPRO_CELL_LEVEL_TARGET 0xfcfu
#define COPRO_CELL_LEVEL 0xfd0u
#define COPRO_CELLS_H
static float cells[0x1000];
#define GP50_EQ_CELL(i) ((volatile float *)&cells[(i)])
#define GP50_NATIVE_TEST
#include "para_eq.c"
typedef struct { double b0, b1, b2, a0, a1, a2; } ref;
static ref rbj(int type, double f, double db, double q) {
 double w = 2 * M_PI * f / 44100, s = sin(w), c = cos(w), A = pow(10, db / 40), al = type == 1 ? s / (2 * q) : s / 2 * sqrt(2.0), sq = 2 * sqrt(A) * al;
 if (type == 1) return (ref){1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A};
 if (type == 0) return (ref){A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq), (A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq};
 return (ref){A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq), (A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq};
}
static double mag_db(double b0, double b1, double b2, double a0, double a1, double a2, double f) {
 double w = 2 * M_PI * f / 44100, cr = cos(w), ci = -sin(w), c2r = cos(2 * w), c2i = -sin(2 * w);
 double nr = b0 + b1 * cr + b2 * c2r, ni = b1 * ci + b2 * c2i, dr = a0 + a1 * cr + a2 * c2r, di = a1 * ci + a2 * c2i;
 return 10 * log10((nr * nr + ni * ni) / (dr * dr + di * di));
}
int main(void) {
 double worst = 0, worst_abs = 0;   /* worst: error beyond float32's own rounding error */
 float p[8] = {40, 0, 50, 0, 40, 50, 0, 50};
 uint8_t on = 1;
 for (int trial = 0; trial < 400; trial++) {
  for (int i = 0; i < 8; i++) p[i] = (i == 1 || i == 3 || i == 6) ? (float)((trial * 37 + i * 11) % 101 - 50) : (float)((trial * 53 + i * 29) % 101);
  para_eq_init(p);
  assert(*(uint32_t *)&cells[COPRO_CELL_ENABLE] == 0);
  float level = cells[COPRO_CELL_LEVEL];
  assert(level == cells[COPRO_CELL_LEVEL_TARGET] && fabsf(level - p[7] * 0.02f) < 1e-6f);
  for (int k = 0; k < 5; k++) { float *c = &cells[COPRO_CELL_BAND0 + 10 * k]; assert(c[0] == GP50_EQ_INV_K && c[1] == 0 && c[2] == 0 && c[3] == 1 && c[4] == 0 && c[5] == 0 && !c[6] && !c[7] && !c[8] && !c[9]); }
  float buf[128] = {0};
  para_eq_process(buf, 64, p, 0, &on, 0, 0);
  assert(*(uint32_t *)&cells[COPRO_CELL_ENABLE] == 1);
  double fk[3] = {40 * pow(10, p[0] / 100.0), 200 * pow(25, p[2] / 100.0), 1500 * pow(8, p[5] / 100.0)};
  double dbk[3] = {p[1] * 0.24, p[3] * 0.24, p[6] * 0.24}, q = 0.3 * pow(20, p[4] / 100.0);
  for (int k = 0; k < 3; k++) {
   float *c = &cells[COPRO_CELL_BAND0 + 10 * k]; assert(c[3] == 1.0f);
   ref r = rbj(k == 0 ? 0 : k == 1 ? 1 : 2, fk[k], dbk[k], q);
   for (int j = 0; j < 24; j++) {
    double f = 20 * pow(1000, j / 23.0) * 0.999;
    double want = mag_db(r.b0, r.b1, r.b2, r.a0, r.a1, r.a2, f);
    /* Hardware response of the stored numbers: y = k (B x - A y), k = rsqrt(1.0)^2 measured on the
     * pedal (0x3f7fffb7 squared, float32) - a fixed constant here, independent of the header. */
    const double K = 0.9999912977218628;
    double e = fabs(mag_db(K * c[0], K * c[1], K * c[2], 1, K * c[4], K * c[5], f) - want);
    /* float32 itself: the exact design rounded to float32 (the coprocessor computes in float32) */
    double e32 = fabs(mag_db((float)(r.b0 / r.a0), (float)(r.b1 / r.a0), (float)(r.b2 / r.a0), 1, (float)(r.a1 / r.a0), (float)(r.a2 / r.a0), f) - want);
    if (e - e32 > worst) worst = e - e32;
    if (e > worst_abs) worst_abs = e;
   }
  }
  /* a knob change redesigns only its band: states untouched */
  cells[COPRO_CELL_BAND0 + 6] = 0.5f; cells[COPRO_CELL_BAND0 + 10 + 6] = 0.25f;
  p[3] = p[3] > 0 ? p[3] - 10 : p[3] + 10;
  para_eq_process(buf, 64, p, 0, &on, 0, 0);
  assert(cells[COPRO_CELL_BAND0 + 6] == 0.5f && cells[COPRO_CELL_BAND0 + 10 + 6] == 0.25f);
  on = 0; para_eq_process(buf, 64, p, 0, &on, 0, 0); assert(*(uint32_t *)&cells[COPRO_CELL_ENABLE] == 0); on = 1;
 }
 printf("para eq: worst magnitude error %.5f dB (%.5f dB beyond float32 rounding) over 400 settings x 3 bands x 24 frequencies\n", worst_abs, worst);
 /* Worst cases are 20 Hz under a 40-60 Hz low shelf: DC gain depends on 1+a1+a2 ~ 1e-4, so a few
  * float32 ulps in a1/a2 move it by 0.01-0.03 dB in any float32 design (conditioning, not approximation). */
 assert(worst < 0.04 && worst_abs < 0.06);
 return 0;
}
