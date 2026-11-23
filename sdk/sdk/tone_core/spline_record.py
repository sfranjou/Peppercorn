"""GPTC v2 ("GPTS"): two-spline compact capture record (2,696 bytes, the stock N->S upload size). Offline encoder/validator.

Model (scripts/tone_capture/spline_modules_20261109.py, SplineModel count=2): input gain -> PRE32 -> 4x interpolation
-> spline 1 -> INTER16 (at 4x) -> spline 2 -> fixed shared LPF40 decimator (phase 3) -> fixed biquad -> POST256.
Each spline: 33 fixed knots KNOTS (sinh-spaced, centre 0), ordinates V, linear interpolation with linear tails.

Folding (exact in real arithmetic, applied by the exporter): spline input gains go into PRE / INTER taps, spline
output gains into the ordinates, and the centre ordinate is subtracted (V[16] = 0). The record therefore carries plain
ordinates; the fixed LPF40/biquad are not stored (the player writes its own copies, identical to GPTC's).

Header 12 u32 words: magic 'GPTC', version 2 (GPTC v1 is the original compact capture; the resident accepts both by
magic, the player selects by version), size 2696, knots 33, pre 32, inter 16, post 256, reserved 0, reserved 0,
input gain (f32), output gain (f32), FNV-1a over the whole record except the checksum word (as GPTC).
Payload (f32 little-endian): PRE reversed @48 (32), INTER reversed @176 (16), V1 @240 (33), V2 @372 (33),
POST spectra @504 (4 partitions x 130 floats, /128, as GPTC). Zero padding @2584..2696.

Evaluation contract shared by the DSP kernel, the ARM init and sdk/tone_core/capture_spline.c (all binary32,
no fused multiply-add):
  segment p = largest j in 1..31 with KNOTS[j] < z, else 0 (binary search: p=0; for s in 16,8,4,2,1: if KNOTS[p+s] < z: p+=s)
  B[p] = (V[p+1] - V[p]) * INV_DK[p];  A[p] = V[p] - KNOTS[p] * B[p];  y = A[p] + z * B[p]
"""
import math
import struct

SIZE = 2696
MAGIC = b'GPTC'
VERSION = 2
OFFSETS = dict(PRE=48, INTER=176, V1=240, V2=372, SPEC=504, END=2584)
KNOT_BITS = (0xc1800000, 0xc14e0567, 0xc125c07f, 0xc1054b6a, 0xc0d63d18, 0xc0abfc30, 0xc089d653, 0xc05c5ef7,
             0xc02f741a, 0xc00ace1d, 0xbfd965ac, 0xbfa76e0c, 0xbf7ab4fe, 0xbf325eb6, 0xbee4e0fd, 0xbe5f9c0c, 0x0,
             0x3e5f9c0c, 0x3ee4e0fd, 0x3f325eb6, 0x3f7ab4fe, 0x3fa76e0c, 0x3fd965ac, 0x400ace1d, 0x402f741a,
             0x405c5ef7, 0x4089d653, 0x40abfc30, 0x40d63d18, 0x41054b6a, 0x4125c07f, 0x414e0567, 0x41800000)
f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
bits = lambda x: struct.unpack('<I', struct.pack('<f', x))[0]
KNOTS = [struct.unpack('<f', struct.pack('<I', b))[0] for b in KNOT_BITS]   # torch float32 sinh knots, exactly
INV_DK = [f32(1.0 / f32(KNOTS[p + 1] - KNOTS[p])) for p in range(32)]      # fixed, rounded once to binary32
LIMIT = 1e6


def checksum(raw):
    h = 2166136261
    for byte in raw[:44] + raw[48:]:
        h = ((h ^ byte) * 16777619) & 0xffffffff
    return h


def encode(pre, inter, v1, v2, spectra, input_gain=.5, output_gain=1.25594995):
    """pre/inter in natural order (tap 0 newest), v1/v2 with 33 ordinates each (centre forced to 0)."""
    assert len(pre) == 32 and len(inter) == 16 and len(v1) == 33 and len(v2) == 33 and len(spectra) == 520
    out = bytearray(SIZE)
    struct.pack_into('<4s8I2f', out, 0, MAGIC, VERSION, SIZE, 33, 32, 16, 256, 0, 0, input_gain, output_gain)
    v1 = list(map(float, v1)); v2 = list(map(float, v2)); v1[16] = v2[16] = 0.0
    for name, seq in dict(PRE=list(pre)[::-1], INTER=list(inter)[::-1], V1=v1, V2=v2, SPEC=spectra).items():
        seq = list(map(float, seq))
        assert all(math.isfinite(x) and abs(x) <= LIMIT for x in seq), name
        struct.pack_into('<%df' % len(seq), out, OFFSETS[name], *seq)
    struct.pack_into('<I', out, 44, checksum(out))
    validate(out)
    return bytes(out)


def validate(raw):
    if len(raw) != SIZE or raw[:4] != MAGIC: raise ValueError('GPTC v2 size/magic')
    if struct.unpack_from('<8I', raw, 4) != (VERSION, SIZE, 33, 32, 16, 256, 0, 0): raise ValueError('GPTC v2 geometry/version')
    if struct.unpack_from('<I', raw, 44)[0] != checksum(raw): raise ValueError('GPTC v2 checksum')
    ig, og = struct.unpack_from('<2f', raw, 36)
    if not (math.isfinite(ig) and math.isfinite(og) and 0 <= ig <= 4 and 0 <= og <= 8): raise ValueError('GPTC v2 scalars')
    values = struct.unpack_from('<%df' % ((OFFSETS['END'] - 48) // 4), raw, 48)
    if not all(math.isfinite(x) and abs(x) <= LIMIT for x in values): raise ValueError('GPTC v2 coefficients')
    if struct.unpack_from('<f', raw, OFFSETS['V1'] + 64)[0] != 0 or struct.unpack_from('<f', raw, OFFSETS['V2'] + 64)[0] != 0:
        raise ValueError('GPTC v2 centre ordinate')
    if any(raw[OFFSETS['END']:]): raise ValueError('GPTC v2 padding')
    return True


def decode(raw):
    validate(raw)
    g = lambda name, n: list(struct.unpack_from('<%df' % n, raw, OFFSETS[name]))
    ig, og = struct.unpack_from('<2f', raw, 36)
    return dict(pre=g('PRE', 32)[::-1], inter=g('INTER', 16)[::-1], v1=g('V1', 33), v2=g('V2', 33),
                spectra=g('SPEC', 520), input_gain=ig, output_gain=og)


def segments(v):
    """(A, B) per segment, binary32, the order of operations in the contract above."""
    A, B = [], []
    for p in range(32):
        b = f32(f32(v[p + 1] - v[p]) * INV_DK[p])
        A.append(f32(v[p] - f32(KNOTS[p] * b))); B.append(b)
    return A, B


def fixed_filters():
    """The fixed shared LPF40 (natural order) and biquad of every GPTC/GPTS capture, as binary32."""
    import json
    from pathlib import Path
    fixed = json.loads((Path(__file__).resolve().parents[2] / 'tools/tone_trainer/fixed_filters.json').read_text())
    return [f32(x) for x in fixed['lpf']], [f32(x) for x in fixed['biquad']]


def c_tables():
    """C initialisers for the fixed tables (sdk/tone_core/spline_tables.h)."""
    row = lambda xs: ',\n '.join(', '.join('0x%08xu' % bits(x) for x in xs[i:i + 6]) for i in range(0, len(xs), 6))
    return ('/* Generated by sdk/tone_core/spline_record.py c_tables(): GPTC v2 two-spline fixed tables as binary32 bit patterns. */\n'
            '#define GPTS_KNOT_BITS {\\\n ' + row(KNOTS).replace('\n', '\\\n') + '}\n'
            '#define GPTS_INV_DK_BITS {\\\n ' + row(INV_DK).replace('\n', '\\\n') + '}\n'
            '/* Fixed shared LPF40 in DSP cell order (reversed, as GPTC records store it) and biquad b0 b1 b2 a1 a2. */\n'
            '#define GPTS_LPF_CELL_BITS {\\\n ' + row(fixed_filters()[0][::-1]).replace('\n', '\\\n') + '}\n'
            '#define GPTS_BQ_BITS {\\\n ' + row(fixed_filters()[1]).replace('\n', '\\\n') + '}\n')


if __name__ == '__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name('spline_tables.h')).write_text(c_tables())
