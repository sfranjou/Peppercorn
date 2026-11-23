"""NDS32 encoder for the instruction subset the NDS UI generator emits, plus the Source
builder and the linker that turns rows into bytes.

Not a general assembler. Every mnemonic here is checked against every instruction the
installed Ghidra NDS32 assembler produced for earlier images (work/*/spec.tsv paired with
assembled.tsv, plus patches.json; tests/test_asm.py). The tier-c full proof re-assembles
the spec with Ghidra and requires identical bytes, so a wrong encoding cannot reach a
handover unnoticed. Instruction words are big-endian; data words are little-endian.
"""
import re

REG = {**{f'a{i}': i for i in range(6)}, **{f's{i}': 6 + i for i in range(9)}, 'ta': 15,
       **{f't{i}': 16 + i for i in range(10)}, 'p0': 26, 'p1': 27, 'fp': 28, 'gp': 29, 'lp': 30, 'sp': 31}
# Sizes follow build_ui_assignment_code.Source: these mnemonics are the 16-bit forms.
SHORT = ('mov55', 'ret5', 'push25', 'movpi45', 'lwi333', 'movi55')
LOAD_STORE = {'lbi': (0x00, 0), 'lhi': (0x01, 1), 'lwi': (0x02, 2), 'sbi': (0x08, 0),
              'shi': (0x09, 1), 'swi': (0x0a, 2), 'lbsi': (0x10, 0), 'lhsi': (0x11, 1)}
IMM15 = {'addi': (0x28, True), 'andi': (0x2a, False), 'xori': (0x2b, False), 'ori': (0x2c, False),
         'slti': (0x2e, True), 'sltsi': (0x2f, True)}
ALU1 = {'add': 0, 'sub': 1, 'and': 2, 'xor': 3, 'or': 4, 'nor': 5, 'slt': 6, 'slts': 7,
        'sll': 0xc, 'srl': 0xd, 'sra': 0xe}
ALU1_IMM5 = {'slli': 8, 'srli': 9, 'srai': 0xa}
BR2 = {'beqz': 2, 'bnez': 3, 'bgez': 4, 'bltz': 5, 'bgtz': 6, 'blez': 7}
PUSH25_RE = {'s0': 0, 's2': 1, 's4': 2, 's8': 3}


class AsmError(ValueError):
    pass


def _reg(name):
    try:
        return REG[name]
    except KeyError:
        raise AsmError('bad register ' + name) from None


def _imm(text):
    return int(text.strip(), 0)


def _signed(value, bits, what):
    if not -(1 << (bits - 1)) <= value < (1 << (bits - 1)):
        raise AsmError(f'{what} {value} outside signed {bits} bits')
    return value & ((1 << bits) - 1)


def _unsigned(value, bits, what):
    if not 0 <= value < (1 << bits):
        raise AsmError(f'{what} {value} outside unsigned {bits} bits')
    return value


def _mem(text):
    m = re.fullmatch(r'\[\s*(\w+)\s*([+-])\s*(\S+)\s*\]', text.strip())
    if not m:
        raise AsmError('bad memory operand ' + text)
    off = _imm(m[3])
    return _reg(m[1]), -off if m[2] == '-' else off


def _ops(text):
    # Split on commas outside brackets.
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def size_of(line):
    return 2 if line.startswith(SHORT) else 4


def encode(pc, line):
    """Encode one fully resolved instruction (no @labels) at address pc."""
    mn, _, rest = line.strip().partition(' ')
    ops = _ops(rest)
    w32 = lambda v: v.to_bytes(4, 'big')
    if mn in LOAD_STORE:
        opc, shift = LOAD_STORE[mn]
        rt = _reg(ops[0]); ra, off = _mem(ops[1])
        if off % (1 << shift):
            raise AsmError('misaligned offset ' + line)
        return w32(opc << 25 | rt << 20 | ra << 15 | _signed(off >> shift, 15, 'offset'))
    if mn in IMM15:
        opc, signed = IMM15[mn]
        v = _imm(ops[2])
        imm = _signed(v, 15, 'imm15') if signed else _unsigned(v, 15, 'imm15')
        return w32(opc << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | imm)
    if mn == 'zeb':
        return w32(0x2a << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | 0xff)
    if mn == 'movi':
        return w32(0x22 << 25 | _reg(ops[0]) << 20 | _signed(_imm(ops[1]), 20, 'movi'))
    if mn == 'sethi':
        return w32(0x23 << 25 | _reg(ops[0]) << 20 | _unsigned(_imm(ops[1]), 20, 'sethi'))
    if mn in ALU1:
        return w32(0x20 << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | _reg(ops[2]) << 10 | ALU1[mn])
    if mn in ALU1_IMM5:
        return w32(0x20 << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | _unsigned(_imm(ops[2]), 5, 'shift') << 10 | ALU1_IMM5[mn])
    if mn in ('seb', 'seh'):
        return w32(0x20 << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | {'seb': 0x10, 'seh': 0x11}[mn])
    if mn in ('divr', 'divsr'):
        # divr rt(quotient), rd(remainder), ra, rb
        return w32(0x20 << 25 | _reg(ops[0]) << 20 | _reg(ops[2]) << 15 | _reg(ops[3]) << 10 | _reg(ops[1]) << 5
                   | {'divr': 0x17, 'divsr': 0x16}[mn])
    if mn == 'mul':
        return w32(0x21 << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | _reg(ops[2]) << 10 | 0x24)
    if mn in ('j', 'jal'):
        target = _imm(ops[0])
        if (target | pc) & 1:
            raise AsmError('odd jump ' + line)
        return w32(0x24 << 25 | (mn == 'jal') << 24 | _signed((target - pc) >> 1, 24, 'jump'))
    if mn in ('beq', 'bne'):
        d = _imm(ops[2]) - pc
        if d & 1:
            raise AsmError('odd branch ' + line)
        return w32(0x26 << 25 | _reg(ops[0]) << 20 | _reg(ops[1]) << 15 | (mn == 'bne') << 14 | _signed(d >> 1, 14, 'branch'))
    if mn in BR2:
        d = _imm(ops[1]) - pc
        if d & 1:
            raise AsmError('odd branch ' + line)
        return w32(0x27 << 25 | _reg(ops[0]) << 20 | BR2[mn] << 16 | _signed(d >> 1, 16, 'branch'))
    if mn == '.word':   # data word patch (little-endian; MOD056 diagnostics_c: handler-table words 0x140bc8 / 0x140c1c)
        return _unsigned(_imm(ops[0]), 32, 'word').to_bytes(4, 'little')
    w16 = lambda v: v.to_bytes(2, 'big')
    if mn == 'movi55':   # MOD056 diagnostics_c: byte-faithful copy of the MOD055 0x6002 receive stub
        return w16(0x8400 | _reg(ops[0]) << 5 | _signed(_imm(ops[1]), 5, 'movi55'))
    if mn == 'mov55':
        return w16(0x8000 | _reg(ops[0]) << 5 | _reg(ops[1]))
    if mn == 'ret5':
        return w16(0xdd80 | _reg(ops[0]))
    if mn == 'push25':
        imm = _imm(ops[1])
        if imm % 8:
            raise AsmError('push25 imm')
        return w16(0xfc00 | PUSH25_RE[ops[0]] << 5 | _unsigned(imm >> 3, 5, 'push25'))
    if mn == 'movpi45':
        r = _reg(ops[0]); r4 = r if r < 8 else r - 8 if 16 <= r < 24 else None
        if r4 is None:
            raise AsmError('movpi45 register')
        return w16(0xfa00 | r4 << 5 | _unsigned(_imm(ops[1]) - 16, 5, 'movpi45'))
    if mn == 'lwi333':
        rt = _reg(ops[0]); ra, off = _mem(ops[1])
        if rt > 7 or ra > 7 or off % 4:
            raise AsmError('lwi333 operands')
        return w16(0xa000 | rt << 6 | ra << 3 | _unsigned(off >> 2, 3, 'lwi333'))
    raise AsmError('unsupported mnemonic ' + mn)


class Source:
    """Row list compatible with scripts/build_ui_assignment_code.Source (same sizes and
    helpers), so feature code ported from the per-MOD generators emits identical rows."""

    def __init__(self):
        self.rows = []

    def label(self, name):
        self.rows.append((name, None, 0))

    def emit(self, text):
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                self.rows.append((None, line, size_of(line)))

    def address(self, r, v):
        self.emit(f'sethi {r},{v >> 12:#x}\nori {r},{r},{v & 4095:#x}')


def resolve(line, labels):
    return re.sub(r'@(\w+)', lambda m: hex(labels[m[1]]), line)


def assemble_rows(rows, base, labels):
    """Return (bytes, spec rows [(pc,size,text)]) for resolved rows starting at base."""
    out, spec, pc = bytearray(), [], base
    for name, line, size in rows:
        if line is None:
            continue
        text = resolve(line, labels)
        raw = encode(pc, text)
        if len(raw) != size:
            raise AsmError(f'size mismatch at {pc:#x}: {text}')
        out += raw; spec.append((pc, size, text)); pc += size
    return bytes(out), spec
