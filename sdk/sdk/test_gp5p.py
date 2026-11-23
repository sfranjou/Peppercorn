"""GP5P validators: host (sdk/copro/gp5p.py) and pedal (sdk/effects/ns_capture_v5/gp5p_validate.h, compiled natively)
must agree on examples, rule violations and mutated programs; packing produces a valid 2,696-byte record."""
import ctypes, random, struct, subprocess, sys, unittest, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(ROOT)]
from sdk.copro import asm, gp5p
from sdk.user_programs import examples as E
LIB = ROOT / 'work/gp5p/libgp5p.dylib'


def native():
    src = ROOT / 'work/gp5p/native.c'
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text('#include "gp5p_validate.h"\nuint32_t validate_c(const uint32_t *w, uint32_t n, uint32_t budget, uint32_t *bound, uint32_t *pc) { return gp5p_validate(w, n, budget, bound, pc); }\n')
    subprocess.run(['clang', '-O1', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT / 'sdk/effects/ns_capture_v5'), str(src), '-o', str(LIB)], check=True)
    lib = ctypes.CDLL(str(LIB)); lib.validate_c.restype = ctypes.c_uint32
    return lib


def c_validate(lib, words, budget=gp5p.BUDGET):
    arr = (ctypes.c_uint32 * max(1, len(words)))(*words); b = ctypes.c_uint32(); pc = ctypes.c_uint32()
    code = lib.validate_c(arr, len(words), budget, ctypes.byref(b), ctypes.byref(pc))
    return (gp5p.ERRORS[code], pc.value if code else b.value)


def py_validate(words, budget=gp5p.BUDGET):
    try: return ('ok', gp5p.validate(words, budget))
    except gp5p.Reject as r: return (r.code, r.pc)


class GP5P(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.lib = native()

    def test_examples_accepted_identically(self):
        for name in E.PROGRAMS:
            code, data, base, zero, knobs = E.build(name)
            self.assertEqual(py_validate(code), c_validate(self.lib, code), name); self.assertEqual(py_validate(code)[0], 'ok')
            rec = gp5p.pack(code, data, base, zero, knobs, name)
            self.assertEqual(len(rec), 2696); self.assertEqual(rec[:4], b'GP5P')
            self.assertEqual(struct.unpack_from('<I', rec, 12)[0], zlib.crc32(rec[128:128 + 4 * (len(code) + len(data))]) & 0xffffffff)

    def test_rule_violations(self):
        U = gp5p.USER_PC
        cases = {
            'form': [0x12345678, asm.assemble([('jump', 0xe00)], U + 1)[0]],
            'end': asm.assemble([('li', 0, 1), ('li', 1, 2)], U),
            'target': asm.assemble([('li', 0, 1), ('jump', 0x500)], U),
            'loop': asm.assemble([('li', 1, 4), 'a:', ('li', 2, 4), 'b:', ('loop', 1, 'a'), ('loop', 2, 'b'), ('jump', 0xe00)], U),
            'counter': asm.assemble([('load', 1, 0x3b0), 'a:', ('loop', 1, 'a'), ('jump', 0xe00)], U),
            'pointer': asm.assemble([('load', 0, 0x3b0), ('load_ind', 1, 0), ('jump', 0xe00)], U),
            'address': asm.assemble([('load', 0, 0x398), ('jump', 0xe00)], U),
            'count': asm.assemble([('li', 9, 0x13), ('li', 11, 0x3b0), ('load', 10, 0x3b0), ('block', 'copy'), ('jump', 0xe00)], U),
            'bound': asm.assemble([('li', 1, 0x7fff), 'a:', ('li', 2, 0x7fff), 'b:', ('loop', 2, 'b'), ('loop', 1, 'a'), ('jump', 0xe00)], U),
        }
        cases['counter_written'] = asm.assemble([('li', 1, 4), 'a:', ('li', 1, 3), ('loop', 1, 'a'), ('jump', 0xe00)], U)
        cases['pointer_hi'] = [0x70c60000, 0x7086_03b0][:1] + asm.assemble([('load_ind', 1, 0), ('jump', 0xe00)], U + 1)
        for name, words in cases.items():
            p, c = py_validate(words), c_validate(self.lib, words)
            self.assertEqual(p, c, name); self.assertNotEqual(p[0], 'ok', name)
            want = name.split('_')[0] if name in gp5p.ERRORS or name.split('_')[0] in gp5p.ERRORS else None
            if name in ('form', 'end', 'target', 'loop', 'pointer', 'address', 'count', 'bound'): self.assertEqual(p[0], name, (name, p))
        self.assertEqual(py_validate(cases['counter_written'])[0], 'counter')

    def test_mutated_programs_agree(self):
        rng = random.Random(7); pool = []
        for name in E.PROGRAMS: pool.append(E.build(name)[0])
        forms = sorted({w for p in pool for w in p})
        agree = verdicts = 0
        for case in range(3000):
            words = list(rng.choice(pool))
            for _ in range(rng.randint(1, 3)):
                i = rng.randrange(len(words)); r = rng.random()
                if r < 0.4: words[i] = rng.choice(forms)
                elif r < 0.6: words[i] ^= 1 << rng.randrange(32)
                elif r < 0.8: words[i] = (words[i] & 0xffff0000) | rng.randrange(0x10000)
                elif r < 0.9 and len(words) > 3: del words[i]
                else: words.insert(i, rng.choice(forms))
            p, c = py_validate(words), c_validate(self.lib, words)
            self.assertEqual(p, c, (case, [hex(w) for w in words]))
            verdicts += p[0] == 'ok'
        self.assertGreater(verdicts, 50)


if __name__ == '__main__':
    unittest.main()
