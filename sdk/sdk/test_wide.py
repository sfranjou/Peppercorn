"""Wide end to end, offline: built Thumb code (interpreter) writes the biquad cells; the built own
EQ-slot program runs in Sim(static=True) (only the end word is static-only). Checks: both outputs
bit-equal to a float32 model of sdk/copro/asm.py biquad_block (products rounded, then added - the
measured multiply-accumulate), opposite tilts left/right of the designed size, equal levels near
the crossover, bypass copies the input to both outputs."""
import json, math, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk')]
import run_effect
from protocol import copro_sim as cs
from sdk.eq_chain import _amplitude
BUILD = ROOT / 'work/sdk_check/wide/build'
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
ENABLE, BQ_L, BQ_R = 0xf9c, 0xfa1, 0xfaa


def model(block, c, st):
    b0, b1, b2, a1, a2 = c; x1, x2, y1, y2 = st; out = []
    for x in block:
        acc = r32(b0 * x); acc = r32(acc + r32(b1 * x1)); acc = r32(acc + r32(b2 * x2))
        t = r32(a1 * y1); t = r32(t + r32(a2 * y2)); y = r32(acc - t)
        x2, x1, y2, y1 = x1, x, y1, y; out.append(fb(y))
    return out, (x1, x2, y1, y2)


def run(params, freq, blocks, enable_at=lambda b: 1, amp=0.25):
    params = [float(v) for v in params] + [0.0] * (8 - len(params))
    mem = bytearray(0x4000); arm = run_effect.OverlayRunner.from_build(BUILD, ((0x28000000, mem),))
    words = list(struct.unpack(f'<{(BUILD / "secondary.bin").stat().st_size // 4}I', (BUILD / 'secondary.bin').read_bytes()))
    sim = cs.Sim(static=True); sim.load_program(0xe00, words); arm.init(params)
    d = struct.unpack('<4096I', bytes(mem))
    for i in range(ENABLE, BQ_R + 9): sim.write(i, d[i])          # init values incl. zero states
    sl = sr = (0.0, 0.0, 0.0, 0.0); res = []
    for b in range(blocks):
        en = enable_at(b); arm.process([(0.0, 0.0)] * 64, params, en); d = struct.unpack('<4096I', bytes(mem))
        sim.write(ENABLE, d[ENABLE])
        for i in range(5): sim.write(BQ_L + i, d[BQ_L + i]); sim.write(BQ_R + i, d[BQ_R + i])   # ARM writes coefficients only
        block = [r32(amp * math.sin(2 * math.pi * freq * (b * 64 + n) / 44100)) for n in range(64)]
        for n, x in enumerate(block): sim.write(0x13 + n, fb(x))
        sim.steps = 0; assert sim.run(0xe00) == 'end'
        left = [sim.read(0x93 + n) for n in range(64)]; right = [sim.read(0xd3 + n) for n in range(64)]
        if en:
            wl, sl = model(block, [ff(d[BQ_L + i]) for i in range(5)], sl); wr, sr = model(block, [ff(d[BQ_R + i]) for i in range(5)], sr)
        else:
            wl = wr = [fb(x) for x in block]
        res.append((en, block, left, right, wl, wr))
    return res


class Wide(unittest.TestCase):
    def test_bit_exact_and_bypass(self):
        for en, block, left, right, wl, wr in run([60, 40, 50], 700, 12, enable_at=lambda b: 0 if b in (5, 6) else 1):
            self.assertEqual(left, wl); self.assertEqual(right, wr)

    def gains(self, params, f):
        res = run(params, f, 48); tail = res[24:]; start = 24 * 64
        x = [v for _, blk, *_ in tail for v in blk]
        l = [ff(v) for *_, left, _, _, _ in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in tail] for v in left]
        r = [ff(v) for t in tail for v in t[3]]
        return 20 * math.log10(_amplitude(l, f, start) / _amplitude(x, f, start)), 20 * math.log10(_amplitude(r, f, start) / _amplitude(x, f, start))

    def test_opposite_tilts(self):
        p = [100, 50, 50]                               # 9 dB, f = 300 * 10^0.5 ~ 949 Hz, unity volume
        lo_l, lo_r = self.gains(p, 100); hi_l, hi_r = self.gains(p, 8000); mid_l, mid_r = self.gains(p, 949)
        self.assertAlmostEqual(hi_l - lo_l, 9.0, delta=0.6); self.assertAlmostEqual(lo_r - hi_r, 9.0, delta=0.6)
        self.assertAlmostEqual(mid_l, mid_r, delta=0.2)
        self.assertAlmostEqual(lo_l, -lo_r, delta=0.3)  # symmetric around 0 dB


if __name__ == '__main__':
    unittest.main()
