"""Build a GP5N v2 content record for NS Capture (2,696 bytes; layout in ns_capture.c).

record(drive, bias, level, pre=(b_a, b_b), post=(b_a, b_b), fir=[h0, h1, ...]) -> bytes. Biquads (b0, b1, b2, a1, a2),
a0 = 1. Up to TAPS_MAX FIR taps, stored as int16 with one float scale (peak tap -> 32767): about -90 dB error.
An empty fir means a unit impulse. Fits the stock upload framing (upload_path_017/build_snaptone_upload.py)."""
import struct

SIZE, MAGIC, TAPS_MAX = 2696, b'GP5N', 704
FLAT = (1.0, 0.0, 0.0, 0.0, 0.0)


def record(drive=1.0, bias=0.0, level=1.0, pre=(FLAT, FLAT), post=(FLAT, FLAT), fir=()):
    fir = [float(v) for v in fir]
    if len(fir) > TAPS_MAX: raise ValueError(f'at most {TAPS_MAX} taps')
    if not -1.0 <= bias <= 1.0: raise ValueError('bias in [-1, 1]')
    peak = max((abs(v) for v in fir), default=0.0) or 1.0
    q = [max(-32768, min(32767, round(v / peak * 32767))) for v in fir]
    out = MAGIC + struct.pack('<II3f', 2, 0, drive, bias, level)
    for b in (*pre, *post):
        if len(b) != 5: raise ValueError('biquads are (b0, b1, b2, a1, a2)')
        out += struct.pack('<5f', *b)
    out += struct.pack('<If', len(fir), peak * 32768 / 32767) + struct.pack(f'<{len(q)}h', *q)
    return out + bytes(SIZE - len(out))


def taps(rec):
    """Decode the stored taps exactly as the ARM init does (float32 scale * q / 32768)."""
    n, scale = struct.unpack_from('<If', rec, 104)
    s = struct.unpack('<f', struct.pack('<f', scale * (1.0 / 32768)))[0]
    return [struct.unpack('<f', struct.pack('<f', s * q))[0] for q in struct.unpack_from(f'<{n}h', rec, 112)]
