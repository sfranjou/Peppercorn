"""Tiny assembler for GP-50 coprocessor programs written as a Python list. Offline only.

Source form: a list whose items are either a label string ending in ':' or a tuple
(mnemonic, operand, ...). Only instruction forms that were executed on the pedal can be
written; every emitted word is checked against protocol/copro_isa.decode (status 'X') and
against the stricter operand rules below (destination distinct from the operands, as in the
experiments). Raw words are possible with ('word', value, 'reason') and are reported.

Mnemonics (registers are numbers 0..13; r14 is the call link, r15 the flags):
  ('li', r, imm15)              r = imm (0..0x7fff; hardware sign-extends)  7R06 iiii
  ('const', r, value32)         r = 32-bit constant (two words)              7Rc6 hhhh, 7R86 llll
  ('constf', r, x)              r = float32 constant (two words)
  ('load', r, address)          r = D[address]                               5R00 aaaa
  ('store', r, address)         D[address] = r                               5R08 aaaa
  ('load_ind', r, ptr)          r = D[ptr]                                   eRP2 0000
  ('load_inc', r, ptr)          r = D[ptr]; ptr += 1                         eRP3 0000
  ('store_ind', ptr, r)         D[ptr] = r                                   ePR4 0000
  ('store_inc', ptr, r)         D[ptr] = r; ptr += 1                         ePR5 0000
  ('mov', d, s)                 d = s                                        fDS4 0000
  ('fmul', d, a, b)             d = a * b (float)                            8AB6 000D
  ('fadd', d, a, b)             d = a + b (float)                            cABe 000D
  ('fsub', d, a, b)             d = a - b (float; sets negative/zero flags)  cABf 000D
  ('fmac', d, a, b)             d += a * b (product rounded, then added: X)  8ABa 000D
  ('run_next_if_negative',)     skip the next word unless the last subtract was negative   9f0a 3c01
  ('skip_next_if_negative',)    skip the next word if the last subtract was negative       9f08 3c01
  ('loop', r, label)            r -= 1; branch to label while r != 0         aR04 tttt
  ('jump', label_or_pc)         unconditional jump (a number = absolute PC,  a008 tttt
                                e.g. the next slot's base)
  ('skip_if_bit0', r)           skip the next word if bit 0 of r is set      9R08 0001
                                (the stock "is this stage enabled" test)
  ('call', label)               one-level call, link in r14 (frame.check(..., allow_calls=True))  ae06 4ttt
  ('ret',)                      return to the caller                         ae0a 4000
  Integer / addressing forms executed 2026-10-20 (COPRO_EXPERIMENTS.md i_fft_*):
  ('pload', r, ptr)             r = P[ptr] (program memory)                  eRP6 0000
  ('pload_inc', r, ptr)         r = P[ptr]; ptr += 1                         eRP7 0000
  ('addi', r, imm16)            r += imm (integer)                           7R00 iiii
  ('subi', r, imm16)            r -= imm (integer)                           7R02 iiii
  ('iadd', d, a, b)             d = a + b (integer; d may equal a)           cAB0 000D
  ('ishr', d, a, b)             d = a >> b.lo (integer)                      cAB7 400D
  ('bitrev', d, a, w)           d = a with its low w bits reversed (w 4, 6, 7; upper bits kept)  fA0c 00(2w)D
  ('shl', d, a, n)              d = a << n (integer, n 0..8)                 dA02 0(2n)D
  ('skip_ge', a, b, 1)          skip the next word if a >= b (integer)       9AB2 0001
  ('neg', r)                    flip the float sign (high-half XOR 0x8000)   7Rcc 8000
  Pitfalls: `li` is sign-extended on hardware (use const for >= 0x8000); a flag skip must follow its fsub
  directly; calls nest only as executed (one r14 level here). Writing an N->S program: sdk/README.md 3d,
  examples sdk/effects/ns_capture_v3 / v4, offline test pattern sdk/test_ns_capture_v3.py (Runner: built ARM
  code in the Thumb interpreter + program in protocol/copro_sim.Sim, strict unless a named hypothesis is passed).
  ('end',)                      end of block (EQ slot exits only)            a00e 0000
  ('block', name)               block word over r8..r11, count in r10        20mm 0000
                                (executed 2026-10-12, COPRO_EXPERIMENTS.md "Block words"):
                                  'copy'        D[r11..] = D[r9..]                 mm = 0
                                  'add'         D[r11..] = D[r8..] + D[r9..]       mm = 3
                                  'add_scalar'  D[r11..] = r8 + D[r9..]            mm = 4
                                  'mul'         D[r11..] = D[r8..] * D[r9..]       mm = 7
                                  'scale'       D[r11..] = r8 * D[r9..]            mm = 8
                                  'dot'         r11 = dot(D[r8..], D[r9..])        mm = d
                                r9/r11 (and r8 when it is a pointer) advance, r10 ends 0.
"""
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from protocol import copro_isa as isa  # noqa: E402

RUN_NEXT_IF_NEGATIVE=0x9f0a3c01
SKIP_NEXT_IF_NEGATIVE=0x9f083c01
BLOCK={'copy':0,'add':3,'add_scalar':4,'mul':7,'scale':8,'dot':0xd}   # float block words executed on the pedal ('sum' removed 2026-10-20: hardware result unexplained)
fbits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]


class AsmError(ValueError):pass


def _general(*regs):
    for r in regs:
        if not 0<=r<=13:raise AsmError(f'register r{r}: only r0..r13 are general registers (r14 link, r15 flags)')


def _distinct(d,*operands):
    if d in operands:raise AsmError(f'destination r{d} equals an operand: only executed with a distinct destination')


def _address(a):
    if not 0<=a<0x1000:raise AsmError(f'data address {a:#x}')
    return a


def _encode(item,labels,pc):
    m,*o=item
    def target(name):
        if isinstance(name,int):
            if not 0<=name<0x1000:raise AsmError(f'jump target {name:#x}')
            return name
        return labels[name] if labels is not None else 0
    if m=='li':
        _general(o[0])
        if not 0<=o[1]<=0x7fff:raise AsmError(f'li r{o[0]}, {o[1]:#x}: the immediate is sign-extended on hardware (i_fft_0_001); use const')
        return [isa.li(o[0],o[1])]
    if m=='const':_general(o[0]);return isa.const(o[0],o[1])
    if m=='constf':_general(o[0]);return isa.constf(o[0],o[1])
    if m=='load':_general(o[0]);return [isa.load(o[0],_address(o[1]))]
    if m=='store':_general(o[0]);return [isa.store(o[0],_address(o[1]))]
    if m in ('load_ind','load_inc'):_general(*o);_distinct(o[0],o[1]);return [isa.load_ind(o[0],o[1],inc=m=='load_inc')]
    if m in ('store_ind','store_inc'):_general(*o);_distinct(o[0],o[1]);return [isa.store_ind(o[0],o[1],inc=m=='store_inc')]
    if m=='mov':_general(*o);return [isa.mov(*o)]
    if m in ('fmul','fadd','fsub'):_general(*o);_distinct(o[0],o[1],o[2]);return [getattr(isa,m)(*o)]
    if m=='fmac':_general(*o);_distinct(o[0],o[1],o[2]);return [0x800a0000|o[1]<<24|o[2]<<20|o[0]]   # d += a*b, product rounded then added (X)
    if m=='run_next_if_negative':return [RUN_NEXT_IF_NEGATIVE]
    if m=='skip_next_if_negative':return [SKIP_NEXT_IF_NEGATIVE]
    if m=='loop':_general(o[0]);return [0xa0040000|o[0]<<24|target(o[1])]
    if m=='jump':return [0xa0080000|target(o[0])]
    if m=='skip_if_bit0':_general(o[0]);return [isa.skip_if_bit0(o[0],1)]
    if m=='call':return [isa.call(target(o[0]))]                                                   # one-level call linking r14 (X)
    if m=='ret':return [isa.RETURN]
    if m=='end':return [0xa00e0000]   # EQ slot only (frame.check_eq): S in isolation, executed every block by stock EQ
    if m=='block':
        if o[0] not in BLOCK:raise AsmError(f'block word {o[0]!r}: only {sorted(BLOCK)} were executed')
        return [0x20000000|BLOCK[o[0]]<<16]
    # Integer/addressing forms executed on the pedal 2026-10-20 (COPRO_EXPERIMENTS.md, i_fft_*):
    if m in ('pload','pload_inc'):_general(*o);_distinct(o[0],o[1]);return [0xe0000000|o[0]<<24|o[1]<<20|(7 if m=='pload_inc' else 6)<<16]   # rA = P[rB] / P[rB++]
    if m in ('addi','subi'):
        _general(o[0])
        if not 0<=o[1]<=0xffff:raise AsmError('addi/subi immediate 0..0xffff')
        return [0x70000000|o[0]<<24|(2 if m=='subi' else 0)<<16|o[1]]                               # rR += / -= imm (integer)
    if m=='bitrev':
        _general(o[0],o[1])
        if o[2] not in (4,6,7):raise AsmError('bitrev: widths 4, 6, 7 executed')
        return [0xf00c0000|o[1]<<24|(2*o[2])<<4|o[0]]                                                # rd = bitrev(low w bits of rA), upper kept
    if m=='shl':
        _general(o[0],o[1])
        if not 0<=o[2]<=8:raise AsmError('shl: shifts 0..8 executed')
        return [0xd0020000|o[1]<<24|(2*o[2])<<4|o[0]]                                                # rd = rA << n (integer)
    if m=='skip_ge':
        _general(o[0],o[1])
        if o[2]!=1:raise AsmError('skip_ge: only a count of 1 was executed')
        return [0x90020000|o[0]<<24|o[1]<<20|1]                                                      # skip next word if rA >= rB
    if m=='iadd':_general(*o);return [0xc0000000|o[1]<<24|o[2]<<20|o[0]]                              # rd = rA + rB (integer; d may equal A, as stock)
    if m=='ishr':_general(*o);return [0xc0074000|o[1]<<24|o[2]<<20|o[0]]                             # rd = rA >> rB.lo (integer)
    if m=='neg':_general(o[0]);return [0x70cc8000|o[0]<<24]                                          # float sign flip (high-half XOR)
    if m=='word':return [o[0]]
    raise AsmError(f'unknown mnemonic {m!r}')


def assemble(source,base):
    """Return the list of words for `source` placed at PC `base`."""
    labels={};pc=base
    for item in source:
        if isinstance(item,str):
            if not item.endswith(':') or item[:-1] in labels:raise AsmError(f'bad or duplicate label {item!r}')
            labels[item[:-1]]=pc
        else:pc+=len(_encode(item,None,pc))
    words=[];previous=None
    for item in source:
        if isinstance(item,str):continue
        new=_encode(item,labels,base+len(words))
        if previous in ('run_next_if_negative','skip_next_if_negative','skip_if_bit0') and len(new)!=1:raise AsmError('a skip must be followed by a one-word instruction')
        if item[0] in ('run_next_if_negative','skip_next_if_negative') and previous!='fsub':
            raise AsmError('a flag skip must directly follow the fsub that sets the flags (only that pairing is used here)')
        for w in new:
            text,status=isa.decode(w)
            if status!='X' and w!=0xa00e0000:raise AsmError(f'{item}: word {w:#010x} ({text}) is not a form executed on the pedal')   # end word: see ('end',)
        words+=new;previous=item[0]
    if base+len(words)>0x1000:raise AsmError('program runs past PC 0xfff')
    return words


def listing(words,base):
    return '\n'.join(f'{pc:04x}  {w:08x}  {text}' for pc,w,text,_ in isa.listing(words,base))


def biquad_block(window, cells, name):
    """Source for one biquad over a 64-sample window, in place: y = b0 x + b1 x1 + b2 x2 - (a1 y1 + a2 y2)
    (float32: products rounded, then added - the measured multiply-accumulate). Coefficients at
    D[cells..cells+4] = b0 b1 b2 a1 a2 (normalized, a0 = 1; no rsqrt scale here), state at
    D[cells+5..cells+8] = x1 x2 y1 y2, written back at the end. Uses every register r0..r13."""
    c = cells
    return [('li', 0, window), ('li', 1, 0x40),
            ('load', 2, c), ('load', 3, c + 1), ('load', 4, c + 2), ('load', 5, c + 3), ('load', 6, c + 4),
            ('load', 7, c + 5), ('load', 8, c + 6), ('load', 9, c + 7), ('load', 10, c + 8),
            name + ':',
            ('load_ind', 11, 0),                 # x
            ('fmul', 12, 2, 11), ('fmac', 12, 3, 7), ('fmac', 12, 4, 8),    # acc = b0 x + b1 x1 + b2 x2
            ('mov', 8, 7), ('mov', 7, 11),       # x2 = x1; x1 = x
            ('fmul', 11, 5, 9), ('fmac', 11, 6, 10),                        # t = a1 y1 + a2 y2
            ('fsub', 13, 12, 11),                # y = acc - t
            ('mov', 10, 9), ('mov', 9, 13),      # y2 = y1; y1 = y
            ('store_inc', 0, 13),
            ('loop', 1, name),
            ('store', 7, c + 5), ('store', 8, c + 6), ('store', 9, c + 7), ('store', 10, c + 8)]


def fir_block(window, taps, hist, n, name):
    """Source for an n-tap FIR over a 64-sample window, in place, using the dot block word:
    y[i] = sum_k h[k] x[i-k]. Cells: taps D[taps..taps+n-1] hold h REVERSED (taps[j] = h[n-1-j]);
    hist D[hist..hist+n+62] keeps the last n-1 inputs of the previous block followed by this block.
    n <= 65 so the end-of-block shift copy never overlaps (overlapping copies are unmeasured).
    dot is measured (dot_order_0/1, 2026-10-20): sequential, products rounded then added, r11
    overwritten - the strict simulator runs this exactly."""
    if not 2 <= n <= 65: raise AsmError('fir_block: 2 <= n <= 65')
    return [('li', 9, window), ('li', 10, 0x40), ('li', 11, hist + n - 1), ('block', 'copy'),   # this block after the history
            ('li', 0, hist), ('li', 1, window), ('li', 2, 0x40), ('li', 3, taps), ('li', 4, n),
            name + ':',
            ('mov', 8, 3), ('mov', 9, 0), ('mov', 10, 4), ('block', 'dot'),     # r11 = taps . hist[i..i+n-1]
            ('store_inc', 1, 11),
            ('load_inc', 5, 0),                                                  # r0 += 1 (value unused)
            ('loop', 2, name),
            ('li', 9, hist + 64), ('li', 10, n - 1), ('li', 11, hist), ('block', 'copy')]   # keep the last n-1 inputs


def fir_long_block(window, taps, hist, n, name):
    """Like fir_block for n up to 0x1000 taps (cab impulse responses): the n-1 sample history is
    shifted down in 64-word chunks, each copy moving data exactly 64 words, so source and
    destination never overlap (overlapping block copies are unmeasured). Taps reversed as in
    fir_block; hist holds n + 63 cells. Cost ~1.4e-5 DSP per tap-sample (FIR LowPass, MOD041)."""
    if not 2 <= n <= 0x1000: raise AsmError('fir_long_block: 2 <= n <= 4096')
    src = [('li', 9, window), ('li', 10, 0x40), ('li', 11, hist + n - 1), ('block', 'copy'),
           ('li', 0, hist), ('li', 1, window), ('li', 2, 0x40), ('li', 3, taps), ('li', 4, n),
           name + ':',
           ('mov', 8, 3), ('mov', 9, 0), ('mov', 10, 4), ('block', 'dot'),
           ('store_inc', 1, 11), ('load_inc', 5, 0), ('loop', 2, name)]
    left, k = n - 1, 0
    while left > 0:
        L = min(64, left)
        src += [('li', 9, hist + 64 * (k + 1)), ('li', 10, L), ('li', 11, hist + 64 * k), ('block', 'copy')]
        left -= L; k += 1
    return src
