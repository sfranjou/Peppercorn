"""Offline fitted32/16->256 kernel: secondary NL accumulates directly into OS.

New owned experiment. Uses qualified SDK FIR/FFT helpers, preserving actual
frozen044 compact nonlinearities/LPF. Independent from ns_capture_v* features.
"""
from sdk.copro import asm,fft

BASE=0x500;EXIT=0xe00;PARTS=4;SPEC=EXIT-PARTS*130;TW=SPEC-160
SIZES=dict(ENABLE=1,ZERO=1,ONE=1,INV1024=1,THIRD=1,TWOTHIRD=1,
    INPUT_GAIN=1,OUTPUT_GAIN=1,FLOOR=1,BRANCH_GAIN=1,PREV0=1,PREV1=1,CUTOFF_SQUARED=1,
    NL0=4,NL1=4,PRE=32,SECOND=16,BQ=9,BRANCH_WINDOW=64,
    H0=95,H1=79,OS=295,LPF=40,
    BUF=256,HIST=64,ACC=130,FDL=520,STATE=1,FFTC=8)
C={};cursor=0x398
for name,size in SIZES.items():C[name]=cursor;cursor+=size
DATA_END=cursor
assert DATA_END<=0xf9c

def nl(name,coeff):
    # r8 input -> r9 output; preserve r0..5 and r8. ONE and floor per model.
    return [name+':',('load',10,coeff),('load',11,coeff+2),('neg',11),
      ('load',12,C['ZERO']),('load',6,coeff+1),('neg',6),('load',7,coeff+3),
      ('fsub',13,8,12),('run_next_if_negative',),('mov',10,6),
      ('fsub',13,8,12),('run_next_if_negative',),('mov',11,7),
      ('fmul',9,11,8),('load',6,C['FLOOR']),
      ('fsub',13,9,6),('run_next_if_negative',),('mov',9,6),
      ('load',6,C['INV1024']),('load',7,C['ONE']),
      ('fmul',13,9,6),('fadd',12,7,13),
      # If e0^2 < .9025, E=e0^1024 < .9025^512 < 2e-23.
      # Then binary32 (1-E) rounds EXACTLY to1, so output is A. Avoid
      # unsupported denormal intermediates without assuming hardware FTZ.
      ('fmul',13,12,12),('load',6,C['CUTOFF_SQUARED']),
      ('fsub',9,13,6),('run_next_if_negative',),('jump',name+'_saturated'),
      *[('fmul',13 if j%2==0 else 12,12 if j%2==0 else 13,12 if j%2==0 else 13) for j in range(1,10)],
      ('fsub',13,7,12),('fmul',9,10,13),('ret',),
      name+'_saturated:',('mov',9,10),('ret',)]

def interp(window,out,previous,label,clip,mix=False):
    store=[('store_inc',2,9)] if not mix else [
      ('load_ind',6,2),('load',7,C['BRANCH_GAIN']),('fmul',10,9,7),
      ('fadd',11,6,10),('store_inc',2,11)]
    return [('li',0,window),('li',1,64),('li',2,out),label+':',
      ('load',3,previous),('load_inc',4,0),('store',4,previous),('fsub',5,4,3),
      ('mov',8,3),('call',clip),*store,
      ('load',6,C['THIRD']),('fmul',7,5,6),('fadd',8,3,7),('call',clip),*store,
      ('load',6,C['TWOTHIRD']),('fmul',7,5,6),('fadd',8,3,7),('call',clip),*store,
      ('mov',8,4),('call',clip),*store,('loop',1,label)]

def biquad():
    c=C['BQ']
    return [('li',0,0x13),('li',1,64),
      *[('load',i+2,c+i) for i in range(5)],
      *[('load',i+7,c+5+i) for i in range(4)],'bq:',
      ('load_ind',11,0),('fmul',12,2,11),('fmac',12,3,7),('fmac',12,4,8),
      ('mov',8,7),('mov',7,11),('fmul',11,5,9),('fsub',13,12,11),
      ('fmul',11,6,10),('fsub',12,13,11), # same sequential subtractions as portable C
      ('mov',10,9),('mov',9,12),('store_inc',0,12),('loop',1,'bq'),
      *[('store',i+7,c+5+i) for i in range(4)]]

def source(parallel=True):
    src=[('li',5,C['ENABLE']),('load_ind',6,5),('skip_if_bit0',6),('jump','bypass'),
      ('load',8,C['INPUT_GAIN']),('li',9,0x13),('li',10,64),('li',11,0x13),('block','scale')]
    if parallel:src += [('li',9,0x13),('li',10,64),('li',11,C['BRANCH_WINDOW']),('block','copy')]
    src+=asm.fir_block(0x13,C['PRE'],C['H0'],32,'main_fir')
    if parallel:src+=asm.fir_block(C['BRANCH_WINDOW'],C['SECOND'],C['H1'],16,'second_fir')
    src+=interp(0x13,C['OS']+39,C['PREV0'],'interp_main','nl_main')
    if parallel:
        src+=interp(C['BRANCH_WINDOW'],C['OS']+39,C['PREV1'],'interp_second','nl_second',mix=True)
    src += [('li',0,0x13),('li',1,64),('li',2,C['OS']+3),'decimate:',
      ('li',8,C['LPF']),('mov',9,2),('li',10,40),('block','dot'),('store_inc',0,11),('addi',2,4),('loop',1,'decimate'),
      ('li',9,C['OS']+256),('li',10,39),('li',11,C['OS']),('block','copy')]
    src+=biquad()
    src+=fft.convolver(0x13,C['BUF'],C['HIST'],C['FDL'],C['ACC'],C['STATE'],SPEC,TW,PARTS,C['ZERO'],'post',fft_label='fft')
    src += [('load',8,C['OUTPUT_GAIN']),('li',9,0x13),('li',10,64),('li',11,0x13),('block','scale'),
      ('jump',EXIT),'bypass:',('jump',EXIT)]
    src+=fft.fft128_subroutine(C['BUF'],TW,'fft',cells=C['FFTC'])
    src+=nl('nl_main',C['NL0'])
    if parallel:src+=nl('nl_second',C['NL1'])
    words=asm.assemble(src,BASE);assert BASE+len(words)<=TW
    return src,words
