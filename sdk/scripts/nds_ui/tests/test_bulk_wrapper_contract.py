"""Negative controls for independently reviewed bulk assembly wrapper chains."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_nds_code_holes as holes


class BulkWrapperContractTests(unittest.TestCase):
    def setUp(self):
        self.labels = {'legacy_w4_open': 0x171000, 'legacy_w4_close': 0x171100,
                       'gr_close': 0x171200, 'nds_bulk_1cc5c': 0x120000,
                       'nds_bulk_1d2bc': 0x120100, 'nds_bulk_16254': 0x171300,
                       'nds_bulk_midi_context_c': 0x120200}
        self.starts = {0x120000, 0x120100, 0x120200}
        self.state = 0x20001234
        assign = holes.API.mod026_assign_state
        addr = [('sethi', f'$r2, #{assign >> 12:#x}'),
                ('ori', f'$r2, $r2, #{assign & 0xfff:#x}')]
        self.rows = {
            0x171000: addr + [('movi', '$r3, #0'), ('swi', '$r3, [$r2 + #0]'), ('j', '0x120000')],
            0x171100: addr + [('movi', '$r3, #0'), ('swi', '$r3, [$r2 + #0]'), ('j', '0x120100')],
            0x171200: [('sethi', '$r2, #0x20001'), ('ori', '$r2, $r2, #0x234'), ('movi', '$r3, #0'),
                       ('swi', '$r3, [$r2 + #0x5c]'), ('swi', '$r3, [$r2 + #0x88]'),
                       ('swi', '$r3, [$r2 + #0x8c]'), ('swi', '$r3, [$r2 + #0x90]'), ('j', '0x171100')],
            0x171300: [('mov55', '$r4, $r6'), ('j', '0x120200')],
        }

    def run_check(self, rows=None, labels=None, starts=None):
        fixture = self.rows if rows is None else rows
        def disassemble(_binary, at, end):
            # Respect the checker's requested byte range, as objdump does.
            address = at
            result = []
            for op, operands in fixture[at]:
                if address >= end:
                    break
                result.append((address, op, operands))
                address += 2 if op == 'mov55' else 4
            return result
        with patch.object(holes, 'objdump_raw', side_effect=disassemble):
            return holes.bulk_wrapper_targets(b'', labels or self.labels,
                                              self.starts if starts is None else starts, self.state)

    def rejected(self, address, index, replacement):
        rows = copy.deepcopy(self.rows)
        rows[address][index] = replacement
        with self.assertRaises(AssertionError):
            self.run_check(rows)

    def test_accepts_reviewed_chains_and_midi_adapter(self):
        self.assertEqual(self.run_check(), {0x1cc5c: 0x171000, 0x1d2bc: 0x171200, 0x16254: 0x171300})

    def test_optional_midi_adapter_absent(self):
        labels = dict(self.labels)
        del labels['nds_bulk_midi_context_c']
        self.assertEqual(self.run_check(labels=labels), {0x1cc5c: 0x171000, 0x1d2bc: 0x171200})

    def test_wrong_assignment_address_or_value_rejected(self):
        self.rejected(0x171000, 1, ('ori', '$r2, $r2, #0x123'))
        self.rejected(0x171100, 2, ('movi', '$r3, #1'))
        self.rejected(0x171100, 3, ('swi', '$r4, [$r2 + #0]'))

    def test_wrong_state_and_store_offset_rejected(self):
        self.rejected(0x171200, 0, ('sethi', '$r2, #0x20002'))
        self.rejected(0x171200, 4, ('swi', '$r3, [$r2 + #0x84]'))
        self.rejected(0x171200, 6, ('swi', '$r3, [$r2 + #0x8c]'))

    def test_wrong_tail_and_non_function_start_rejected(self):
        self.rejected(0x171000, 4, ('j', '0x120100'))
        self.rejected(0x171200, 7, ('j', '0x120100'))
        self.rejected(0x171300, 1, ('j', '0x120000'))
        with self.assertRaises(AssertionError):
            self.run_check(starts={0x120000, 0x120100})

    def test_extra_or_wrong_instruction_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0x171200].insert(3, ('swi', '$r3, [$r2 + #0x94]'))
        with self.assertRaises(AssertionError):
            self.run_check(rows)
        self.rejected(0x171000, 3, ('jal', '0x120000'))
        self.rejected(0x171300, 0, ('mov55', '$r4, $r5'))


if __name__ == '__main__':
    unittest.main()
