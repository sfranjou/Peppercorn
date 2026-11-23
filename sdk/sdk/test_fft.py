"""Own FFT128 and partitioned convolver (sdk/copro/fft.py) in the STRICT simulator: every word an executed form,
no simulator hypotheses. FFT against numpy; convolver against a float64 linear convolution over many blocks."""
import math, struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT), str(ROOT / 'sdk')]
import numpy as np
from sdk.copro import asm, fft
from protocol import copro_sim as cs
fb = lambda v: struct.unpack('<I', struct.pack('<f', float(v)))[0]
ff = lambda b: struct.unpack('<f', struct.pack('<I', b))[0]
CODE, TW = 0x100, 0x800
BUF, HIST, ACC, STATE, ZERO, FDL = 0x400, 0x500, 0x540, 0x5c4, 0x5c5, 0x600


def sim_with(src, extra_p=()):
    words = asm.assemble(src + [('jump', 0xfff)], CODE)
    s = cs.Sim(max_steps=2_000_000); s.load_program(CODE, words); s.load_program(TW, fft.twiddle_table())
    for base, ws in extra_p: s.load_program(base, ws)
    return s, len(words)


class FFT(unittest.TestCase):
    def test_fft128_matches_numpy(self):
        s, n = sim_with(fft.fft128(BUF, TW, 'f'))
        rng = np.random.default_rng(5)
        for trial in range(3):
            z = (rng.uniform(-1, 1, 128) + 1j * rng.uniform(-1, 1, 128)).astype(np.complex64)
            for k in range(128): s.d[BUF + 2 * k] = fb(z[k].real); s.d[BUF + 2 * k + 1] = fb(z[k].imag)
            s.steps = 0; self.assertEqual(s.run(CODE, stop=(CODE + n - 1,)), 'stop')
            out = np.array([ff(s.d[BUF + 2 * k]) + 1j * ff(s.d[BUF + 2 * k + 1]) for k in range(128)])
            ref = np.fft.fft(z.astype(np.complex128))
            self.assertLess(np.max(np.abs(out - ref)) / np.max(np.abs(ref)), 2e-6)
        self.fft_steps = s.steps

    def test_fft128_compact_matches_numpy(self):
        s, n = sim_with(fft.fft128_compact(BUF, TW, 0x5d0, 'f'))
        self.assertLess(n, 110)
        rng = np.random.default_rng(6)
        z = (rng.uniform(-1, 1, 128) + 1j * rng.uniform(-1, 1, 128)).astype(np.complex64)
        for k in range(128): s.d[BUF + 2 * k] = fb(z[k].real); s.d[BUF + 2 * k + 1] = fb(z[k].imag)
        self.assertEqual(s.run(CODE, stop=(CODE + n - 1,)), 'stop')
        out = np.array([ff(s.d[BUF + 2 * k]) + 1j * ff(s.d[BUF + 2 * k + 1]) for k in range(128)])
        ref = np.fft.fft(z.astype(np.complex128))
        self.assertLess(np.max(np.abs(out - ref)) / np.max(np.abs(ref)), 2e-6)

    def run_convolver(self, parts, taps, blocks, seed):
        rng = np.random.default_rng(seed)
        h = rng.uniform(-1, 1, taps) * np.exp(-np.arange(taps) / (taps / 4))
        spectra = [fb(v) for v in fft.filter_spectra(h, parts)]
        SPEC = 0x1000 - len(spectra)
        s, n = sim_with(fft.convolver(0x13, BUF, HIST, FDL, ACC, STATE, SPEC, TW, parts, ZERO, 'c'), [(SPEC, spectra)])
        self.assertLess(CODE + n, TW)
        for i in range(0x13, 0x53): s.d[i] = 0
        for i in list(range(HIST, HIST + 64)) + list(range(FDL, FDL + parts * 130)) + list(range(ACC, ACC + 130)): s.d[i] = 0
        s.d[STATE] = 0; s.d[ZERO] = 0; s.d[BUF:BUF + 256] = [0] * 256
        x = rng.uniform(-0.5, 0.5, 64 * blocks).astype(np.float32); y = []
        for b in range(blocks):
            for i in range(64): s.d[0x13 + i] = fb(x[64 * b + i])
            s.steps = 0; self.assertEqual(s.run(CODE, stop=(CODE + n - 1,)), 'stop')
            y += [ff(s.d[0x13 + i]) for i in range(64)]
        ref = np.convolve(x.astype(np.float64), h)[:len(y)]
        err = np.max(np.abs(np.array(y) - ref)) / np.max(np.abs(ref))
        return err, s.steps, n

    def test_convolver_with_fft_subroutine(self):
        rng = np.random.default_rng(7); parts, taps = 6, 380
        h = rng.uniform(-1, 1, taps) * np.exp(-np.arange(taps) / 90)
        spectra = [fb(v) for v in fft.filter_spectra(h, parts)]; SPEC = 0x1000 - len(spectra)
        src = fft.convolver(0x13, BUF, HIST, FDL, ACC, STATE, SPEC, TW, parts, ZERO, 'c', fft_label='fft') + [('jump', 0xfff), *fft.fft128_subroutine(BUF, TW, 'fft')]
        words = asm.assemble(src, CODE); end = CODE + words.index(asm.assemble([('jump', 0xfff)], 0)[0])
        s = cs.Sim(max_steps=2_000_000); s.load_program(CODE, words); s.load_program(TW, fft.twiddle_table()); s.load_program(SPEC, spectra)
        for i in [*range(0x13, 0x53), *range(HIST, HIST + 64), *range(FDL, FDL + parts * 130), *range(ACC, ACC + 130), STATE, ZERO]: s.d[i] = 0
        x = rng.uniform(-0.5, 0.5, 64 * 14).astype(np.float32); y = []
        for b in range(14):
            for i in range(64): s.d[0x13 + i] = fb(x[64 * b + i])
            s.r[14] = None; self.assertEqual(s.run(CODE, stop=(end,)), 'stop'); y += [ff(s.d[0x13 + i]) for i in range(64)]
        ref = np.convolve(x.astype(np.float64), h)[:len(y)]
        self.assertLess(np.max(np.abs(np.array(y) - ref)) / np.max(np.abs(ref)), 2e-5)
        self.assertLess(len(words), 400)

    def test_convolver_partition_count_from_cells(self):
        rng = np.random.default_rng(9)
        for parts, taps in ((3, 170), (6, 384)):
            h = rng.uniform(-1, 1, taps) * np.exp(-np.arange(taps) / 80)
            spectra = [fb(v) for v in fft.filter_spectra(h, 6)]; SPEC = 0x1000 - len(spectra)   # area sized for 6
            PC, SC = 0x5c6, 0x5c7
            src = fft.convolver(0x13, BUF, HIST, FDL, ACC, STATE, SPEC, TW, ('cells', PC, SC), ZERO, 'c', fft_label='fft') + [('jump', 0xfff), *fft.fft128_subroutine(BUF, TW, 'fft', cells=0x5d0)]
            words = asm.assemble(src, CODE); end = CODE + words.index(asm.assemble([('jump', 0xfff)], 0)[0])
            s = cs.Sim(max_steps=2_000_000); s.load_program(CODE, words); s.load_program(TW, fft.twiddle_table()); s.load_program(SPEC, spectra)
            for i in [*range(0x13, 0x53), *range(HIST, HIST + 64), *range(FDL, FDL + 6 * 130), *range(ACC, ACC + 130), STATE, ZERO]: s.d[i] = 0
            s.d[PC] = parts; s.d[SC] = parts * 130
            x = rng.uniform(-0.5, 0.5, 64 * 12).astype(np.float32); y = []
            for b in range(12):
                for i in range(64): s.d[0x13 + i] = fb(x[64 * b + i])
                s.r[14] = None; self.assertEqual(s.run(CODE, stop=(end,)), 'stop'); y += [ff(s.d[0x13 + i]) for i in range(64)]
            h6 = np.concatenate([h, np.zeros(6 * 64 - taps)])[:parts * 64]   # only the first `parts` partitions are used
            ref = np.convolve(x.astype(np.float64), h6)[:len(y)]
            self.assertLess(np.max(np.abs(np.array(y) - ref)) / np.max(np.abs(ref)), 2e-5, parts)

    def test_convolver_matches_linear_convolution(self):
        for parts, taps, blocks in ((1, 64, 6), (4, 250, 12), (8, 512, 20), (11, 704, 26)):
            err, steps, n = self.run_convolver(parts, taps, blocks, parts)
            self.assertLess(err, 2e-5, (parts, taps, err))
            print(f'\n  convolver P={parts} ({taps} taps): rel err {err:.1e}, {steps} steps/block, {n} program words', end='')


if __name__ == '__main__':
    unittest.main()
