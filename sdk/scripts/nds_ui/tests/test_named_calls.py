"""Constant call naming must preserve all non-target tokens and dynamic calls."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from nds_ui.named_calls import rewrite, definitions


class NamedCallsTests(unittest.TestCase):
    def test_only_indexed_function_targets_change(self):
        source = '((stock_fn_t)(uintptr_t)(0x177aa))(a,26); ((stock_fn_t)(uintptr_t)(0x12345))(b);'
        result, targets = rewrite(source, {0x177aa})
        self.assertEqual(targets, {0x177aa})
        self.assertTrue(result.endswith('((stock_fn_t)(uintptr_t)(gp50_absolute_177aa))(a,26); ((stock_fn_t)(uintptr_t)(0x12345))(b);'))
        self.assertIn('extern unsigned long gp50_absolute_177aa();', result)

    def test_float_arguments_and_dynamic_targets_remain(self):
        source = 'stock_call_f((io), (0x177aa), (index), (bits)); stock_call_rf((io), (address));'
        result, targets = rewrite(source, {0x177aa})
        self.assertEqual(targets, {0x177aa})
        self.assertTrue(result.endswith('stock_call_f((io), ((uint32_t)(uintptr_t)gp50_absolute_177aa), (index), (bits)); stock_call_rf((io), (address));'))

    def test_memory_and_other_casts_remain(self):
        source = '*(uint8_t *)(uintptr_t)(0x177aa); ((other_fn)(uintptr_t)(0x177aa))(a);'
        self.assertEqual(rewrite(source, {0x177aa}), (source, set()))

    def test_definitions_are_exact_and_sorted(self):
        self.assertEqual(definitions({0x177aa, 0x10000}), 'gp50_absolute_10000 = 0x10000;\ngp50_absolute_177aa = 0x177aa;\n')


if __name__ == '__main__': unittest.main()
