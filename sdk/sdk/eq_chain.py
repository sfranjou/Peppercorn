"""End-to-end offline check for EQ-slot effects that reuse the stock EQ program.

Cells written by the effect's built Thumb code (interpreter run) are loaded into the coprocessor
simulator together with the stock EQ program; sine blocks are run through it and
 1. every output sample of both output windows must equal a float32 model of the stock routine
    (b0 x + b1 x1 + b2 x2, minus a1 y1 + a2 y2, times k = rsqrt(1.0)^2 measured on hardware,
    five sections in series, then the output level), bit for bit;
 2. the steady-state gain at each test frequency must match the double-precision magnitude of the
    hardware transfer function of the written numbers (k B / (1 + k A) per section, times the level)
    within 0.01 dB. Whether the written numbers realise the intended design is the effect's own
    native test (it knows the design; e.g. para_eq/test_para_eq.c with the measured k).
Uses Sim(static=True) (end word, block copy/multiply are static-only readings; see
protocol/copro_sim.py) — not a hardware proof. No device access.
"""
import math, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from protocol import copro_sim as cs

FLAG, BAND0, LEVEL_T, LEVEL = 0xf9c, 0xf9d, 0xfcf, 0xfd0
RSQRT_ONE = 0x3f7fffb7          # hardware-measured approximate 1/sqrt(1.0) (sdk/copro/test_soft_gain.py)
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]


def _model(sections, level, block, state):
    k = r32(ff(RSQRT_ONE) * ff(RSQRT_ONE)); out = block
    for s, (b0, b1, b2, a1, a2) in enumerate(sections):
        x1, x2, y1, y2 = state[s]; res = []
        for x in out:
            acc = r32(x * b0); acc = r32(acc + r32(x1 * b1)); acc = r32(acc + r32(x2 * b2))
            fbk = r32(y1 * a1); fbk = r32(fbk + r32(y2 * a2))
            y = r32(r32(acc - fbk) * k); x2, x1, y2, y1 = x1, x, y1, y; res.append(y)
        state[s] = (x1, x2, y1, y2); out = res
    return [fb(r32(level * y)) for y in out]


def _mag(sections, f, k=1.0):
    """Magnitude of the cascade as the coprocessor computes it: y = k (B x - A y), i.e.
    H = k B / (1 + k A) per section (k = 1: the plain B / A of the stored numbers)."""
    w = 2 * math.pi * f / 44100; z1, z2 = complex(math.cos(w), -math.sin(w)), complex(math.cos(2 * w), -math.sin(2 * w)); h = 1
    for b0, b1, b2, a1, a2 in sections: h *= k * (b0 + b1 * z1 + b2 * z2) / (1 + k * (a1 * z1 + a2 * z2))
    return abs(h)


def _amplitude(samples, f, start):
    """Least-squares sine amplitude at a known frequency (exact for a steady sinusoid)."""
    w = 2 * math.pi * f / 44100; ss = sc = cc = ys = yc = 0.0
    for i, y in enumerate(samples):
        sn, cn = math.sin(w * (start + i)), math.cos(w * (start + i)); ss += sn * sn; sc += sn * cn; cc += cn * cn; ys += y * sn; yc += y * cn
    det = ss * cc - sc * sc; a = (ys * cc - yc * sc) / det; b = (yc * ss - ys * sc) / det
    return math.hypot(a, b)


def check(cells, spec, params, secondary, freqs=(150, 600, 1500, 6000), blocks=64, amp=0.25):
    d = struct.unpack('<4096I', cells)
    words = list(struct.unpack(f'<{len(secondary) // 4}I', secondary))
    sections = []
    for k in range(5):
        c = [ff(d[BAND0 + 10 * k + j]) for j in range(10)]
        if c[3] != 1.0: raise AssertionError(f'section {k}: a0 {c[3]} != 1.0 (only a0 = 1 has a measured reciprocal)')
        sections.append((c[0], c[1], c[2], c[4], c[5]))
    level, target = ff(d[LEVEL]), ff(d[LEVEL_T])
    if level != target: raise AssertionError('level ramp in progress: current != target')
    if d[FLAG] != 1: raise AssertionError('EQ flag not set by an enabled process call')
    report = dict(level=level, sections=[[round(v, 7) for v in s] for s in sections], frequencies={}, samples_compared=0)
    k = r32(ff(RSQRT_ONE) * ff(RSQRT_ONE))
    for f in freqs:
        sim = cs.Sim(static=True); sim.load_program(0xe00, words)
        for i in range(FLAG, LEVEL + 1): sim.write(i, d[i])
        state = [(0.0, 0.0, 0.0, 0.0)] * 5; tail_in = []; tail_out = []
        for b in range(blocks):
            block = [r32(amp * math.sin(2 * math.pi * f * (b * 64 + n) / 44100)) for n in range(64)]
            for n, x in enumerate(block): sim.write(0x13 + n, fb(x))
            sim.steps = 0   # the step guard is per block (one coprocessor run per audio block)
            if sim.run(0xe00) != 'end': raise AssertionError('EQ program did not reach its end word')
            want = _model(sections, level, block, state)
            got_l = [sim.read(0x93 + n) for n in range(64)]; got_r = [sim.read(0xd3 + n) for n in range(64)]
            if got_l != want or got_r != want:
                n = next(i for i in range(64) if got_l[i] != want[i] or got_r[i] != want[i])
                raise AssertionError(f'{f} Hz block {b} sample {n}: coprocessor {ff(got_l[n])} / {ff(got_r[n])} vs model {ff(want[n])}')
            report['samples_compared'] += 128
            if b >= blocks // 2: tail_in += block; tail_out += [ff(v) for v in want]
        start = (blocks // 2) * 64
        measured = 20 * math.log10(_amplitude(tail_out, f, start) / _amplitude(tail_in, f, start)); designed = 20 * math.log10(_mag(sections, f, k) * level)
        report['frequencies'][f] = dict(measured_db=round(measured, 4), hardware_model_db=round(designed, 4))
        if abs(measured - designed) > 0.01:   # float32 recursion noise; first half of the run settles (~46 ms)
            raise AssertionError(f'{f} Hz: measured {measured:.3f} dB vs designed {designed:.3f} dB')
    report['status'] = 'pass'
    return report
