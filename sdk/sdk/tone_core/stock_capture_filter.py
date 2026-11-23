"""Generate the spline runtime's LPF definition from decoded GP-50 V1.1.0 region G."""
import struct


def lpf_header(region_g):
    # SDK build verifies the stock container before passing its decoded region here.
    cell_words = struct.unpack_from('<40I', region_g, 50768)
    taps = [cell_words[i ^ 3] for i in range(len(cell_words))]
    taps.reverse()
    rows = [', '.join(f'0x{word:08x}u' for word in taps[i:i + 6])
            for i in range(0, len(taps), 6)]
    return ('#define GPTS_LPF_CELL_BITS {\\\n ' + ',\\\n '.join(rows) + '}\n').encode()
