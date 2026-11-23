"""GPTC v1: fixed2696byte compact model record, full precision, no GP5N ambiguity.

Header12u32 words: magic/version/size/parallel/pre32/secondary16or0/post256/
branchgain/floor/inputgain/outputgain/FNV1a(excluding checksum word).
Payload: reversed PRE32, SECOND16, NL0/1four positive floats each,
reversed original shared LPF40, fixedBQ5,4partitions×130float spectra(/128).
Tail padding zero; entire record except checksum participates in integrity hash.
"""
import math,struct
SIZE=2696;MAGIC=b'GPTC';VERSION=1
OFFSETS=dict(PRE=48,SECOND=176,NL0=240,NL1=256,LPF=272,BQ=432,SPEC=452)

def checksum(raw):
    h=2166136261
    for byte in raw[:44]+raw[48:]:h=((h^byte)*16777619)&0xffffffff
    return h

def encode(values,spectra,input_gain=.5,output_gain=1.25594995):
    out=bytearray(SIZE);parallel=bool(values['parallel'])
    struct.pack_into('<4s6I4f',out,0,MAGIC,VERSION,SIZE,int(parallel),32,16 if parallel else 0,256,
      values['branch_gain'],values['floor'],input_gain,output_gain)
    arrays=dict(PRE=values['pre'][::-1],SECOND=values['second'][::-1],NL0=values['nl'][0],
      NL1=values['nl'][1] if parallel else [1.]*4,LPF=values['lpf'][::-1],BQ=values['biquad'],SPEC=spectra)
    for name,seq in arrays.items():
        seq=list(map(float,seq));assert all(math.isfinite(x) for x in seq)
        struct.pack_into('<%df'%len(seq),out,OFFSETS[name],*seq)
    struct.pack_into('<I',out,44,checksum(out));validate(out);return bytes(out)

def validate(raw):
    if len(raw)!=SIZE or raw[:4]!=MAGIC:raise ValueError('GPTCsize/magic')
    version,size,parallel,pre,secondary,post=struct.unpack_from('<6I',raw,4)
    if (version,size,pre,post)!=(1,SIZE,32,256) or parallel not in (0,1) or secondary!=16*parallel:raise ValueError('GPTCgeometry/version')
    if struct.unpack_from('<I',raw,44)[0]!=checksum(raw):raise ValueError('GPTCchecksum')
    branch,floor,ig,og=struct.unpack_from('<4f',raw,28)
    if not all(math.isfinite(x) for x in [branch,floor,ig,og]) or floor not in [-1024.,-2047.] or abs(branch)>100 or not(0<=ig<=4 and 0<=og<=8):raise ValueError('GPTCscalars')
    coeffs=struct.unpack_from('<621f',raw,48)
    if not all(math.isfinite(x) and abs(x)<=1e6 for x in coeffs):raise ValueError('GPTCcoefficients')
    for name in ['NL0','NL1']:
        if min(struct.unpack_from('<4f',raw,OFFSETS[name]))<=0:raise ValueError('GPTCnonlinearity')
    _,_,_,a1,a2=struct.unpack_from('<5f',raw,OFFSETS['BQ'])
    if not(abs(a2)<1 and 1+a1+a2>0 and 1-a1+a2>0):raise ValueError('GPTCunstableBQ')
    return True
