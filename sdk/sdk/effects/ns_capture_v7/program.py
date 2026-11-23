"""Exactly stock VTSI + latest GPTC: init installs one of two exclusive kernels."""
import importlib.util
from pathlib import Path
from sdk.effects.ns_capture_v5 import program as stock
from sdk.copro import fft,asm
path=Path(__file__).resolve().parents[2]/'tone_core/fused_079/program.py'
spec=importlib.util.spec_from_file_location('ns_fused_079',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
C=stock.CELLS
CELLS={**C,**{'G_'+k:v for k,v in module.CELLS.items()}}
MODE_EXCLUSIVE_CELLS=True
SOURCE=[('li',5,C['ENABLE']),('load_ind',6,5),('skip_if_bit0',6),('jump','bypass'),
 *stock.VTSI,*stock.tail(fast_mac=True),   # fast_mac: after MOD146, bit-identical except zero signs
 ('jump',0xe00),'bypass:',('jump',0xe00),
 *fft.fft128_subroutine(C['BUF'],stock.TW_PC,'fft',cells=C['FFTC'],fast=True),*stock.NLCLIP]   # 2026-11-08 MOD145: bit-identical, fewer instructions
STAGED_SOURCE=module.SOURCE
MODE_CODE_PC=0x500+len(asm.assemble(SOURCE,0x500))
PROGRAM_DATA_PC=module.TW
ALLOW_CALLS=True
ALLOWED_NON_X=[]
