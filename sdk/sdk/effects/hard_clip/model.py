"""Float32 model of the ARM half of Hard Clip: knob values -> coprocessor cell bit patterns."""
import struct
r32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
GAIN_CURVE,LIMIT=r32(0.0049),r32(0.05)


def cells(gain_knob,vol_knob,enable=1):
    """dict cell name -> 32-bit value, as hard_clip.c computes them (each step rounded to float32)."""
    g=r32(gain_knob);v=r32(r32(vol_knob)*r32(0.02))
    return dict(ENABLE=1 if enable else 0,GAIN=bits(r32(1.0+r32(r32(g*g)*GAIN_CURVE))),LIMIT=bits(LIMIT),NLIMIT=bits(-LIMIT),LEVEL=bits(r32(v*v)))
