"""Build a GP5N v1 content record for NS Basic (the N->S slot's 2,696 bytes; layout in ns_basic.c).

record(drive, bias, level, pre=(b_a, b_b), post=(b_a, b_b), fir=[h0, h1, ...]) -> bytes
Each biquad is (b0, b1, b2, a1, a2) with a0 = 1. Up to 128 FIR taps. Zero-padded to 2,696 bytes so it
fits the stock upload framing (work/tone_capture/upload_path_017/build_snaptone_upload.py).
"""
import struct

SIZE, FIR_MAX, MAGIC = 2696, 128, b'GP5N'
FLAT = (1.0, 0.0, 0.0, 0.0, 0.0)


def record(drive=1.0, bias=0.0, level=1.0, pre=(FLAT, FLAT), post=(FLAT, FLAT), fir=()):
    fir = list(fir)
    if len(fir) > FIR_MAX: raise ValueError(f'at most {FIR_MAX} FIR taps')
    if not -1.0 <= bias <= 1.0: raise ValueError('bias in [-1, 1]')
    out = MAGIC + struct.pack('<II3f', 1, 0, drive, bias, level)
    for b in (*pre, *post):
        if len(b) != 5: raise ValueError('biquads are (b0, b1, b2, a1, a2)')
        out += struct.pack('<5f', *b)
    out += struct.pack('<I', len(fir)) + struct.pack(f'<{FIR_MAX}f', *(fir + [0.0] * (FIR_MAX - len(fir))))
    assert len(out) == 108 + 4 * FIR_MAX
    return out + bytes(SIZE - len(out))
