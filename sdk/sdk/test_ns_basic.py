"""NS Basic (own N->S program) end to end, offline and STRICT: the built Thumb init parses a GP5N
content record through the group-9 init ABI (r1 = &content pointer) and writes the cells; the built
N->S program runs in Sim() (executed forms only) until it jumps to the EQ slot. Checks: window
bit-equal to a float32 model of the whole chain over several blocks and knob settings; stock-format
and missing records leave the slot bypassed (window untouched)."""
import math, random, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk'), str(ROOT / 'sdk/effects/ns_basic')]
import run_effect
import ns_record
from protocol import copro_sim as cs
from protocol.overlay_image import parse_container, parse_overlay
BUILD = ROOT / 'work/sdk_build/ns_basic'
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
C = dict(ENABLE=0x398, DRIVE=0x399, BIAS=0x39a, LEVEL=0x39f, DC=0x3a0, PRE_A=0x3a8, PRE_B=0x3b1, POST_A=0x3ba, POST_B=0x3c3,
         BASS=0x3cc, MID=0x3d5, TREBLE=0x3de, TAPS=0x400, HIST=0x480)
N = 128
ARM_WRITES = [*range(0x398, 0x3a1)] + [C[k] + i for k in ('BASS', 'MID', 'TREBLE') for i in range(5)]


def rbj(kind, f, q=0.707):
    w = 2 * math.pi * f / 44100; a = math.sin(w) / (2 * q); c = math.cos(w); a0 = 1 + a
    b = ((1 - c) / 2, 1 - c, (1 - c) / 2) if kind == 'lp' else ((1 + c) / 2, -(1 + c), (1 + c) / 2)
    return tuple(r32(x / a0) for x in (*b, -2 * c, 1 - a))


def biquad(block, co, st):
    b0, b1, b2, a1, a2 = co; x1, x2, y1, y2 = st; out = []
    for x in block:
        acc = r32(b0 * x); acc = r32(acc + r32(b1 * x1)); acc = r32(acc + r32(b2 * x2))
        t = r32(a1 * y1); t = r32(t + r32(a2 * y2)); y = r32(acc - t); x2, x1, y2, y1 = x1, x, y1, y; out.append(y)
    return out, (x1, x2, y1, y2)


class Model:
    def __init__(self): self.st = {k: (0.0, 0.0, 0.0, 0.0) for k in ('PRE_A', 'PRE_B', 'POST_A', 'POST_B', 'BASS', 'MID', 'TREBLE')}; self.hist = [0.0] * (N - 1)

    def block(self, x, d):
        co = lambda k: tuple(ff(d[C[k] + i]) for i in range(5))
        for k in ('PRE_A', 'PRE_B'): x, self.st[k] = biquad(x, co(k), self.st[k])
        g, bias, dc, lev = (ff(d[C[k]]) for k in ('DRIVE', 'BIAS', 'DC', 'LEVEL')); y = []
        for s in x:
            v = r32(r32(s * g) + bias)
            if r32(1.0 - v) < 0: v = 1.0
            if r32(v - (-1.0)) < 0: v = -1.0
            q = r32(r32(r32(v * v) * 0.5)); q = r32(1.5 - q); y.append(r32(r32(r32(v * q) - dc) * lev))
        x = y
        for k in ('POST_A', 'POST_B'): x, self.st[k] = biquad(x, co(k), self.st[k])
        taps = [ff(d[C['TAPS'] + k]) for k in range(N)]; buf = self.hist + x; y = []
        for i in range(64):
            acc = 0.0
            for k in range(N): acc = r32(acc + r32(taps[k] * buf[i + k]))
            y.append(acc)
        self.hist = buf[64:]; x = y
        for k in ('BASS', 'MID', 'TREBLE'): x, self.st[k] = biquad(x, co(k), self.st[k])
        return x


def run(content, params, blocks, amp=0.4, enable=1):
    params = [float(v) for v in params] + [0.0] * (8 - len(params))
    mem = bytearray(0x4000); arm = run_effect.OverlayRunner.from_build(BUILD, ((0x28000000, mem),))
    words = list(struct.unpack(f'<{(BUILD / "secondary.bin").stat().st_size // 4}I', (BUILD / 'secondary.bin').read_bytes()))
    sim = cs.Sim(); sim.load_program(0x500, words); arm.init_content(params, content)
    d = struct.unpack('<4096I', bytes(mem))
    for i in range(0x398, C['HIST'] + N + 63): sim.write(i, d[i])
    model = Model(); rng = random.Random(9); res = []
    for b in range(blocks):
        arm.process([(0.0, 0.0)] * 64, params, enable); d = struct.unpack('<4096I', bytes(mem))
        for i in ARM_WRITES: sim.write(i, d[i])
        x = [r32(amp * math.sin(2 * math.pi * 196 * (b * 64 + n) / 44100) + 0.125 * amp * rng.uniform(-1, 1)) for n in range(64)]
        for n, s in enumerate(x): sim.write(0x13 + n, fb(s))
        sim.steps = 0; assert sim.run(0x500, stop=(0xe00,)) == 'stop'
        got = [sim.read(0x13 + n) for n in range(64)]
        want = [fb(s) for s in (model.block(x, d) if d[C['ENABLE']] & 1 else x)]
        res.append((got, want, d, x))
    return res


def stock_vtsi():
    g = parse_container((ROOT / 'work/custom_images/mod046_reload_veneer/regions/decoded_g.bin').read_bytes())
    return b'VTSI' + struct.pack('<I', 0xa88) + bytes(range(256)) * 10 + bytes(2696 - 8 - 2560)


class NSBasic(unittest.TestCase):
    REC = ns_record.record(drive=4.0, bias=0.2, level=0.5, pre=(rbj('hp', 80), rbj('lp', 6000)), post=(rbj('lp', 4500), rbj('hp', 60)),
                           fir=[r32(math.exp(-k / 6) * (0.6 if k % 2 else 1.0) / 3) for k in range(40)])

    def test_bit_exact_strict_chain(self):
        for params in ([50] * 5, [80, 30, 70, 20, 90], [0, 100, 0, 100, 0]):
            for got, want, d, _ in run(self.REC, params, 6):
                self.assertEqual(d[C['ENABLE']], 1); self.assertEqual(got, want)

    def test_identity_fir_default_and_bias_removed(self):
        r = ns_record.record(drive=1.0, bias=0.5, level=1.0)
        res = run(r, [50] * 5, 3, amp=1e-3)
        for got, want, d, x in res: self.assertEqual(got, want)
        self.assertLess(max(abs(ff(v)) for v in res[-1][0]), 0.01)   # DC from the bias point removed

    def test_non_gp5n_records_stay_bypassed(self):
        for content in (None, stock_vtsi(), b'GP5N' + struct.pack('<I', 2) + bytes(2688)):
            for got, want, d, x in run(content, [50] * 5, 2):
                self.assertEqual(d[C['ENABLE']], 0); self.assertEqual(got, [fb(s) for s in x])

    def test_record_fits_upload(self):
        self.assertEqual(len(self.REC), 2696); self.assertEqual(self.REC[:4], b'GP5N')
        with self.assertRaises(ValueError): ns_record.record(fir=[0.0] * 129)


if __name__ == '__main__':
    unittest.main()
