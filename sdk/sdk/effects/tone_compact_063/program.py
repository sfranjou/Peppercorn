"""SDK effect063: exact compact kernel, optional independent secondary front.

New owned experiment. Uses qualified SDK FIR/FFT helpers, preserving actual
frozen044 compact nonlinearities/LPF. Independent from ns_capture_v* features.
"""
from sdk.copro import asm,fft

BASE=0x500;EXIT=0xe00;PARTS=4;SPEC=EXIT-PARTS*130;TW=SPEC-160
# 2026-11-08 options (defaults keep the shipped 063 program byte-identical): FAST_FFT uses fft128_fast (bit-identical
# output, fewer instructions); TW_IN_DATA keeps the twiddle table in data cells C['TW'] instead of program memory at TW.
FAST_FFT=False;TW_IN_DATA=False
FAST_MAC=False  # 2026-11-08: convolver fast_mac (bit-identical output except zero signs, fewer instructions)
RUNTIME_PARTS=False # 2026-11-08: partition count from cells C['PARTS']/C['SPAN'] (ARM sets 4 without an IR, 12 with one)
NL_PRENEG=False # 2026-11-08: NL coefficients 1 and 2 stored negated by the ARM init (sign-bit XOR, as the DSP neg); drops 2 neg per call
SIZES=dict(ENABLE=1,ZERO=1,ONE=1,INV1024=1,THIRD=1,TWOTHIRD=1,
    INPUT_GAIN=1,OUTPUT_GAIN=1,FLOOR=1,BRANCH_GAIN=1,PREV0=1,PREV1=1,CUTOFF_SQUARED=1,
    NL0=4,NL1=4,PRE=32,SECOND=16,BQ=9,BRANCH_WINDOW=64,
    H0=95,H1=79,OS=295,LPF=40,
    BUF=256,HIST=64,ACC=130,FDL=520,STATE=1,FFTC=8,PARALLEL=1,BASS=9,MID=9,TREBLE=9)
C={};cursor=0x398
for name,size in SIZES.items():C[name]=cursor;cursor+=size
DATA_END=cursor
assert DATA_END<=0xf9c

def nl(name,coeff):
    # r8 input -> r9 output; preserve r0..5 and r8. ONE and floor per model.
    neg11=[] if NL_PRENEG else [('neg',11)]; neg6=[] if NL_PRENEG else [('neg',6)]
    return [name+':',('load',10,coeff),('load',11,coeff+2),*neg11,
      ('load',12,C['ZERO']),('load',6,coeff+1),*neg6,('load',7,coeff+3),
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

# 2026-11-08 capture pair hooks (defaults keep every existing program byte-identical): SPEC_FROM_CELL reads the
# spectra address from C['SPEC']; PRE_BODY runs after the enable check (fused_079 pair mode: the second capture);
# EXTRA_SUBS are appended subroutines; CODE_LIMIT overrides the code-end bound.
SPEC_FROM_CELL=False;PRE_BODY=[];EXTRA_SUBS=[];CODE_LIMIT=None
# 2026-11-21 GPTS v1 two-spline mode (sdk/tone_core/spline_record.py). SPLINE=False keeps every program byte-identical.
# When True the fused player supplies cells SPLINE (bit 0 = this record is GPTS), KN (33 fixed knots) and AB (A1, B1,
# A2, B2: 32 segment coefficients each, from the ARM init). In GPTS mode PARALLEL is 0, SECOND holds the reversed
# 16-tap interstage FIR and H1 its history (16 + 63 cells, exactly fir_block's layout). Spline 1 runs in the 4x
# interpolation in place of nl_main; the interstage FIR then spline 2 run in place over the 256 new OS samples.
SPLINE=False
# 2026-11-21 SPLINE_ONLY: the spline front always runs; no GPTC v1 nonlinearity, no SPLINE
# flag cell, no parallel branch. The caller removes the v1-only cells from SIZES (fused_079).
SPLINE_ONLY=False

def spline_sub():
    """spline_a / spline_b: r8 = z -> r9 = A[p] + z*B[p]; preserves r0..r5 and r8 (as nl). Segment p = largest j in
    1..31 with KN[j] < z, else 0 (binary search; fsub + negative flag, as capture_spline.c)."""
    kn,ab=C['KN'],C['AB']
    off=lambda d:('li',6,d) if 0<=d<=0x7fff else ('const',6,d&0xffffffff)   # AB may lie below KN (second slot)
    src=['spline_a:',off(ab-kn),('jump','spline_common'),'spline_b:',off(ab+64-kn),'spline_common:',('li',10,kn)]
    for step in (16,8,4,2,1):
        src+=[('mov',11,10),('addi',11,step),('load_ind',12,11),('fsub',13,12,8),('run_next_if_negative',),('addi',10,step)]
    return src+[('iadd',11,10,6),('load_ind',9,11),('addi',11,32),('load_ind',12,11),('fmac',9,8,12),('ret',)]

def spline_stage():
    """Spline-mode body between the main FIR and the decimator: interpolation through spline 1 into OS+39..OS+294,
    the interstage FIR over four 64-sample windows (fir_block with a moving window), then spline 2 in place."""
    os_,h=C['OS']+39,C['H1']
    src=interp(0x13,os_,C['PREV0'],'interp_spline','spline_a')
    src+=[('li',13,os_),('li',12,4),'inter_chunk:',
      ('mov',9,13),('li',10,0x40),('li',11,h+15),('block','copy'),
      ('li',0,h),('mov',1,13),('li',2,0x40),('li',3,C['SECOND']),('li',4,16),
      'inter_tap:',('mov',8,3),('mov',9,0),('mov',10,4),('block','dot'),('store_inc',1,11),('load_inc',5,0),('loop',2,'inter_tap'),
      ('li',9,h+64),('li',10,15),('li',11,h),('block','copy'),
      ('addi',13,0x40),('loop',12,'inter_chunk'),
      ('li',0,os_),('li',1,256),'spline_out:',('load_ind',8,0),('call','spline_b'),('store_inc',0,9),('loop',1,'spline_out')]
    return src

def body(parallel=True):
    """The per-block processing on D[0x13..0x52], from input gain to output gain (no enable check, exit or subroutines)."""
    src=[('load',8,C['INPUT_GAIN']),('li',9,0x13),('li',10,64),('li',11,0x13),('block','scale')]
    if parallel:src += [('load',6,C['PARALLEL']),('skip_if_bit0',6),('jump','copy_done'),('li',9,0x13),('li',10,64),('li',11,C['BRANCH_WINDOW']),('block','copy'),'copy_done:']
    src+=asm.fir_block(0x13,C['PRE'],C['H0'],32,'main_fir')
    if parallel:src += [('load',6,C['PARALLEL']),('skip_if_bit0',6),('jump','second_done'),*asm.fir_block(C['BRANCH_WINDOW'],C['SECOND'],C['H1'],16,'second_fir'),'second_done:']
    if SPLINE_ONLY:src += spline_stage()
    elif SPLINE:src += [('load',6,C['SPLINE']),('skip_if_bit0',6),('jump','gptc_front'),*spline_stage(),('jump','front_done'),'gptc_front:']
    if not SPLINE_ONLY:src+=interp(0x13,C['OS']+39,C['PREV0'],'interp_main','nl_main')
    if parallel:
        src += [('load',6,C['PARALLEL']),('skip_if_bit0',6),('jump','interp_done'),*interp(C['BRANCH_WINDOW'],C['OS']+39,C['PREV1'],'interp_second','nl_second',mix=True),'interp_done:']
    if SPLINE and not SPLINE_ONLY:src += ['front_done:']
    src += [('li',0,0x13),('li',1,64),('li',2,C['OS']+3),'decimate:',
      ('li',8,C['LPF']),('mov',9,2),('li',10,40),('block','dot'),('store_inc',0,11),('addi',2,4),('loop',1,'decimate'),
      ('li',9,C['OS']+256),('li',10,39),('li',11,C['OS']),('block','copy')]
    src+=biquad()
    src+=fft.convolver(0x13,C['BUF'],C['HIST'],C['FDL'],C['ACC'],C['STATE'],('cell',C['SPEC']) if SPEC_FROM_CELL else SPEC,TW,('cells',C['PARTS'],C['SPAN']) if RUNTIME_PARTS else PARTS,C['ZERO'],'post',fft_label='fft',fast_mac=FAST_MAC)
    src += asm.biquad_block(0x13,C['BASS'],'tone_bass')+asm.biquad_block(0x13,C['MID'],'tone_mid')+asm.biquad_block(0x13,C['TREBLE'],'tone_treble')
    src += [('load',8,C['OUTPUT_GAIN']),('li',9,0x13),('li',10,64),('li',11,0x13),('block','scale')]
    return src

def source(parallel=True):
    src=[('li',5,C['ENABLE']),('load_ind',6,5),('skip_if_bit0',6),('jump','bypass'),*PRE_BODY,*body(parallel),
      ('jump',EXIT),'bypass:',('jump',EXIT)]
    src+=fft.fft128_subroutine(C['BUF'],C['TW'] if TW_IN_DATA else TW,'fft',cells=C['FFTC'],fast=FAST_FFT,tw_data=TW_IN_DATA)
    if not SPLINE_ONLY:src+=nl('nl_main',C['NL0'])
    if parallel and not SPLINE_ONLY:src+=nl('nl_second',C['NL1'])
    if SPLINE or SPLINE_ONLY:src+=spline_sub()
    src+=EXTRA_SUBS
    words=asm.assemble(src,BASE);assert BASE+len(words)<=(CODE_LIMIT or (SPEC if TW_IN_DATA else TW))
    return src,words

CELLS=C
PROGRAM_DATA_PC=TW
ALLOW_CALLS=True
ALLOWED_NON_X=[]
SOURCE=source(True)[0]
