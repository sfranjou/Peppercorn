"""Bit-exact float32 reference model of chop_trem.c (one IEEE binary32 operation per step,
in source order; the build uses -ffp-contract=off so the overlay does the same)."""
import struct


def f32(x):
    return struct.unpack('<f',struct.pack('<f',x))[0]


class ChopTremModel:
    def __init__(self):
        self.phase=0.0;self.gain=1.0

    def init(self,params):
        self.phase=0.0;self.gain=1.0

    def run_mono(self,samples,params,block=64,enable=1):
        if not enable:return [f32(x) for x in samples]
        out=[]
        for start in range(0,len(samples),block):
            depth=f32(f32(params[0])*f32(0.01));increment=f32(f32(params[1])*f32(1.0/44100.0));volume=f32(f32(params[2])*f32(0.02))
            low=f32(1.0-depth)
            for x in samples[start:start+block]:
                p=f32(self.phase+increment)
                self.phase=f32(p-1.0) if p>=1.0 else p
                target=1.0 if self.phase<0.5 else low
                self.gain=f32(self.gain+f32(f32(target-self.gain)*f32(0.01)))
                out.append(f32(volume*f32(self.gain*f32(x))))
        return out
