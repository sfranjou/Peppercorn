"""Build stock gain-reduction support for the reviewed MOD154 ARM layout."""
import hashlib
import json
from pathlib import Path

from sdk.build_capture import require, run, symbols

ROOT = Path(__file__).resolve().parent
ARM_BASE = 0x4000
PARENT_SHA256 = '0f236bb5502c58ebe5ac5c67ec66199a42d6d3ec86cc78019c7019dfd1cfc87d'
RESERVATIONS = {
    'patch': (0x53f4, 0x53f8),
    'take': (0xfee8, 0xff34),
    'observer': (0xff38, 0xffb0),
    'pack': (0xffb0, 0x10000),
    'reply': (0x11978, 0x11b1c),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_and_bind(parent, out, clang, arm):
    """Return the region and a receipt binding each installed section to its ELF."""
    require(sha(parent) == PARENT_SHA256, 'stock GR requires the reviewed MOD154 ARM region')
    require(parent[0x13f4:0x13fc] == bytes.fromhex('64692946a0470020'), 'stock GR wrapper changed')
    out.mkdir(parents=True, exist_ok=True)
    resources = ROOT / 'resources'
    source = resources / 'arm'
    observer = out / 'stock_gr_observer.o'
    reply = out / 'stock_gr_reply.o'
    elf = out / 'stock_gr.elf'
    run([arm / 'arm-none-eabi-as', source / 'stock_gr_observer.S', '-o', observer])
    run([clang, '--target=arm-none-eabi', '-mcpu=cortex-m4', '-mthumb', '-mfloat-abi=soft',
         '-Oz', '-ffreestanding', '-fno-builtin', '-fno-jump-tables', '-ffunction-sections',
         '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-fstack-usage',
         '-Wall', '-Wextra', '-Werror', '-I', resources, '-DGP50_METER_REPLY',
         '-DGP50_STOCK_GR_REPLY', '-c', source / 'lease_reply.c', '-o', reply])
    run([arm / 'arm-none-eabi-ld', '--no-undefined', '-T', source / 'stock_gr_layout.ld',
         '-Map', out / 'stock_gr.map', '-o', elf, observer, reply])
    names = symbols(elf, arm)
    require(names['gp50_lease_reply'] == RESERVATIONS['reply'][0], 'lease reply entry changed')
    region = bytearray(parent)
    sections = {}
    for name, (start, end) in RESERVATIONS.items():
        section = '.stock_gr_' + name
        lo, hi = start - ARM_BASE, end - ARM_BASE
        if name not in ('patch', 'reply'):
            require(parent[lo:hi] == b'\xff' * (hi - lo), 'stock GR reservation occupied: ' + name)
        output = out / (section[1:] + '.bin')
        run([arm / 'arm-none-eabi-objcopy', '-O', 'binary', '-j', section, elf, output])
        data = output.read_bytes()
        require(0 < len(data) <= hi - lo, 'stock GR section exceeds reservation: ' + name)
        region[lo:lo + len(data)] = data
        sections[name] = dict(address=hex(start), size=len(data), sha256=sha(data))
    region = bytes(region)
    (out / 'stock_gr.lst').write_text(run([arm / 'arm-none-eabi-objdump', '-d', elf]))
    receipt = dict(parent_sha256=PARENT_SHA256, output_sha256=sha(region),
                   elf_sha256=sha(elf.read_bytes()), sections=sections,
                   stack_usage=(out / 'stock_gr_reply.su').read_text())
    (out / 'stock_gr_build.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return region, receipt


def bind_container(root, parent, out, clang, arm):
    """Bind the component to the selected container while retaining its other regions."""
    import firmware_verify
    import htfw_pack

    original = (root / parent['image']).read_bytes()
    require(sha(original) == parent['sha256'], 'stock GR container identity')
    records, integrity = firmware_verify.decode(original)
    require(integrity['all_region_crcs_ok'], 'stock GR container CRCs')
    regions = {key: data for key, _, data in records}
    regions['c'], _ = build_and_bind(regions['c'], out, clang, arm)
    header, _ = htfw_pack.parse_template(original)
    encoded = htfw_pack.build(header, [(key, address, regions[key]) for key, address, _ in records],
                              compressed=True)
    decoded, integrity = firmware_verify.decode(encoded)
    require(integrity['all_region_crcs_ok'] and decoded == [
        (key, address, regions[key]) for key, address, _ in records
    ], 'stock GR container round trip')
    target = out / 'container.bin'
    target.write_bytes(encoded)
    return dict(parent, image=str(target.relative_to(root)), sha256=sha(encoded))
