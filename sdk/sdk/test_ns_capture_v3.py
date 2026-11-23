"""NS Capture v3 (own N->S for GP5N and stock VTSI records), offline: built Thumb init/process (interpreter) + built
program (simulator). GP5N mode = v2 output; VTSI mode vs the host SnapTone renderer (scripts/tone_capture/vtsi_render.py)
with our own low-pass; float64 -> float32 conversion exact; empty / foreign records bypass."""
import importlib.util, math, re, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk'), str(ROOT / 'scripts/tone_capture')]
import numpy as np
import run_effect, vtsi_render as vr
from protocol import copro_sim as cs
fb = lambda v: struct.unpack('<I', struct.pack('<f', float(v)))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
F = ROOT / 'work/custom_images/mod047_ns_capture/regions/decoded_f.bin'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


P = _load('ns_capture_v3_program', ROOT / 'sdk/effects/ns_capture_v3/program.py')
REC3 = _load('ns_capture_v3_record', ROOT / 'sdk/effects/ns_capture_v3/ns_record.py')
REC2 = _load('ns_capture_v2_record', ROOT / 'sdk/effects/ns_capture_v2/ns_record.py')
C = P.CELLS


class Runner:
    def __init__(self, build, content, params, hypotheses=('ftz',)):
        self.mem = bytearray(0x8000); sec = (build / 'secondary.bin').read_bytes(); self.mem[0x4000 + 0x1400:0x4000 + 0x1400 + len(sec)] = sec
        self.arm = run_effect.OverlayRunner.from_build(build, ((0x28000000, self.mem),)); self.params = [float(v) for v in params] + [0.0] * 3
        self.arm.init_content(self.params, content)
        self.sim = cs.Sim(hypotheses=hypotheses, max_steps=3_000_000); w = struct.unpack('<8192I', bytes(self.mem))
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

    def run(self, x): return np.concatenate([self.block(x[k:k + 64]) for k in range(0, len(x), 64)])


def factory(k): return F.read_bytes()[0x11000 + 0x1000 * k:0x11000 + 0x1000 * k + vr.RECORD_SIZE]


class NSCaptureV3(unittest.TestCase):
    B3 = ROOT / 'work/sdk_build/ns_capture_v3'; B2 = ROOT / 'work/sdk_build/ns_capture_v2'

    def test_constants_match_program(self):
        src = (ROOT / 'sdk/effects/ns_capture_v3/ns_capture.c').read_text()
        d = {k: int(v, 0) for k, v in re.findall(r'#define (NS_PARTS_MAX|NS_TW_PC|NS_SPEC_PC) (0x[0-9a-f]+|\d+)u', src)}
        self.assertEqual(d, dict(NS_PARTS_MAX=P.PARTS_MAX, NS_TW_PC=P.TW_PC, NS_SPEC_PC=P.SPEC_PC))
        self.assertEqual(REC3.TAPS_MAX, 64 * P.PARTS_MAX)

    def test_gp5n_mode_equals_v2(self):
        rng = np.random.default_rng(4); h = list(rng.uniform(-1, 1, 500) * np.exp(-np.arange(500) / 100) * 0.3)
        args = dict(drive=2.0, bias=0.1, level=0.6, fir=h)
        x = (0.3 * np.sin(np.arange(64 * 12) / 9) + 0.02 * rng.uniform(-1, 1, 64 * 12)).astype(np.float32)
        y3 = Runner(self.B3, REC3.record(**args), [60, 45, 55, 50, 40]).run(x)
        y2 = Runner(self.B2, REC2.record(**args), [60, 45, 55, 50, 40]).run(x)
        self.assertLess(np.max(np.abs(y3 - y2)) / np.max(np.abs(y2)), 1e-5)

    def test_vtsi_cells_and_double_conversion(self):
        raw = factory(10); run = Runner(self.B3, raw, [50] * 5); d = run.sim.d
        self.assertEqual(d[C['MODE']], 1); self.assertEqual(d[C['PARTS']], 8)
        want = [np.float32(v) for v in struct.unpack_from('<5d', raw, 0x18)]
        self.assertEqual([ff(d[C['BQA'] + i]) for i in range(5)], [float(v) for v in want])

    def test_vtsi_matches_renderer(self):
        g = np.load(ROOT / 'sdk/effects/ns_capture_v3/lpf40.npy').astype(np.float64)
        lpf_arg = g.reshape(10, 4)[:, ::-1].reshape(-1)          # the renderer reverses within groups of 4; undo it
        for k, amp, params in ((10, 0.05, [50] * 5), (3, 0.3, [70, 40, 60, 45, 55])):
            raw = factory(k); B = 40; n = 64 * B; t = np.arange(n)
            x = (amp * np.sin(2 * np.pi * 220 * t / 44100) + 0.3 * amp * np.sin(2 * np.pi * 1730 * t / 44100)).astype(np.float32)
            y = Runner(self.B3, raw, params).run(x)
            ref = vr.render(vr.Vtsi(raw), x.astype(np.float64), *params, lpf=lpf_arg)
            tail = slice(n // 2, None)
            esr = float(np.sum((y[tail] - ref[tail]) ** 2) / np.sum(ref[tail] ** 2))
            print(f'\n  VTSI record {k} amp {amp}: ESR {esr:.1e}, rms {np.sqrt(np.mean(y[tail]**2)):.3f} vs {np.sqrt(np.mean(ref[tail]**2)):.3f}', end='')
            self.assertLess(esr, 1e-4, (k, esr))

    def test_empty_and_foreign_records_bypass(self):
        empty = b'VTSI' + struct.pack('<I', 0xa88) + bytes(2688)
        for content in (None, empty, REC3.record()[:4] + struct.pack('<I', 1) + bytes(2688)):
            run = Runner(self.B3, content, [50] * 5); x = [0.01 * math.sin(n / 3) for n in range(64)]
            self.assertEqual([fb(v) for v in run.block(x)], [fb(np.float32(v)) for v in x])


if __name__ == '__main__':
    unittest.main()
