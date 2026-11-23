"""Auto Pan end to end, offline: built Thumb code (interpreter) writes the cells; the built
coprocessor program runs in Sim(static=True) (only the end word is static-only); both output
windows must equal a float32 model bit for bit, gains must be continuous across blocks and
equal-power at block ends, and the bypass must copy the input to both outputs."""
import json, math, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk')]
import run_effect
from protocol import copro_sim as cs
BUILD = ROOT / 'work/sdk_check/auto_pan/build'
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
CELLS = dict(ENABLE=0xf9c, GL=0xf9d, DGL=0xf9e, GR=0xf9f, DGR=0xfa0)


def run(params, blocks, enable_at=lambda b: 1):
    params = [float(v) for v in params] + [0.0] * (8 - len(params))
    mem = bytearray(0x4000); arm = run_effect.OverlayRunner.from_build(BUILD, ((0x28000000, mem),))
    words = list(struct.unpack(f'<{(BUILD / "secondary.bin").stat().st_size // 4}I', (BUILD / 'secondary.bin').read_bytes()))
    sim = cs.Sim(static=True); sim.load_program(0xe00, words); arm.init(params); out = []
    for b in range(blocks):
        en = enable_at(b)
        arm.process([(0.0, 0.0)] * 64, params, en)
        d = struct.unpack('<4096I', bytes(mem))
        block = [r32(0.3 * math.sin(2 * math.pi * 440 * (b * 64 + n) / 44100)) for n in range(64)]
        for n, x in enumerate(block): sim.write(0x13 + n, fb(x))
        for c in CELLS.values(): sim.write(c, d[c])
        sim.steps = 0; assert sim.run(0xe00) == 'end'
        out.append((en, block, {k: d[v] for k, v in CELLS.items()}, [sim.read(0x93 + n) for n in range(64)], [sim.read(0xd3 + n) for n in range(64)]))
    return out


class AutoPan(unittest.TestCase):
    def test_outputs_match_float32_model_bit_for_bit(self):
        for params in ([40, 80, 50], [100, 100, 70], [0, 30, 35]):
            prev_end = None
            for en, block, c, left, right in run(params, 40):
                self.assertEqual(c['ENABLE'], 1)
                gl, gr, dl, dr = ff(c['GL']), ff(c['GR']), ff(c['DGL']), ff(c['DGR']); wl = []; wr = []
                # Continuous across blocks: the ARM restarts from its exact target while the coprocessor
                # reached it by 64 float32 additions; the step is ~1e-6 (about -120 dB), bounded here.
                if prev_end: self.assertLess(max(abs(gl - prev_end[0]), abs(gr - prev_end[1])), 1e-5)
                for x in block:
                    gl = r32(gl + dl); gr = r32(gr + dr); wl.append(fb(r32(x * gl))); wr.append(fb(r32(x * gr)))
                self.assertEqual(left, wl); self.assertEqual(right, wr)
                prev_end = (gl, gr)
                vol = params[2] * 0.02
                self.assertAlmostEqual(gl * gl + gr * gr, vol * vol, delta=1e-4 * max(1, vol * vol))   # equal power at block end

    def test_pans_both_ways(self):
        res = run([80, 100, 50], 400)   # ~2.4 Hz over 0.58 s: more than one LFO cycle
        ratio = [ff(c['GL']) - ff(c['GR']) for _, _, c, _, _ in res]
        self.assertLess(min(ratio), -0.5); self.assertGreater(max(ratio), 0.5)

    def test_bypass_copies_input_to_both_outputs(self):
        for en, block, c, left, right in run([40, 80, 50], 6, enable_at=lambda b: b % 2):
            if not en:
                self.assertEqual(c['ENABLE'], 0)
                self.assertEqual(left, [fb(x) for x in block]); self.assertEqual(right, [fb(x) for x in block])


if __name__ == '__main__':
    unittest.main()
