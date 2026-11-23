"""fir_long_block in the STRICT simulator (dot measured): a 200-tap FIR in the CAB slot frame,
outputs bit-equal to the sequential float32 model over 8 blocks (history carried by chunked
non-overlapping copies), and the CAB frame rules accept the program."""
import math, random, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from sdk.copro import asm, frame
from protocol import copro_sim as cs
fb = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
N, TAPS, HIST = 200, 0x600, 0x700


class FirLong(unittest.TestCase):
    def program(self):
        src = [('li', 5, 0x580), ('load_ind', 6, 5), ('skip_if_bit0', 6), ('jump', 'bypass'),
               *asm.fir_long_block(0x13, TAPS, HIST, N, 'fir'), ('jump', 0xe00), 'bypass:', ('jump', 0xe00)]
        return asm.assemble(src, 0xb00)

    def test_frame_and_bit_exact(self):
        words = self.program(); rep = frame.check(4, words); self.assertEqual(rep['slot'], 'CAB')
        rng = random.Random(4); h = [r32(rng.uniform(-1, 1) * math.exp(-k / 40) / 10) for k in range(N)]
        sim = cs.Sim(); sim.load_program(0xb00, words); sim.write(0x580, 1)
        for k in range(N): sim.write(TAPS + k, fb(h[N - 1 - k]))
        for k in range(N + 63): sim.write(HIST + k, 0)
        hist = [0.0] * (N - 1)
        for b in range(8):
            block = [r32(0.3 * math.sin(0.05 * (b * 64 + n)) + 0.1 * rng.uniform(-1, 1)) for n in range(64)]
            for n, x in enumerate(block): sim.write(0x13 + n, fb(x))
            sim.steps = 0; self.assertEqual(sim.run(0xb00, stop=(0xe00,)), 'stop')
            buf = hist + block; want = []
            for i in range(64):
                acc = 0.0
                for k in range(N): acc = r32(acc + r32(h[N - 1 - k] * buf[i + k]))
                want.append(fb(acc))
            self.assertEqual([sim.read(0x13 + n) for n in range(64)], want); hist = buf[64:]


if __name__ == '__main__':
    unittest.main()
