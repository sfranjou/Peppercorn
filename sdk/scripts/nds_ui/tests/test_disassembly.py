from pathlib import Path
import subprocess
import tempfile
import unittest
from nds_ui.disassembly import mapped_view

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / 'tools/nds32/prefix/bin'


class DisassemblyTests(unittest.TestCase):
    def test_relocated_mapping_preserves_table_and_next_instruction(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'work/nds_space_refactor') as tmp:
            folder=Path(tmp)
            source=folder/'fixture.s'; elf=folder/'fixture.o'
            source.write_text('.section .hole_test,"ax"\nret5 $lp\n.byte 0x24\n.byte 0x3e\n.byte 0x5c\n.byte 0x4c\n.byte 0x44\n.byte 0x24\nbnez38 $r4, .\n')
            subprocess.run([str(TOOLS/'nds32le-elf-as'),str(source),'-o',str(elf)],check=True)
            original=elf.read_bytes()
            view,names=mapped_view(elf,['.hole_test'],TOOLS/'nds32le-elf-objcopy')
            self.assertNotEqual(view.suffix,'.elf')  # views must not enter final-ELF discovery
            result=subprocess.check_output([str(TOOLS/'nds32le-elf-objdump'),'-d','-j',names['.hole_test'],str(view)],text=True)
            self.assertEqual(elf.read_bytes(),original)
            self.assertEqual(result.count('.byte'),6)
            self.assertIn('bnez38',result)
            self.assertNotIn('*unknown*',result)
