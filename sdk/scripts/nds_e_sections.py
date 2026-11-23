"""Read final ELF E sections and bind their bytes to the composed E image."""
import struct


def verify(elf, region_e, base=0x190000):
    assert elf[:6] == b'\x7fELF\x01\x01', 'expected ELF32 little endian'
    shoff = struct.unpack_from('<I', elf, 32)[0]
    stride, count, names_index = struct.unpack_from('<HHH', elf, 46)
    assert stride == 40 and count and names_index < count
    sections = [struct.unpack_from('<10I', elf, shoff + i * stride) for i in range(count)]
    strings = sections[names_index]
    names = elf[strings[4]:strings[4] + strings[5]]
    rows = []
    for name, typ, flags, address, offset, size, *_ in sections:
        if not flags & 2 or not size or address < base:
            continue
        label = names[name:names.index(b'\0', name)].decode('ascii')
        assert typ == 1 and not flags & 1, ('unexpected E section type/permissions', label)
        assert base <= address < address + size <= base + len(region_e), (label, 'E bounds')
        raw = elf[offset:offset + size]
        assert len(raw) == size and raw == region_e[address-base:address-base+size], (label, 'ELF/image mismatch')
        assert not any(address < r['end'] and r['address'] < address+size for r in rows), label
        rows.append(dict(name=label, address=address, end=address+size, executable=bool(flags & 4)))
    return rows
