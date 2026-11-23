#include "capture_spline.h"
#include "spline_tables.h"
#include <float.h>
#include <string.h>
static const uint32_t knot_bits[SPLINE_KNOTS] = GPTS_KNOT_BITS, inv_bits[SPLINE_KNOTS - 1] = GPTS_INV_DK_BITS;
static float f(uint32_t u) { float x; memcpy(&x, &u, 4); return x; }
static int finite_array(const float *x, unsigned n) {
 unsigned i; for (i = 0; i < n; i++) if (!(x[i] <= FLT_MAX && x[i] >= -FLT_MAX)) return 0;
 return 1;
}
int spline_init(spline_state *s, const spline_model *m) {
 unsigned k, p;
 if (!s || !m || !finite_array(m->pre, SPLINE_PRE) || !finite_array(m->inter, SPLINE_INTER) ||
     !finite_array(m->v[0], 2 * SPLINE_KNOTS) || !finite_array(m->post, SPLINE_POST) ||
     !finite_array(m->lpf, SPLINE_LPF) || !finite_array(m->biquad, 5)) return -1;
 memset(s, 0, sizeof *s); s->model = m;
 for (k = 0; k < 2; k++)
  for (p = 0; p < SPLINE_KNOTS - 1; p++) {
   float slope = (m->v[k][p + 1] - m->v[k][p]) * f(inv_bits[p]);
   float product = f(knot_bits[p]) * slope;
   s->b[k][p] = slope; s->a[k][p] = m->v[k][p] - product;
  }
 return 0;
}
float spline_eval(const float *a, const float *b, float z) {
 unsigned p = 0, step;
 for (step = 16; step; step >>= 1) if (f(knot_bits[p + step]) - z < 0) p += step;   /* the DSP's fsub + negative flag */
 { float product = z * b[p]; return a[p] + product; }
}
static float fir(float x, float *history, uint32_t *pos, const float *h, unsigned n) {
 unsigned k, j = *pos; float sum = 0;
 history[j] = x;
 for (k = 0; k < n; k++) { float product = history[j] * h[k]; sum = sum + product; j = j ? j - 1 : n - 1; }
 *pos = (*pos + 1 == n) ? 0 : *pos + 1;
 return sum;
}
void spline_process(spline_state *s, const float *in, float *out, size_t n) {
 const spline_model *m = s->model; const float *bq = m->biquad;
 size_t i; unsigned k;
 for (i = 0; i < n; i++) {
  float first = fir(in[i] * m->input_gain, s->pre, &s->pre_pos, m->pre, SPLINE_PRE), d = first - s->previous, y = 0, z;
  float points[4]; points[0] = s->previous; points[1] = s->previous + d / 3.0f; points[2] = s->previous + 2.0f * d / 3.0f;
  points[3] = first; s->previous = first;
  for (k = 0; k < 4; k++) {
   float u = spline_eval(s->a[0], s->b[0], points[k]);
   u = spline_eval(s->a[1], s->b[1], fir(u, s->inter, &s->inter_pos, m->inter, SPLINE_INTER));
   if (k == 3) y = fir(u, s->lpf, &s->lpf_pos, m->lpf, SPLINE_LPF);
   else { s->lpf[s->lpf_pos] = u; s->lpf_pos = (s->lpf_pos + 1) % SPLINE_LPF; }
  }
  z = bq[0] * y + bq[1] * s->x1 + bq[2] * s->x2 - bq[3] * s->y1 - bq[4] * s->y2;
  s->x2 = s->x1; s->x1 = y; s->y2 = s->y1; s->y1 = z;
  out[i] = fir(z, s->post, &s->post_pos, m->post, SPLINE_POST) * m->output_gain;
 }
}
