"""Offline two parallel fitted compact captures; no loader/firmware integration.

Mechanically relocates the qualified051optimized kernels into separate data
histories while sharing only ephemeral FFT BUF/ACC/FFTC. Own full-float post
spectra, one shared twiddle table. Two complete convolvers, output average.
"""
from sdk.tone_core.copro_051 import program_optimized as K
from sdk.copro import asm

BASE=0x500;EXIT=0xe00;TW=EXIT-2*520-160;SPECS=[TW+160,TW+160+520]
ENABLE=0x398;MIX_GAIN=ENABLE+1;RAW=MIX_GAIN+1;MIX=RAW+64;MAPS=[];cursor=MIX+64
SHARED={'BUF','ACC','FFTC'}
for slot in range(2):
    c={'ENABLE':ENABLE}
    for name,size in K.SIZES.items():
        if name=='ENABLE':continue
        if slot and name in SHARED:c[name]=MAPS[0][name]
        else:c[name]=cursor;cursor+=size
    MAPS.append(c)
DATA_END=cursor
assert DATA_END<=0xf9c

def relocated(slot,parallel):
    src,_=K.source(parallel);out=[];skip=False;prefix=f'm{slot}_';c=MAPS[slot]
    mapping={K.C[name]+i:c[name]+i for name,size in K.SIZES.items() for i in range(size)}
    # Remove inner entry/bypass; one outer enabled flag controls both models.
    for item in src[4:]:
        if item=='bypass:':skip=True;continue
        if skip:skip=False;continue
        if isinstance(item,str):out.append(prefix+item);continue
        op,*args=item
        if op=='jump' and args[0]==EXIT:out.append(('jump',prefix+'done'));continue
        if op in ('load','store'):
            args[1]=mapping[args[1]]
        elif op=='li':
            if args[1]==K.TW:args[1]=TW
            elif args[1]==K.SPEC:args[1]=SPECS[slot]
            elif args[1] in mapping:args[1]=mapping[args[1]]
        elif op in ('addi','subi') and args[1] in mapping:
            # SDK FFT/convolver forms absolute pointers by adding BUF/FDL
            # bases to offsets. These base immediates also require relocation.
            args[1]=mapping[args[1]]
        if op in ('loop','jump','call') and isinstance(args[-1],str):args[-1]=prefix+args[-1]
        out.append(tuple([op]+args))
    return out+[prefix+'done:']

def source(parallel=(True,True)):
    src=[('li',5,ENABLE),('load_ind',6,5),('skip_if_bit0',6),('jump','bypass'),
      ('li',9,0x13),('li',10,64),('li',11,RAW),('block','copy')]
    src+=relocated(0,parallel[0])
    src += [('li',9,0x13),('li',10,64),('li',11,MIX),('block','copy'),
      ('li',9,RAW),('li',10,64),('li',11,0x13),('block','copy')]
    src+=relocated(1,parallel[1])
    src += [('li',8,MIX),('li',9,0x13),('li',10,64),('li',11,0x13),('block','add'),
      ('load',8,MIX_GAIN),
      ('li',9,0x13),('li',10,64),('li',11,0x13),('block','scale'),
      ('jump',EXIT),'bypass:',('jump',EXIT)]
    words=asm.assemble(src,BASE);assert BASE+len(words)<=TW,(len(words),TW-BASE)
    return src,words
