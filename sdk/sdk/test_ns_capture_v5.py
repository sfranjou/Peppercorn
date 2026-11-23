"""NS Capture v5 user programs (GP5P), offline: built Thumb init/process + built program in the strict simulator.
User examples run as their models; bad CRC / rejected programs bypass with an error code; the watchdog stops the
coprocessor and bypasses; GP5N and stock VTSI records give the same output as v4."""
import math, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk'), str(ROOT / 'scripts/tone_capture')]
import numpy as np
import run_effect, test_ns_capture_v3 as T3
from protocol import copro_sim as cs
from sdk.copro import asm, gp5p
from sdk.user_programs import examples as E
fb, ff = T3.fb, T3.ff
B5 = ROOT / 'work/sdk_build/ns_capture_v5'; B4 = ROOT / 'work/sdk_build/ns_capture_v4'
UERR, UMODE, ENABLE = 0x3a6, 0x3a7, 0x398
r32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]


class Runner(T3.Runner):
    """T3.Runner plus the coprocessor control registers (0x28008000 / +0x40) the watchdog uses."""
    def __init__(self, build, content, params, hypotheses=()):
        self.mem = bytearray(0x8100); sec = (build / 'secondary.bin').read_bytes(); self.mem[0x4000 + 0x1400:0x4000 + 0x1400 + len(sec)] = sec
        self.arm = run_effect.OverlayRunner.from_build(build, ((0x28000000, self.mem),)); self.params = [float(v) for v in params] + [0.0] * 3
        self.arm.init_content(self.params, content)
        self.sim = cs.Sim(hypotheses=hypotheses, max_steps=3_000_000); w = struct.unpack('<8192I', bytes(self.mem[:0x8000]))
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

    def cell(self, i): return struct.unpack_from('<I', self.mem, 4 * i)[0]


def record(name):
    code, data, base, zero, knobs = E.build(name); return gp5p.pack(code, data, base, zero, knobs, name)


def signal(n, amp=0.3): return (amp * np.sin(np.arange(n) / 7) + 0.1 * amp * np.sin(np.arange(n) / 1.3)).astype(np.float32)


class NSCaptureV5(unittest.TestCase):
    def test_gain_program(self):
        run = Runner(B5, record('gain'), [50] * 5); x = signal(64 * 4); y = run.run(x)
        self.assertEqual((run.cell(UMODE), run.cell(UERR), run.cell(ENABLE)), (1, 0, 1))
        g = ff(run.cell(E.D)); self.assertAlmostEqual(g, 10 ** (-6 / 20), places=3)        # Gain 50 on -24..+12 dB
        self.assertEqual([fb(v) for v in y], [fb(r32(float(s) * g)) for s in x])

    def test_lowpass_and_softclip_programs(self):
        x = signal(64 * 6)
        run = Runner(B5, record('lowpass'), [50] * 5); y = run.run(x)
        co = [ff(run.cell(E.D + 16 + i)) for i in range(5)]; g = ff(run.cell(E.D))
        st = (0.0, 0.0, 0.0, 0.0); out = []
        for k in range(0, len(x), 64):
            bq, st = T3_biquad(list(x[k:k + 64]), co, st); out += [r32(v * g) for v in bq]
        self.assertEqual([fb(v) for v in y], [fb(v) for v in out])
        run = Runner(B5, record('softclip'), [80, 60, 50, 50, 50]); y = run.run(x)
        drive, lev = ff(run.cell(E.D)), ff(run.cell(E.D + 5))
        self.assertAlmostEqual(drive, 30 ** 0.8, delta=0.05)
        want = []
        for s in x:
            v = r32(float(s) * drive); v = min(max(v, -1.0), 1.0)
            want.append(r32(r32(v * r32(1.5 - r32(r32(v * v) * 0.5))) * lev))
        self.assertEqual([fb(v) for v in y], [fb(v) for v in want])

    def test_bad_records_bypass_with_error(self):
        x = signal(64)
        rec = bytearray(record('gain')); rec[130] ^= 1                                       # code corrupted -> CRC
        run = Runner(B5, bytes(rec), [50] * 5)
        self.assertEqual((run.cell(UMODE), run.cell(UERR) & 0xff), (0, gp5p.ERRORS.index('crc')))
        self.assertEqual([fb(v) for v in run.block(x)], [fb(v) for v in x])
        bad = asm.assemble([('load', 0, 0x3b0), ('load_ind', 1, 0), ('jump', 0xe00)], gp5p.USER_PC)   # untraced pointer
        body = struct.pack('<3I', *bad); rec = bytearray(record('gain')); rec[16:18] = struct.pack('<H', 3); rec[18:20] = struct.pack('<H', 0)
        rec[128:128 + 12] = body; rec[12:16] = struct.pack('<I', __import__('zlib').crc32(body) & 0xffffffff)
        run = Runner(B5, bytes(rec), [50] * 5)
        self.assertEqual((run.cell(UMODE), run.cell(UERR)), (0, gp5p.ERRORS.index('pointer') | 1 << 8))
        self.assertEqual([fb(v) for v in run.block(x)], [fb(v) for v in x])

    def test_watchdog_bypasses_after_overrun(self):
        run = Runner(B5, record('gain'), [50] * 5); x = signal(64)
        run.block(x)
        struct.pack_into('<I', run.mem, 0x8040, 2)                                           # coprocessor still busy
        run.arm.process([(0.0, 0.0)] * 64, run.params, 1)
        self.assertEqual(struct.unpack_from('<I', run.mem, 0x8000)[0], 0); self.assertEqual(struct.unpack_from('<I', run.mem, 0x8040)[0], 0)
        self.assertEqual((run.cell(UERR), run.cell(ENABLE)), (0xff, 0))
        self.assertEqual([fb(v) for v in run.block(x)], [fb(v) for v in x])                 # dry from now on

    def test_other_records_unchanged_from_v4(self):
        x = signal(64 * 8)
        for content in (T3.factory(5), T3.REC3.record(fir=[0.3, -0.2, 0.1] * 50)):
            y5 = Runner(B5, content, [60, 40, 50, 55, 45], ('ftz',)).run(x); y4 = T3.Runner(B4, content, [60, 40, 50, 55, 45]).run(x)
            self.assertEqual(y5.tobytes(), y4.tobytes())


def T3_biquad(block, co, st): return T3_mod.biquad(block, co, st)


import test_ns_capture as T3_mod  # noqa: E402  (float32 biquad model)


if __name__ == '__main__':
    unittest.main()
