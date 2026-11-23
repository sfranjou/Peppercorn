"""FIR Lowpass end to end, offline, in the STRICT simulator: the dot block word's accumulation was
measured on the pedal on 2026-10-20 (work/copro_experiments/dot_order_0_m40_002, dot_order_1_m40:
sequential, products rounded then added). Window bit-equal to the sequential float32 model, within
float32 bounds of a double convolution, response (passband ~0 dB, stopband an octave above
cutoff) and bypass."""
import math, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk')]
import run_effect
from protocol import copro_sim as cs
from sdk.eq_chain import _amplitude
BUILD = ROOT / 'work/sdk_check/fir_lowpass/build'
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
N, ENABLE, LEVEL, TAPS, HIST = 32, 0x193, 0x194, 0x1a0, 0x1c0


def setup(params, hyp=()):
    params = [float(v) for v in params] + [0.0] * (8 - len(params))
    mem = bytearray(0x4000); arm = run_effect.OverlayRunner.from_build(BUILD, ((0x28000000, mem),))
    words = list(struct.unpack(f'<{(BUILD / "secondary.bin").stat().st_size // 4}I', (BUILD / 'secondary.bin').read_bytes()))
    sim = cs.Sim(hypotheses=hyp); sim.load_program(0, words); arm.init(params)
    d = struct.unpack('<4096I', bytes(mem))
    for i in range(ENABLE, HIST + N + 63): sim.write(i, d[i])
    sim.write(0x10, 0)
    return params, mem, arm, sim


def run(params, freq, blocks, amp=0.25, enable_at=lambda b: 1, hyp=()):
    params, mem, arm, sim = setup(params, hyp); hist = [0.0] * (N - 1); res = []
    for b in range(blocks):
        en = enable_at(b); arm.process([(0.0, 0.0)] * 64, params, en); d = struct.unpack('<4096I', bytes(mem))
        for i in list(range(ENABLE, LEVEL + 1)) + list(range(TAPS, TAPS + N)): sim.write(i, d[i])
        block = [r32(amp * math.sin(2 * math.pi * freq * (b * 64 + n) / 44100)) for n in range(64)]
        for n, x in enumerate(block): sim.write(0x13 + n, fb(x))
        sim.steps = 0; assert sim.run(0, stop=(0x500,)) == 'stop'
        got = [ff(sim.read(0x13 + n)) for n in range(64)]
        taps = [ff(d[TAPS + k]) for k in range(N)]; lev = ff(d[LEVEL])
        if en:
            buf = hist + block; seq = []; exact = []
            for i in range(64):
                acc = 0.0
                for k in range(N): acc = r32(acc + r32(taps[k] * buf[i + k]))
                seq.append(r32(acc * lev)); exact.append(sum(taps[k] * buf[i + k] for k in range(N)) * lev)
            hist = buf[64:]
        else:
            seq = exact = block
        res.append((en, block, got, seq, exact, taps, lev))
    return res


class FirLowpass(unittest.TestCase):
    def test_block_sum_is_refused(self):
        sim = cs.Sim(); sim.load_program(0xf80, [0x7906_0f05, 0x7a06_0004, 0x200c0000]); sim.r[8] = 0
        for i in range(4): sim.write(0xf05 + i, 0x3f800000)
        with self.assertRaises(cs.UnconfirmedInstruction): sim.run(0xf80, stop=(0xf83,))

    def test_bit_exact_strict_and_order_independent_bound(self):
        for en, block, got, seq, exact, taps, lev in run([60, 50], 700, 10, enable_at=lambda b: 0 if b == 4 else 1):
            self.assertEqual([fb(v) for v in got], [fb(v) for v in seq])
            if en:
                bound = sum(abs(t) for t in taps) * 0.25 * lev * N * 2 ** -23 * 2
                self.assertLess(max(abs(g - e) for g, e in zip(got, exact)), bound)

    def test_response(self):
        def gain(f, p=[50, 50]):
            res = run(p, f, 16); tail = res[8:]; x = [v for r in tail for v in r[1]]; y = [v for r in tail for v in r[2]]
            # linear phase delay 15.5 samples: amplitude fit is delay-independent
            return 20 * math.log10(_amplitude(y, f, 8 * 64) / _amplitude(x, f, 8 * 64))
        fc = 500 * 24 ** 0.5                            # Cutoff 50 -> ~2449 Hz
        self.assertAlmostEqual(gain(300), 0.0, delta=0.3)
        self.assertLess(gain(2 * fc), -20.0)


if __name__ == '__main__':
    unittest.main()
