"""NS Capture (own N->S with a long post filter) end to end, offline: the built Thumb init parses a GP5N v2 record
(group-9 content ABI), writes cells, twiddles and filter spectra (program-memory window); the built program runs
in the STRICT simulator. Output vs a numpy model of the chain (float32 biquads/clipper, float64 FIR); non-GP5N
records bypass; C constants match program.py."""
import math, random, re, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk'), str(ROOT / 'sdk/effects/ns_capture_v2')]
import numpy as np
import importlib.util
import run_effect


def _load(name, path):   # by path, under a unique name: both NS Capture versions run in one test process
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


P = _load('ns_capture_v2_program', ROOT / 'sdk/effects/ns_capture_v2/program.py')
ns_record = _load('ns_capture_v2_record', ROOT / 'sdk/effects/ns_capture_v2/ns_record.py')
from protocol import copro_sim as cs
BUILD = ROOT / 'work/sdk_build/ns_capture_v2'
fb = lambda v: struct.unpack('<I', struct.pack('<f', float(v)))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
C = P.CELLS


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


class Runner:
    def __init__(self, content, params, hypotheses=()):
        self.mem = bytearray(0x8000)
        sec = (BUILD / 'secondary.bin').read_bytes(); self.mem[0x4000 + 4 * 0x500:0x4000 + 4 * 0x500 + len(sec)] = sec
        self.arm = run_effect.OverlayRunner.from_build(BUILD, ((0x28000000, self.mem),))
        self.params = [float(v) for v in params] + [0.0] * 3
        self.arm.init_content(self.params, content)
        self.sim = cs.Sim(hypotheses=hypotheses, max_steps=2_000_000); w = struct.unpack('<8192I', bytes(self.mem))
        for i in range(0x1000): self.sim.d[i] = w[i]; self.sim.p[i] = w[0x1000 + i]
        self.seen = bytes(self.mem)

    def block(self, x):
        self.arm.process([(0.0, 0.0)] * 64, self.params, 1); now = bytes(self.mem)
        for i in range(0, 0x8000, 4):
            if now[i:i + 4] != self.seen[i:i + 4]: (self.sim.d if i < 0x4000 else self.sim.p)[(i // 4) & 0xfff] = struct.unpack_from('<I', now, i)[0]
        self.seen = now
        for n, s in enumerate(x): self.sim.d[0x13 + n] = fb(s)
        self.sim.steps = 0; self.sim.r[14] = None
        assert self.sim.run(0x500, stop=(0xe00,)) == 'stop'
        return [ff(self.sim.d[0x13 + n]) for n in range(64)]


class NSCapture(unittest.TestCase):
    def test_constants_match_program(self):
        src = (ROOT / 'sdk/effects/ns_capture_v2/ns_capture.c').read_text()
        d = {k: int(v, 0) for k, v in re.findall(r'#define (NS_PARTS|NS_TW_PC|NS_SPEC_PC) (0x[0-9a-f]+|\d+)u', src)}
        self.assertEqual(d, dict(NS_PARTS=P.PARTS, NS_TW_PC=P.TW_PC, NS_SPEC_PC=P.SPEC_PC))
        self.assertEqual(ns_record.TAPS_MAX, 64 * P.PARTS)

    def test_chain_matches_model(self):
        rng = np.random.default_rng(11)
        h = list(rng.uniform(-1, 1, 600) * np.exp(-np.arange(600) / 120) * 0.2)
        rec = ns_record.record(drive=3.0, bias=0.15, level=0.6, pre=(rbj('hp', 90), rbj('lp', 7000)), post=(rbj('lp', 5000), rbj('hp', 50)), fir=h)
        hq = np.array(ns_record.taps(rec), dtype=np.float64)
        params = [62, 45, 60, 40, 55]; run = Runner(rec, params); B = 24
        x = (0.3 * np.sin(2 * np.pi * 147 * np.arange(64 * B) / 44100) + 0.05 * rng.uniform(-1, 1, 64 * B)).astype(np.float32)
        y = np.concatenate([run.block(x[k:k + 64]) for k in range(0, 64 * B, 64)])
        d = run.sim.d; co = lambda k: tuple(ff(d[C[k] + i]) for i in range(5))
        st = {k: (0.0,) * 4 for k in ('PRE_A', 'PRE_B', 'POST_A', 'POST_B', 'BASS', 'MID', 'TREBLE')}
        g, bias, dc, lev = (ff(d[C[k]]) for k in ('DRIVE', 'BIAS', 'DC', 'LEVEL')); z = []
        for k in range(0, 64 * B, 64):
            v = list(x[k:k + 64])
            for name in ('PRE_A', 'PRE_B'): v, st[name] = biquad(v, co(name), st[name])
            out = []
            for s in v:
                u = r32(r32(s * g) + bias)
                if r32(1.0 - u) < 0: u = 1.0
                if r32(u + 1.0) < 0: u = -1.0
                q = r32(1.5 - r32(r32(u * u) * 0.5)); out.append(r32(r32(r32(u * q) - dc) * lev))
            for name in ('POST_A', 'POST_B'): out, st[name] = biquad(out, co(name), st[name])
            z += out
        z = np.convolve(np.array(z, dtype=np.float64), hq)[:64 * B]
        for name in ('BASS', 'MID', 'TREBLE'):
            z, _ = biquad([r32(v) for v in z], co(name), (0.0,) * 4); z = np.array(z)
        err = np.max(np.abs(y - z)) / np.max(np.abs(z))
        self.assertLess(err, 1e-4, err); print(f'\n  NS Capture chain vs model: max rel err {err:.1e}, {run.sim.steps} steps/block', end='')

    def test_non_gp5n_records_bypass(self):
        for content in (None, b'VTSI' + struct.pack('<I', 0xa88) + bytes(2688), ns_record.record()[:4] + struct.pack('<I', 1) + bytes(2688)):
            run = Runner(content, [50] * 5); x = [0.01 * math.sin(n / 3) for n in range(64)]
            self.assertEqual([fb(v) for v in run.block(x)], [fb(r32(v)) for v in x])

    def test_unit_impulse_default_and_record_size(self):
        rec = ns_record.record()
        self.assertEqual(len(rec), 2696)
        run = Runner(rec, [50] * 5); x = (0.2 * np.sin(np.arange(64 * 6) / 7)).astype(np.float32)
        y = np.concatenate([run.block(x[k:k + 64]) for k in range(0, len(x), 64)])
        self.assertTrue(np.all(np.isfinite(y))); self.assertGreater(np.max(np.abs(y)), 0.05)
        with self.assertRaises(ValueError): ns_record.record(fir=[0.0] * (ns_record.TAPS_MAX + 1))


if __name__ == '__main__':
    unittest.main()
