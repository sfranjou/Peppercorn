"""NS Capture v4 = v3 + GP5N v3 records (stock SnapTone structure with a post filter up to 704 taps, for WH fits from
scripts/tone_capture). Offline: v4 VTSI output = v3; GP5N v3 record vs the host renderer fed the same coefficients."""
import importlib.util, struct, sys, unittest
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk'), str(ROOT / 'scripts/tone_capture')]
import numpy as np
import vtsi_render as vr
import test_ns_capture_v3 as T3
spec = importlib.util.spec_from_file_location('ns_capture_v4_record', ROOT / 'sdk/effects/ns_capture_v4/ns_record.py')
R4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(R4)
B4 = ROOT / 'work/sdk_build/ns_capture_v4'


class NSCaptureV4(unittest.TestCase):
    def test_vtsi_equals_v3(self):
        raw = T3.factory(7); x = (0.2 * np.sin(np.arange(64 * 10) / 6)).astype(np.float32)
        y4 = T3.Runner(B4, raw, [55, 50, 50, 50, 50]).run(x); y3 = T3.Runner(T3.NSCaptureV3.B3, raw, [55, 50, 50, 50, 50]).run(x)
        self.assertEqual(y4.tobytes(), y3.tobytes())

    def test_wh_record_matches_renderer(self):
        base = vr.Vtsi(T3.factory(12)); rng = np.random.default_rng(3)
        post = (rng.uniform(-1, 1, 700) * np.exp(-np.arange(700) / 150) * 0.4).tolist()
        rec = R4.record_wh(base.fir128, base.nl, base.biquad_b, post, biquad_a=tuple(base.biquad_a))
        r32 = lambda a: np.asarray(a, dtype=np.float32).astype(np.float64)
        model = SimpleNamespace(biquad_a=r32(base.biquad_a), biquad_b=r32(base.biquad_b), nl=r32(base.nl), fir128=r32(base.fir128),
                                fir512=np.array(R4.taps_wh(rec), dtype=np.float64))
        g = np.load(ROOT / 'sdk/effects/ns_capture_v3/lpf40.npy').astype(np.float64); lpf_arg = g.reshape(10, 4)[:, ::-1].reshape(-1)
        for amp in (0.05, 0.4):
            n = 64 * 40; t = np.arange(n); x = (amp * np.sin(2 * np.pi * 180 * t / 44100) + 0.2 * amp * np.sin(2 * np.pi * 2100 * t / 44100)).astype(np.float32)
            run = T3.Runner(B4, rec, [50] * 5); y = run.run(x)
            self.assertEqual((run.sim.d[T3.C['MODE']], run.sim.d[T3.C['PARTS']]), (1, 11))
            ref = vr.render(model, x.astype(np.float64), lpf=lpf_arg); tail = slice(n // 2, None)
            esr = float(np.sum((y[tail] - ref[tail]) ** 2) / np.sum(ref[tail] ** 2))
            print(f'\n  GP5N v3 (700-tap post) amp {amp}: ESR {esr:.1e}', end=''); self.assertLess(esr, 1e-4)

    def test_record_limits(self):
        base = vr.Vtsi(T3.factory(12))
        with self.assertRaises(ValueError): R4.record_wh(base.fir128, base.nl, base.biquad_b, [0.1] * 705)
        self.assertEqual(len(R4.record_wh(base.fir128, base.nl, base.biquad_b, [0.1] * 704)), 2696)


if __name__ == '__main__':
    unittest.main()
