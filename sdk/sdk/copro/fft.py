"""Own FFT and partitioned FIR convolution for coprocessor programs (item 6, analysis/firmware/NS_SLOT.md).

Pure source generators for sdk/copro/asm.py, using only forms executed on the pedal (program-memory loads, bit
reverse, shifts, compare-skip: COPRO_EXPERIMENTS.md i_fft_*). Written from scratch; the stock N->S convolver
was only used to learn the instruction set.

fft128(buf, tw, name)       in-place radix-2 DIT FFT of 128 complex values at D[buf..buf+255] (re, im
                            interleaved), forward sign e^(-i...), natural order out. Twiddles: program memory
                            P[tw..tw+159] = cos(2*pi*n/128), n = 0..159 (twiddle_table()). Uses r0..r13.
convolver(...)              uniformly partitioned overlap-save FIR, 64-sample partitions, zero latency:
                            y = h * x for up to P*64 taps on the 64-sample window, in place.
The ARM side provides the filter spectra (filter_spectra()): H_p = FFT128([h_p, 0*64]) / 128, bins 0..64,
re/im interleaved, P * 130 words, in program memory at `spectra` (read with P[r++]).
"""
import math, struct

N, HALF, BINS = 128, 64, 65


def twiddle_table():
    """160 float32 words cos(2*pi*n/128): sin(t_k) = cos(t_{k+96})."""
    return [struct.unpack('<I', struct.pack('<f', math.cos(2 * math.pi * n / N)))[0] for n in range(160)]


def _bitreverse(buf, name):
    """Swap x[i] <-> x[bitrev7(i)] for i < bitrev7(i). Uses r0..r6."""
    return [('li', 0, N), ('li', 1, 0),
            name + ':',
            ('bitrev', 2, 1, 7),
            ('skip_ge', 1, 2, 1),                  # i >= j: skip the jump into the swap
            ('jump', name + '_swap'),
            ('jump', name + '_next'),
            name + '_swap:',
            ('shl', 3, 1, 1), ('addi', 3, buf), ('shl', 4, 2, 1), ('addi', 4, buf),
            ('load_ind', 5, 3), ('load_ind', 6, 4), ('store_ind', 3, 6), ('store_ind', 4, 5),
            ('addi', 3, 1), ('addi', 4, 1),
            ('load_ind', 5, 3), ('load_ind', 6, 4), ('store_ind', 3, 6), ('store_ind', 4, 5),
            name + '_next:',
            ('addi', 1, 1),
            ('loop', 0, name)]


def _stage(buf, tw, s, name):
    """One radix-2 stage, butterflies of span 2^s. r0 j counter, r1 twiddle pointer, r2 group base,
    r3 group counter, r4 a pointer, r5 b pointer, r6..r13 values."""
    half = 1 << s; m = 2 * half; step = N >> (s + 1)
    return [('li', 0, half), ('li', 1, tw), ('li', 2, buf),
            name + '_j:',
            ('pload', 10, 1),                       # wr = cos(2 pi j step / 128)
            ('addi', 1, 96), ('pload', 11, 1), ('subi', 1, 96),   # s = sin(...)
            ('mov', 4, 2), ('mov', 5, 2), ('addi', 5, 2 * half),
            ('li', 3, N // m),
            name + '_k:',
            ('load_inc', 8, 5), ('load_ind', 9, 5),               # b = br, bi (r5 -> bi)
            ('fmul', 12, 10, 8), ('fmac', 12, 11, 9),             # tr = wr br + s bi
            ('fmul', 13, 10, 9), ('fmul', 9, 11, 8), ('fsub', 8, 13, 9),   # ti = wr bi - s br
            ('load_inc', 6, 4), ('load_ind', 7, 4),               # a = ar, ai (r4 -> ai)
            ('fsub', 9, 6, 12), ('fsub', 13, 7, 8),               # b' = a - t
            ('store_ind', 5, 13), ('subi', 5, 1), ('store_ind', 5, 9),
            ('fadd', 9, 6, 12), ('fadd', 13, 7, 8),               # a' = a + t
            ('store_ind', 4, 13), ('subi', 4, 1), ('store_ind', 4, 9),
            ('addi', 4, 2 * m), ('addi', 5, 2 * m),
            ('loop', 3, name + '_k'),
            ('addi', 2, 2), ('addi', 1, step),
            ('loop', 0, name + '_j')]


def fft128(buf, tw, name):
    src = _bitreverse(buf, name + '_br')
    for s in range(7): src += _stage(buf, tw, s, f'{name}_s{s}')
    return src


def fft128_compact(buf, tw, cells, name):
    """fft128 with ONE stage body run 7 times (~80 words instead of ~275): per-stage values live in 6 data cells
    cells..cells+5 (HALF, BOFF = 2 half, STRIDE = 4 half, GRP = groups = twiddle step, TWP, STG). Uses r0..r13."""
    HALF_, BOFF, STRIDE, GRP, TWP, STG = range(cells, cells + 6)
    return _bitreverse(buf, name + '_br') + [
        ('li', 3, 1), ('store', 3, HALF_), ('li', 3, 2), ('store', 3, BOFF), ('li', 3, 4), ('store', 3, STRIDE),
        ('li', 3, N // 2), ('store', 3, GRP), ('li', 3, 7),
        name + '_s:', ('store', 3, STG),
        ('load', 0, HALF_), ('li', 1, tw), ('li', 2, buf),
        name + '_j:',
        ('pload', 10, 1), ('addi', 1, 96), ('pload', 11, 1), ('subi', 1, 96), ('store', 1, TWP),
        ('mov', 4, 2), ('mov', 5, 2), ('load', 3, BOFF), ('iadd', 5, 5, 3),
        ('load', 1, STRIDE), ('load', 3, GRP),
        name + '_k:',
        ('load_inc', 8, 5), ('load_ind', 9, 5),
        ('fmul', 12, 10, 8), ('fmac', 12, 11, 9),
        ('fmul', 13, 10, 9), ('fmul', 9, 11, 8), ('fsub', 8, 13, 9),
        ('load_inc', 6, 4), ('load_ind', 7, 4),
        ('fsub', 9, 6, 12), ('fsub', 13, 7, 8),
        ('store_ind', 5, 13), ('subi', 5, 1), ('store_ind', 5, 9),
        ('fadd', 9, 6, 12), ('fadd', 13, 7, 8),
        ('store_ind', 4, 13), ('subi', 4, 1), ('store_ind', 4, 9),
        ('iadd', 4, 4, 1), ('iadd', 5, 5, 1),
        ('loop', 3, name + '_k'),
        ('load', 1, TWP), ('addi', 2, 2), ('load', 3, GRP), ('iadd', 1, 1, 3),
        ('loop', 0, name + '_j'),
        ('load', 3, HALF_), ('shl', 3, 3, 1), ('store', 3, HALF_),
        ('load', 3, BOFF), ('shl', 3, 3, 1), ('store', 3, BOFF),
        ('load', 3, STRIDE), ('shl', 3, 3, 1), ('store', 3, STRIDE),
        ('load', 3, GRP), ('li', 6, 1), ('ishr', 3, 3, 6), ('store', 3, GRP),
        ('load', 3, STG), ('loop', 3, name + '_s'),
    ]


def _radix4_first(buf, name):
    """Stages 0 and 1 of the DIT FFT fused into one radix-4 pass over the bit-reversed buffer (2026-11-08).

    Their twiddles are 1 (stage 0) and 1, -i (stage 1): t = -i b = (bi, -br). No multiply, no twiddle load,
    no intermediate store. Every float operation has the same operands as the general butterfly with an
    exact-cardinal twiddle table (cos = 0 / 1 exactly), so results equal fft128_compact's except possibly the
    sign of an exact zero. 33 words per 4 points. Uses r0..r11, r13."""
    return [('li', 0, N // 4), ('li', 1, buf), ('li', 13, buf),
            name + ':',
            ('load_inc', 2, 1), ('load_inc', 3, 1), ('load_inc', 4, 1), ('load_inc', 5, 1),   # p0, p1
            ('load_inc', 6, 1), ('load_inc', 7, 1), ('load_inc', 8, 1), ('load_inc', 9, 1),   # p2, p3
            ('fadd', 10, 2, 4), ('fsub', 11, 2, 4),        # a0r, a1r
            ('fadd', 2, 3, 5), ('fsub', 4, 3, 5),          # a0i, a1i
            ('fadd', 3, 6, 8), ('fsub', 5, 6, 8),          # a2r, a3r
            ('fadd', 6, 7, 9), ('fsub', 8, 7, 9),          # a2i, a3i
            ('fadd', 7, 10, 3), ('fadd', 9, 2, 6), ('store_inc', 13, 7), ('store_inc', 13, 9),   # y0 = a0 + a2
            ('fadd', 7, 11, 8), ('fsub', 9, 4, 5), ('store_inc', 13, 7), ('store_inc', 13, 9),   # y1 = a1 - i a3
            ('fsub', 7, 10, 3), ('fsub', 9, 2, 6), ('store_inc', 13, 7), ('store_inc', 13, 9),   # y2 = a0 - a2
            ('fsub', 7, 11, 8), ('fadd', 9, 4, 5), ('store_inc', 13, 7), ('store_inc', 13, 9),   # y3 = a1 + i a3
            ('loop', 0, name)]


def _last_stage(buf, tw, name, tw_data=False):
    """Stage 6 (span 64, one group, twiddle step 1) as a single 64-butterfly loop (2026-11-08). The general stage body
    pays its per-twiddle overhead 64 times here; with step 1 both twiddle pointers auto-increment and the b half is
    read and written through contiguous pointers. Float operations, operands and order equal the general butterfly
    (tr = wr br + s bi; ti = wr bi - s br; b' = a - t; a' = a + t), so results are bit-identical. Uses r0..r13."""
    return [('li', 0, HALF), ('li', 1, tw), ('li', 2, tw + 96), ('li', 4, buf), ('li', 5, buf + N), ('li', 3, buf + N),
            name + ':',
            (('load_inc' if tw_data else 'pload_inc'), 10, 1), (('load_inc' if tw_data else 'pload_inc'), 11, 2),   # wr, s
            ('load_inc', 8, 5), ('load_inc', 9, 5),                    # br, bi
            ('fmul', 12, 10, 8), ('fmac', 12, 11, 9),                  # tr
            ('fmul', 13, 10, 9), ('fmul', 9, 11, 8), ('fsub', 8, 13, 9),   # ti
            ('load_inc', 6, 4), ('load_ind', 7, 4),                    # ar, ai (r4 -> ai)
            ('fsub', 9, 6, 12), ('fsub', 13, 7, 8),                    # b' = a - t
            ('store_inc', 3, 9), ('store_inc', 3, 13),
            ('fadd', 9, 6, 12), ('fadd', 13, 7, 8),                    # a' = a + t
            ('store_ind', 4, 13), ('subi', 4, 1), ('store_ind', 4, 9), ('addi', 4, 2),
            ('loop', 0, name)]


def fft128_fast(buf, tw, cells, name, tw_data=False):
    """fft128_compact with stages 0 and 1 replaced by _radix4_first and stage 6 by _last_stage; stages 2..5 run the
    same compact stage body (cells as fft128_compact). Same transform, same twiddle table, same data/register
    footprint (r0..r13). tw_data=True: the 160-word table is in DATA memory at D[tw..tw+159] (load instead of
    program-memory load; same values, same instruction count)."""
    HALF_, BOFF, STRIDE, GRP, TWP, STG = range(cells, cells + 6)
    compact = fft128_compact(buf, tw, cells, name)
    stage_start = compact.index(name + '_s:')
    stage_body = compact[stage_start:]
    if tw_data:
        stage_body = [('load_ind',) + it[1:] if isinstance(it, tuple) and it[0] == 'pload' else it for it in stage_body]
    return _bitreverse(buf, name + '_br') + _radix4_first(buf, name + '_r4') + [
        ('li', 3, 4), ('store', 3, HALF_), ('li', 3, 8), ('store', 3, BOFF), ('li', 3, 16), ('store', 3, STRIDE),
        ('li', 3, N // 8), ('store', 3, GRP), ('li', 3, 4),
    ] + stage_body + _last_stage(buf, tw, name + '_s6', tw_data)


def fft128_subroutine(buf, tw, label, cells=None, fast=False, tw_data=False):
    """fft128 as a one-level subroutine (('call', label) with frame.check(..., allow_calls=True)).
    fast=True (cells required) uses fft128_fast: same results, ~21 % fewer instructions, 64 more program words.
    tw_data=True (fast only): twiddle table in data memory at D[tw..]."""
    if fast and cells is None:raise ValueError('fast FFT needs the compact stage cells')
    if tw_data and not fast:raise ValueError('data-memory twiddles are implemented for the fast FFT only')
    body = (fft128_fast(buf, tw, cells, label + '_b', tw_data) if fast else fft128_compact(buf, tw, cells, label + '_b')) if cells is not None else fft128(buf, tw, label + '_b')
    return [label + ':', *body, ('ret',)]


def convolver(window, buf, hist, fdl, acc, state, spectra, tw, parts, zero, name, fft_label=None, fast_mac=False):
    """Overlap-save partitioned FIR on D[window..window+63], in place, zero latency.
    Cells: buf 256 (FFT work), hist 64 (previous input block), fdl parts*130 (input spectra, circular),
    acc 130 (spectrum accumulator), state 1 (FDL write offset in words, integer, 0 at init), zero 1 (0.0).
    Program memory: spectra parts*130 words (filter spectra / 128, filter_spectra()), tw 160 (twiddle_table()).
    parts: an int, or ('cells', PARTS_CELL, SPAN_CELL) to read the partition count and parts*130 from data cells at
    run time (one program for records with different filter lengths; FDL/spectra areas sized for the maximum).
    fast_mac=True (2026-11-08; run-time partition counts too since the MOD146 follow-up): partition 0 writes the accumulator directly (no clearing loop, no
    accumulator reads; adding to 0 is exact, so only the sign of an exact zero can differ) and the other partitions use
    separate accumulator read/write pointers (r2/r12; r12 holds the FDL base only around the wrap). Same float
    operations, operands and order: results equal the default except for zero signs. ~1,150 fewer steps per block at
    12 partitions."""
    dyn = isinstance(parts, tuple)
    # spectra: a program address, or ('cell', CELL) to read the spectra address from a data cell at run time (2026-11-08,
    # capture pair mode: the same program reads its spectra from 0x7e8 or above the pair code).
    spec_load = ('load', 5, spectra[1]) if isinstance(spectra, tuple) else ('li', 5, spectra)
    span = None if dyn else parts * 2 * BINS
    load_parts = ('load', 3, parts[1]) if dyn else ('li', 3, parts)
    wrap = [('load', 13, parts[2]), ('iadd', 13, 4, 13), ('skip_ge', 4, 12, 1), ('mov', 4, 13)] if dyn else [('skip_ge', 4, 12, 1), ('addi', 4, span)]
    load_span = ('load', 1, parts[2]) if dyn else ('li', 1, span)
    return [
        # 1. buf = [hist, window] as complex, imaginary parts 0; hist = window
        ('li', 0, HALF), ('li', 1, hist), ('li', 2, buf), ('load', 7, zero),
        name + '_in0:', ('load_inc', 6, 1), ('store_inc', 2, 6), ('store_inc', 2, 7), ('loop', 0, name + '_in0'),
        ('li', 0, HALF), ('li', 1, window), ('li', 3, hist),
        name + '_in1:', ('load_inc', 6, 1), ('store_inc', 2, 6), ('store_inc', 2, 7), ('store_inc', 3, 6), ('loop', 0, name + '_in1'),
        *([('call', fft_label)] if fft_label else fft128(buf, tw, name + '_f')),
        # 2. fdl[slot] = X[0..64]; slot pointer r4 = fdl + state
        ('load', 4, state), ('addi', 4, fdl), ('li', 9, buf), ('li', 10, 2 * BINS), ('mov', 11, 4), ('block', 'copy'),
        *(_mac_fast(fdl, acc, spec_load, parts, span, name, wrap) if fast_mac else [
        # 3. acc = 0
        ('li', 0, 2 * BINS), ('li', 1, acc), ('load', 7, zero),
        name + '_z:', ('store_inc', 1, 7), ('loop', 0, name + '_z'),
        # 4. acc += fdl[slot - p] * H_p, p = 0..parts-1 (r4 walks back one slot per partition, wraps below fdl)
        load_parts, spec_load, ('li', 12, fdl),
        name + '_p:',
        ('li', 0, BINS), ('mov', 1, 4), ('li', 2, acc),
        name + '_b:',
        ('load_inc', 6, 1), ('load_inc', 7, 1),                  # xr, xi
        ('pload_inc', 8, 5), ('pload_inc', 9, 5),                # hr, hi
        ('load_inc', 10, 2), ('load_ind', 11, 2), ('subi', 2, 1),   # yr, yi (r2 back on yr)
        ('fmac', 11, 6, 9), ('fmac', 11, 7, 8),                  # yi += xr hi + xi hr
        ('fmac', 10, 6, 8), ('fmul', 13, 7, 9), ('fsub', 8, 10, 13),   # yr += xr hr - xi hi
        ('store_inc', 2, 8), ('store_inc', 2, 11),
        ('loop', 0, name + '_b'),
        ('subi', 4, 2 * BINS),
        *wrap,
        ('loop', 3, name + '_p')]),
        # 5. buf = [conj(Y[0..64]), Y[63..1] mirrored]: FFT(conj Y) has the real part of 128 * IFFT(Y)
        ('li', 0, BINS), ('li', 1, acc), ('li', 2, buf),
        name + '_m0:', ('load_inc', 6, 1), ('load_inc', 7, 1), ('neg', 7), ('store_inc', 2, 6), ('store_inc', 2, 7), ('loop', 0, name + '_m0'),
        ('li', 0, HALF - 1), ('li', 1, acc + 2), ('li', 2, buf + 2 * (N - 1)),
        name + '_m1:', ('load_inc', 6, 1), ('load_inc', 7, 1), ('store_inc', 2, 6), ('store_ind', 2, 7), ('subi', 2, 3), ('loop', 0, name + '_m1'),
        *([('call', fft_label)] if fft_label else fft128(buf, tw, name + '_i')),
        # 6. window = Re(buf[64..127]) (overlap-save: the second half is the linear convolution)
        ('li', 0, HALF), ('li', 1, buf + 2 * HALF), ('li', 2, window),
        name + '_o:', ('load_inc', 6, 1), ('addi', 1, 1), ('store_inc', 2, 6), ('loop', 0, name + '_o'),
        # 7. state += 130, wrapping to 0 at parts * 130
        ('load', 0, state), ('addi', 0, 2 * BINS), load_span,
        ('skip_ge', 0, 1, 1), ('jump', name + '_st'), ('li', 0, 0),
        name + '_st:', ('store', 0, state),
    ]


def _mac_fast(fdl, acc, spec_load, parts, span, name, wrap):
    """Steps 3+4 of convolver(fast_mac=True). Partition 0: acc = X_slot * H_0 written directly. Partitions 1..: acc +=
    with read pointer r2 and write pointer r12 (r12 = FDL base again before each wrap check). A run-time count
    (parts = ('cells', PARTS, SPAN)) loads PARTS - 1 and skips the remaining partitions when PARTS < 2."""
    dyn = isinstance(parts, tuple)
    first = [('li', 0, BINS), ('mov', 1, 4), ('li', 2, acc), spec_load,
             name + '_b0:',
             ('load_inc', 6, 1), ('load_inc', 7, 1),                  # xr, xi
             ('pload_inc', 8, 5), ('pload_inc', 9, 5),                # hr, hi
             ('fmul', 11, 6, 9), ('fmac', 11, 7, 8),                  # yi = xr hi + xi hr   (was 0 + ... + ...)
             ('fmul', 10, 6, 8), ('fmul', 13, 7, 9), ('fsub', 8, 10, 13),   # yr = xr hr - xi hi  (was (0 + xr hr) - xi hi)
             ('store_inc', 2, 8), ('store_inc', 2, 11),
             ('loop', 0, name + '_b0'),
             ('subi', 4, 2 * BINS), ('li', 12, fdl), *wrap]
    if parts == 1:
        return first
    count = [('load', 3, parts[1]), ('li', 13, 2), ('skip_ge', 3, 13, 1), ('jump', name + '_pend'), ('subi', 3, 1)] \
        if dyn else [('li', 3, parts - 1)]
    return first + count + [
        name + '_p:',
        ('li', 0, BINS), ('mov', 1, 4), ('li', 2, acc), ('li', 12, acc),
        name + '_b:',
        ('load_inc', 6, 1), ('load_inc', 7, 1),                      # xr, xi
        ('pload_inc', 8, 5), ('pload_inc', 9, 5),                    # hr, hi
        ('load_inc', 10, 2), ('load_inc', 11, 2),                    # yr, yi (read pointer r2)
        ('fmac', 11, 6, 9), ('fmac', 11, 7, 8),                      # yi += xr hi + xi hr
        ('fmac', 10, 6, 8), ('fmul', 13, 7, 9), ('fsub', 8, 10, 13),   # yr += xr hr - xi hi
        ('store_inc', 12, 8), ('store_inc', 12, 11),                 # write pointer r12
        ('loop', 0, name + '_b'),
        ('subi', 4, 2 * BINS), ('li', 12, fdl), *wrap,
        ('loop', 3, name + '_p'),
        *([name + '_pend:'] if dyn else [])]


def filter_spectra(h, parts):
    """Host model of the ARM-side preparation: H_p = FFT128([h_p (64 taps), 0*64]) / 128, bins 0..64 interleaved."""
    import numpy as np
    h = np.asarray(h, dtype=np.float64); h = np.concatenate([h, np.zeros(parts * HALF - len(h))])
    out = []
    for p in range(parts):
        X = np.fft.fft(np.concatenate([h[p * HALF:(p + 1) * HALF], np.zeros(HALF)])) / N
        out += [v for k in range(BINS) for v in (X[k].real, X[k].imag)]
    return out
