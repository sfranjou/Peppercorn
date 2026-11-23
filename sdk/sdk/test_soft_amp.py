"""Soft Amp end to end, offline and STRICT: built Thumb code (interpreter) writes the cells; the
built AMP-slot program runs in Sim() without static-only forms (every word executed on the pedal)
until it jumps to the CAB slot. Checks: window bit-equal to a float32 model (gain, clamp, cubic,
level, then the biquad block), output bounded by the level, small-signal slope 1.5, bypass leaves
the window untouched."""
import math, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk')]
import run_effect
from protocol import copro_sim as cs
BUILD = ROOT / 'work/sdk_check/soft_amp/build'
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
C = dict(ENABLE=0x398, GAIN=0x399, ONE=0x39a, NONE=0x39b, C15=0x39c, C05=0x39d, LEVEL=0x39e, TONE=0x3a0)


def model(block, d, st):
    g, lev = ff(d[C['GAIN']]), ff(d[C['LEVEL']]); b0, b1, b2, a1, a2 = (ff(d[C['TONE'] + i]) for i in range(5)); x1, x2, y1, y2 = st
    clipped = []
    for x in block:
        v = r32(x * g)
        if r32(1.0 - v) < 0: v = 1.0
        if r32(v + 1.0) < 0: v = -1.0                      # fsub v - (-1)
        q = r32(v * v); q = r32(q * 0.5); q = r32(1.5 - q); clipped.append(r32(r32(v * q) * lev))
    out = []
    for x in clipped:
        acc = r32(b0 * x); acc = r32(acc + r32(b1 * x1)); acc = r32(acc + r32(b2 * x2))
        t = r32(a1 * y1); t = r32(t + r32(a2 * y2)); y = r32(acc - t); x2, x1, y2, y1 = x1, x, y1, y; out.append(fb(y))
    return clipped, out, (x1, x2, y1, y2)


def run(params, blocks, amp, enable_at=lambda b: 1, freq=220):
    params = [float(v) for v in params] + [0.0] * (8 - len(params))
    mem = bytearray(0x4000); arm = run_effect.OverlayRunner.from_build(BUILD, ((0x28000000, mem),))
    words = list(struct.unpack(f'<{(BUILD / "secondary.bin").stat().st_size // 4}I', (BUILD / 'secondary.bin').read_bytes()))
    sim = cs.Sim(); sim.load_program(0x500, words); arm.init(params)
    d = struct.unpack('<4096I', bytes(mem))
    for i in range(C['ENABLE'], C['TONE'] + 9): sim.write(i, d[i])
    st = (0.0, 0.0, 0.0, 0.0); res = []
    for b in range(blocks):
        en = enable_at(b); arm.process([(0.0, 0.0)] * 64, params, en); d = struct.unpack('<4096I', bytes(mem))
        for i in range(C['ENABLE'], C['TONE'] + 5): sim.write(i, d[i])     # ARM writes everything but the tone state
        block = [r32(amp * math.sin(2 * math.pi * freq * (b * 64 + n) / 44100)) for n in range(64)]
        for n, x in enumerate(block): sim.write(0x13 + n, fb(x))
        sim.steps = 0; assert sim.run(0x500, stop=(0xb00,)) == 'stop'
        got = [sim.read(0x13 + n) for n in range(64)]
        if en: clipped, want, st = model(block, d, st)
        else: clipped, want = None, [fb(x) for x in block]
        res.append((en, block, got, want, clipped, d))
    return res


class SoftAmp(unittest.TestCase):
    def test_bit_exact_strict_simulation_and_bypass(self):
        for p, amp in (([40, 60, 50], 0.3), ([100, 0, 70], 0.8), ([0, 100, 35], 0.05)):
            for en, block, got, want, clipped, d in run(p, 10, amp, enable_at=lambda b: 0 if b == 4 else 1):
                self.assertEqual(got, want)

    def test_clip_curve(self):
        res = run([100, 50, 50], 4, 0.9)                # drive x32: hard into the clipper
        lev = ff(res[0][5][C['LEVEL']])
        self.assertLessEqual(max(abs(v) for r in res for v in r[4]), lev + 1e-7)
        res = run([0, 50, 50], 2, 1e-3)                 # gain 1, tiny signal: slope 1.5 before the tone shelf
        for x, y in zip(res[1][1], res[1][4]):
            if abs(x) > 1e-5: self.assertAlmostEqual(y / x, 1.5 * ff(res[1][5][C['LEVEL']]), delta=1e-4)


if __name__ == '__main__':
    unittest.main()
