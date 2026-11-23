"""NS Capture v6 = v5 + GPTC compact tone-capture records, offline: built Thumb init/process + built program in the strict
simulator (sdk/test_ns_capture_v5.Runner, a fresh program load per Runner as the stock reload does).
- Every v5 format (stock VTSI SnapTones, GP5N v2/v3, GP5P user programs incl. errors and the watchdog) gives output
  bit-identical to the v5 build.
- GPTC records give output bit-identical to the tone_compact_063 build (parallel and single front, knob changes).
- Malformed GPTC records bypass; the watchdog also covers GPTC mode.
Builds: work/sdk_build/ns_capture_v5, ns_capture_v6, tone_compact_063 (sdk/build_effect.py)."""
import struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk'), str(ROOT / 'scripts/tone_capture')]
import numpy as np
import test_ns_capture_v5 as T5
import test_ns_capture_v3 as T3
B5, B6, BC = ROOT / 'work/sdk_build/ns_capture_v5', ROOT / 'work/sdk_build/ns_capture_v6', ROOT / 'work/sdk_build/tone_compact_063'
GPTC = {n: (ROOT / f'work/tone_capture/deployment_063/{n}.gptc').read_bytes() for n in ('high_gain', 'distorted', 'clean')}
GMODE, ENABLE = 0x3e7, 0x398
fb = T5.fb


def run(build, content, knobs, x, hyp=(), changes=()):
    """Blocks of x; changes = {block index: new knob list} applied before that block."""
    r = T5.Runner(build, content, knobs, hyp); out = []
    for k in range(0, len(x), 64):
        if k // 64 in dict(changes): r.params[:5] = [float(v) for v in dict(changes)[k // 64]]
        out += r.block(list(x[k:k + 64]))
    return np.array(out, dtype=np.float32), r


def signal(n, amp=0.3): return T5.signal(n, amp)


class NSCaptureV6(unittest.TestCase):
    def test_v5_formats_identical(self):
        x = signal(64 * 8)
        cases = [('vtsi factory 5', T3.factory(5), ('ftz',)), ('vtsi factory 33', T3.factory(33), ('ftz',)),
                 ('gp5n v3', T3.REC3.record(fir=[0.3, -0.2, 0.1] * 50), ('ftz',)),
                 ('gp5p gain', T5.record('gain'), ()), ('gp5p lowpass', T5.record('lowpass'), ()), ('gp5p softclip', T5.record('softclip'), ()),
                 ('empty', None, ()), ('garbage', bytes(range(256)) * 10 + bytes(136), ())]
        for name, content, hyp in cases:
            with self.subTest(name):
                knobs = [60, 40, 50, 55, 45]; ch = {3: [30, 70, 20, 80, 65]}
                y5, r5 = run(B5, content, knobs, x, hyp, ch); y6, r6 = run(B6, content, knobs, x, hyp, ch)
                self.assertEqual(y6.tobytes(), y5.tobytes())
                self.assertEqual([r6.cell(c) for c in (0x3a3, 0x3a6, 0x3a7, ENABLE)], [r5.cell(c) for c in (0x3a3, 0x3a6, 0x3a7, ENABLE)])
                self.assertEqual(r6.cell(GMODE), 0)

    def test_gp5p_errors_and_watchdog_as_v5(self):
        rec = bytearray(T5.record('gain')); rec[130] ^= 1
        for b in (B5, B6):
            r = T5.Runner(b, bytes(rec), [50] * 5); self.assertEqual((r.cell(0x3a7), r.cell(0x3a6) & 0xff), (0, T5.gp5p.ERRORS.index('crc')))

    def test_gptc_identical_to_063(self):
        x = signal(64 * 10, 0.4)
        for name, rec in GPTC.items():
            for knobs, ch in (([50] * 5, {}), ([70, 10, 50, 50, 50], {4: [30, 60, 20, 80, 65], 7: [100, 100, 0, 100, 0]})):
                with self.subTest(name, knobs=knobs):
                    yc, rc = run(BC, rec, knobs, x, (), ch); y6, r6 = run(B6, rec, knobs, x, (), ch)
                    self.assertEqual((r6.cell(GMODE), r6.cell(ENABLE)), (1, 1))
                    self.assertTrue(np.isfinite(y6).all() and np.abs(y6).max() > 1e-4)
                    self.assertEqual(y6.tobytes(), yc.tobytes())

    def test_gptc_malformed_bypasses(self):
        x = signal(64 * 2)
        rec = bytearray(GPTC['clean']); rec[600] ^= 1                                          # hash mismatch
        y6, r6 = run(B6, bytes(rec), [50] * 5, x)
        self.assertEqual((r6.cell(GMODE), r6.cell(ENABLE)), (0, 0)); self.assertEqual(y6.tobytes(), x.astype(np.float32).tobytes())
        rec = bytearray(GPTC['clean']); rec[4] = 2                                             # unknown version
        y6, r6 = run(B6, bytes(rec), [50] * 5, x); self.assertEqual(r6.cell(GMODE), 0)

    def test_gptc_watchdog(self):
        r = T5.Runner(B6, GPTC['distorted'], [50] * 5); x = list(signal(64))
        r.block(x)
        struct.pack_into('<I', r.mem, 0x8040, 2)                                               # coprocessor still busy
        r.arm.process([(0.0, 0.0)] * 64, r.params, 1)
        self.assertEqual((struct.unpack_from('<I', r.mem, 0x8000)[0], r.cell(0x3a6), r.cell(ENABLE)), (0, 0xff, 0))
        self.assertEqual([fb(v) for v in r.block(x)], [fb(v) for v in x])

    def test_layout(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('p6', ROOT / 'sdk/effects/ns_capture_v6/program.py'); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
        self.assertLessEqual(P.GPTC_PC, P.USER_PC); self.assertLessEqual(P.CODE_END, P.GPTC_TW_PC)
        self.assertEqual((P.GPTC_TW_PC, P.GPTC_SPEC_PC), (0xb58, 0xbf8))
        v5 = (B5 / 'secondary.bin').read_bytes(); v6 = (B6 / 'secondary.bin').read_bytes()
        self.assertEqual(len(v6) // 4, P.CODE_END - 0x500)


if __name__ == '__main__':
    unittest.main()
