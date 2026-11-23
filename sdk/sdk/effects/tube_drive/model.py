"""Float32 model of Tube Drive. Offline only.

  cells(gain, tone, vol, enable)   what the ARM half (tube_drive.c) writes: cell name -> 32-bit value
  init_cells(gain, tone, vol)      the complete cell set after init (states zero, ramps at their targets)
  run_block(c, window)             one block of the coprocessor program (program.py), operation by
                                   operation in the program's order, each result rounded to binary32
                                   (IEEE, gradual underflow); updates the state cells in `c`
  transfer(x)                      the static curve of stage 3

`c` maps cell names to 32-bit patterns, `window` is a list of 64 bit patterns.
"""
import struct
r32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
fl=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]

# --- constants shared with tube_drive.c (same decimal literals) -------------------------------
DRIVE_MIN,DRIVE_CURVE=r32(3.0),r32(0.0147)          # drive = 3 + Gain^2 * 0.0147        3 .. 150
TONE_MIN,TONE_CURVE=r32(0.09),r32(0.6)              # a = 0.09 + (Tone/100)^2 * 0.6      0.09 .. 0.69
OUT_SCALE,MAKEUP,LEVEL_FLOOR=r32(0.08),r32(0.75),r32(1e-6)   # level = (VOL/50)^2 * (0.08 + 0.75/drive) + 1e-6
# Second-order Butterworth high-pass, 140 Hz at 44.1 kHz (RBJ form, normalised by a0); see test_hp_design.
HP_B0,HP_B1,HP_B2,HP_A1,HP_A2=(r32(x) for x in (0.985994606,-1.97198921,0.985994606,-1.97179305,0.972185372))
HP_FC,FS=140.0,44100.0
RAMP_K=fl(0x396dc66d)
ONE,MINUS_ONE,MINUS_THIRD=r32(1.0),r32(-1.0),r32(-1.0/3.0)


def cells(gain_knob,tone_knob,vol_knob,enable=1):
    """Cells written by every process call (targets, tone coefficient, enable)."""
    g=r32(gain_knob);t=r32(r32(tone_knob)*r32(0.01));v=r32(r32(vol_knob)*r32(0.02))
    drive=r32(DRIVE_MIN+r32(r32(g*g)*DRIVE_CURVE))
    level=r32(r32(r32(v*v)*r32(OUT_SCALE+r32(MAKEUP/drive)))+LEVEL_FLOOR)
    return dict(ENABLE=1 if enable else 0,DRIVE_TGT=bits(drive),TONE_A=bits(r32(TONE_MIN+r32(r32(t*t)*TONE_CURVE))),LEVEL_TGT=bits(level))


def init_cells(gain_knob,tone_knob,vol_knob):
    c=cells(gain_knob,tone_knob,vol_knob,enable=0)
    c.update(HP_B0=bits(HP_B0),HP_B1=bits(HP_B1),HP_B2=bits(HP_B2),HP_A1=bits(HP_A1),HP_A2=bits(HP_A2),HP_S1=0,HP_S2=0,
             DRIVE_CUR=c['DRIVE_TGT'],TONE_Z=0,LEVEL_CUR=c['LEVEL_TGT'])
    return c


def transfer(x):
    x=max(-1.0,min(1.0,x));return x-x*x*x/3.0


def _ramp(c,target,current,w):
    tgt,cur=fl(c[target]),fl(c[current]);step=r32(RAMP_K*r32(tgt-cur));out=[]
    for x in w:
        cur=r32(cur+step);out.append(r32(cur*x))
    c[current]=bits(cur);return out


def run_block(c,window,stages=None):
    """Returns the 64 output bit patterns; `stages`, if a list, receives the window after each stage."""
    w=[fl(b) for b in window]
    def note():
        if stages is not None:stages.append([bits(x) for x in w])
    w=_ramp(c,'DRIVE_TGT','DRIVE_CUR',w);note()
    b0,b1,b2,a1,a2,s1,s2=(fl(c[k]) for k in ('HP_B0','HP_B1','HP_B2','HP_A1','HP_A2','HP_S1','HP_S2'));out=[]
    for x in w:
        y=r32(r32(x*b0)+s1)
        s1=r32(r32(r32(x*b1)-r32(y*a1))+s2)
        s2=r32(r32(x*b2)-r32(y*a2))
        out.append(y)
    c['HP_S1'],c['HP_S2']=bits(s1),bits(s2);w=out;note()
    out=[]
    for x in w:
        if r32(ONE-x)<0:x=ONE
        if r32(x-MINUS_ONE)<0:x=MINUS_ONE
        s=r32(x*x);s=r32(x*s);s=r32(MINUS_THIRD*s)
        out.append(r32(s+x))
    w=out;note()
    a,z=fl(c['TONE_A']),fl(c['TONE_Z']);out=[]
    for x in w:
        z=r32(z+r32(r32(x-z)*a));out.append(z)
    c['TONE_Z']=bits(z);w=out;note()
    w=_ramp(c,'LEVEL_TGT','LEVEL_CUR',w);note()
    return [bits(x) for x in w]
