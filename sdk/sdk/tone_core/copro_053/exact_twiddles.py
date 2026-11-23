"""Research-owned table refinement; shared SDK remains unchanged.

cos(pi/2) and cos(3pi/2) are mathematically zero. Generic libm cos leaves
~1e-16 residuals that multiply tiny decay FFT residuals into denormals. Keep
the qualified SDKcode and all other table words, but encode these two as0.
This changes table data, so requalify numerical/state tests; no bitparity claim.
"""
from sdk.copro.fft import twiddle_table as _original_table

def exact_cardinal_table():
    words=_original_table()
    words[32]=0;words[96]=0
    return words
