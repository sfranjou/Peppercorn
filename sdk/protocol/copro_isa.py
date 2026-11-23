"""GP-50 DSP coprocessor instruction set: decoder and small assembler. Offline only.

Word layout: [op:4][a:4][b:4][mode:4][imm:16], little-endian 32-bit words, 16 registers
holding raw 32-bit values; float operations are IEEE binary32.

Status of each form: X = confirmed by executing it on the pedal
(analysis/firmware/COPRO_EXPERIMENTS.md), S = read from stock programs only (static),
? = not understood. The decoder never invents a meaning: unknown words print as `.word`.
"""
from __future__ import annotations
import struct

X,S,U='X','S','?'


def fields(word):
    return word>>28,word>>24&15,word>>20&15,word>>16&15,word&0xffff


def decode(word):
    """Return (text, status)."""
    op,a,b,mode,imm=fields(word);d=imm&15;hi=imm>>4
    r=lambda n:f'r{n}'
    if op==7:
        if b==0 and mode==6:return f'{r(a)} = #{imm:#x}'+('  ; sign-extended' if imm>>15 else ''),X
        if b==0xc and mode==6:return f'{r(a)}.hi = #{imm:#06x}',X
        if b==8 and mode==6:return f'{r(a)}.lo = #{imm:#06x}',X
        # Immediate ALU: mode = function, b = which half the immediate addresses.
        # b = 0 and 2 behave alike (zero-extended immediate); b = c / 8 address one half and keep the other.
        fn={0:'+=',2:'-=',8:'&=',0xc:'|='}.get(mode)
        if fn and b in (0,2):return f'{r(a)} {fn} #{imm:#x}  ; integer',X
        if mode==8 and b==0xc:return f'{r(a)} &= #{imm:#06x}ffff  ; integer, high half only',X
        if mode==8 and b==8:return f'{r(a)} &= #0xffff{imm:04x}  ; integer, low half only',X
        if mode==0xc and b==0xc:return f'{r(a)} ^= #{imm:#06x}0000  ; integer, high half (sign flip)',X
        if fn and b==0xc:return f'{r(a)} {fn} #{imm:#06x}0000  ; integer, high half',S
        if fn and b==8:return f'{r(a)} {fn} #{imm:#06x}  ; integer, low half',S
        if mode==0xa and b in (0,2):return f'{r(a)} |= #{imm:#x}  ; integer; OR / XOR / add not distinguished',X
        if mode==4 and b==0:return f'{r(a)} *= #{imm:#x}  ; integer',X
        return f'.word {word:#010x}  ; op7 a={a} b={b:x} mode={mode:x} imm={imm:#06x}',U
    if op==5:
        if b==0 and mode==0:return f'{r(a)} = D[{imm:#05x}]',X
        if b==0 and mode==8:return f'D[{imm:#05x}] = {r(a)}',X
    if op==0xe and imm==0:
        if mode==2:return f'{r(a)} = D[{r(b)}]',X
        if mode==3:return f'{r(a)} = D[{r(b)}++]',X
        if mode==4:return f'D[{r(a)}] = {r(b)}',X
        if mode==5:return f'D[{r(a)}++] = {r(b)}',X
        if mode==6:return f'{r(a)} = P[{r(b)}]',X
        if mode==7:return f'{r(a)} = P[{r(b)}++]',X
    if op==0xf and mode==4 and imm==0:return f'{r(a)} = {r(b)}',X
    if op==0xf and mode==4 and imm==0x4000:return f'{r(a)}.lo = {r(b)}.lo',X
    if op==0xf and mode==4 and imm==0x7000:return f'{r(a)}.hi = {r(b)}.hi',X
    if op==0xf and mode==0xc and b==0 and imm>>8==0:return f'{r(d)} = bitrev({r(a)}, {(imm>>4)>>1} low bits)',X
    if op==0xd and b==0 and mode==2 and imm>>12==0:return f'{r(d)} = {r(a)} << {(imm>>4)>>1}  ; integer',(X if (imm>>4)>>1<=8 else S)
    if op==0xc and imm>>4==0x400 and mode==6:return f'{r(d)} = {r(a)} ^ {r(b)}.lo  ; integer',X
    if op==0xc and imm>>4==0x500 and mode==0:return f'{r(d)} = {r(a)} + {r(b)}.hi  ; integer',X
    if op==0xc and imm>>4==0x680 and mode in (7,8):return f'{r(d)}.hi = {r(a)}.hi {">>" if mode==7 else "<<"} {r(b)}  ; integer, low half kept',S
    if op==0xc and imm>>4==0x400 and mode in (0,7,8):return f'{r(d)} = {r(a)} {dict([(0,"+"),(7,">>"),(8,"<<")])[mode]} {r(b)}.lo  ; integer',X
    if op==0xf and mode==0xe and hi==0:return f'{r(d)} = rsqrt({r(a)})  ; approximate 1/sqrt',X
    if op==8 and hi==0:
        if mode in (6,7):return f'{r(d)} = {r(a)} * {r(b)}',X
        if mode in (0xa,0xb):return f'{r(d)} += {r(a)} * {r(b)}',X
        if mode==0:return f'{r(d)} = {r(a)} * {r(b)}  ; integer',X
        if mode==4:return f'{r(d)} += {r(a)} * {r(b)}  ; integer',X
        if mode==8:return f'{r(d)} -= {r(a)} * {r(b)}  ; integer',X
    if op==0xc and hi==0:
        names={0xe:('+',X,'f'),0xf:('-',X,'f'),0:('+',X,'i'),0xc:('+',X,'i'),1:('+sat',X,'i'),2:('-',X,'i'),3:('-',X,'i'),0xb:('-',X,'i'),4:('&',X,'i'),5:('|',X,'i'),6:('^',X,'i'),
               7:('>>',X,'i'),0xa:('>>',X,'i'),8:('<<',X,'i'),9:('<<',X,'i')}
        if mode==0xd:return f'{r(d)} = max({r(a)}, {r(b)})  ; signed-integer compare of the words',X
        if mode in names:
            sym,status,kind=names[mode]
            return f'{r(d)} = {r(a)} {sym} {r(b)}'+('' if kind=='f' else '  ; integer'),status
    if op==0xa:
        if a==0xe and b==0 and mode==6 and imm>>12==4:return f'call {imm&0xfff:#05x}',X
        if a==0xe and b==0 and mode==0xa and imm==0x4000:return 'return',X
        if b==0 and mode==6 and imm>>12 in (4,6):return f'call {imm&0xfff:#05x}  ; link {r(a)}.{"hi" if imm>>12==6 else "lo"}',(X if a==12 else S)
        if b==0 and mode==0xa and imm in (0x4000,0x6000):return f'return to {r(a)}.{"hi" if imm==0x6000 else "lo"}',(X if a==12 else S)
        if b==0 and mode==4:return f'loop {r(a)} -> {imm:#05x}',X
        if a==0 and b==0 and mode==8:return f'jump {imm:#05x}',X
        if a==0 and b==0 and mode==0xe and imm==0:return 'end',S
    if op==9 and mode==6 and imm<0x200:
        n=imm-(imm>>8<<9);return (f'skip {n} if {r(a)} != {r(b)}' if n>=0 else f'branch {n} if {r(a)} != {r(b)}')+'  ; integer',(X if n==1 else S)
    if op==9 and mode==2 and imm>>8==0:return f'skip {imm&0xff} if {r(a)} >= {r(b)}  ; integer',(X if imm&0xff==1 else S)
    if op==9 and b==0 and mode in (8,0xa):
        # Conditional skip. Confirmed idioms only; the general condition encoding is open.
        # imm = bit index << 9 | number of words skipped; mode 8 skips when the bit is set,
        # mode a when it is clear. Executed: bit 30 of the flags register and bit 0 of r2.
        bit,count=imm>>9,imm&0x1ff;word_='unless' if mode==0xa else 'if'
        if a==15 and bit==30:return f'skip {count} {word_} negative  ; flags r15',(X if count==1 else S)
        if mode==8 and bit==0:return f'skip {count} if bit 0 of {r(a)}',X
        return f'skip {count} {word_} bit {bit} of {r(a)}',S
    if op==2 and a==0 and b==0 and imm==0:
        # Block words: r10 = count, r9 = source, r11 = destination, r8 = second source or scalar.
        names={0:'copy D[r9..] -> D[r11..]',3:'D[r11..] = D[r8..] + D[r9..]',7:'D[r11..] = D[r8..] * D[r9..]',8:'D[r11..] = r8 * D[r9..]',
               0xd:'r11 = dot(D[r8..], D[r9..])',4:'D[r11..] = r8 + D[r9..]',0xc:'r11 = sum(D[r9..])',1:'D[r11..] = D[r8..] + D[r9..]  ; integer',
               0xa:'r8 = max(r8, D[r9..]), r11 = address of the new maximum',0xb:'r8 = min(r8, D[r9..]), r11 = address of the new minimum',2:'D[r11..] = r8 + D[r9..]  ; integer',5:'D[r11..] = D[r8..] * D[r9..]  ; integer',6:'D[r11..] = r8 * D[r9..]  ; integer'}
        if mode in names:return f'block {names[mode]}  ; count r10',X
        return f'block {mode:#x}  ; r8..r11',S
    return f'.word {word:#010x}',U


# --- assembler for the confirmed (X) forms -----------------------------------

def _reg(n):
    if not 0<=n<=15:raise ValueError('register 0..15')
    return n


def li(r,imm):return 0x70060000|_reg(r)<<24|imm&0xffff if 0<=imm<=0xffff else (_ for _ in ()).throw(ValueError('imm16'))   # hardware sign-extends imm >= 0x8000
def const(r,value):return [0x70c60000|_reg(r)<<24|value>>16&0xffff,0x70860000|_reg(r)<<24|value&0xffff]
def constf(r,x):return const(r,struct.unpack('<I',struct.pack('<f',x))[0])
def load(r,address):return 0x50000000|_reg(r)<<24|address&0xfff
def store(r,address):return 0x50080000|_reg(r)<<24|address&0xfff
def load_ind(r,ptr,inc=False):return 0xe0020000|_reg(r)<<24|_reg(ptr)<<20|(0x10000 if inc else 0)
def store_ind(ptr,r,inc=False):return 0xe0040000|_reg(ptr)<<24|_reg(r)<<20|(0x10000 if inc else 0)
def mov(d,s):return 0xf0040000|_reg(d)<<24|_reg(s)<<20
def fmul(d,a,b):return 0x80060000|_reg(a)<<24|_reg(b)<<20|_reg(d)
def fmac(d,a,b):return 0x800a0000|_reg(a)<<24|_reg(b)<<20|_reg(d)
def fadd(d,a,b):return 0xc00e0000|_reg(a)<<24|_reg(b)<<20|_reg(d)
def fsub(d,a,b):return 0xc00f0000|_reg(a)<<24|_reg(b)<<20|_reg(d)
def loop(r,pc):return 0xa0040000|_reg(r)<<24|pc&0xfff
def jump(pc):return 0xa0080000|pc&0xfff
def skip_if_bit0(r,count=1):return 0x90080000|_reg(r)<<24|count&0x1ff
RUN_NEXT_IF_NEGATIVE,SKIP_NEXT_IF_NEGATIVE=0x9f0a3c01,0x9f083c01
def call(pc):return 0xae064000|pc&0xfff
RETURN=0xae0a4000


def listing(words,base=0):
    return [(base+i,w)+decode(w) for i,w in enumerate(words)]
