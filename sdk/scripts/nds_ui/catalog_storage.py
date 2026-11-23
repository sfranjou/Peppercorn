"""Checked in-container E placement for immutable catalog data and C code/rodata.

The legacy single reservation keeps its section names and byte layout. Multi-span
configs explicitly assign whole source objects to named spans inside known erased
stock ranges. No E growth, automatic spill, or movement of stock assets is allowed.
"""
import hashlib, re, subprocess
from pathlib import Path

ADDRESS = 0x1a4000
END = 0x1a6000
CODE_ADDRESS = 0x1a6000
CODE_END = 0x1a9600
FILE_BASE = 0x190000
# First valid aligned addresses after factory presets, catalog descriptors and
# boot-card assets respectively. apply() additionally checks the actual parent.
CODE_RANGES = ((0x19d9a8, 0x1a0000), (0x1a4c44, 0x1a9600), (0x1b0114, 0x1b8000))
def code_ranges(cfg=None):
    from .expanded_e import enabled, GROWTH_RANGE
    return CODE_RANGES + ((GROWTH_RANGE,) if enabled(cfg) else ())


RESERVATIONS = {'.catalog_ext': (ADDRESS, END), '.e_text': (CODE_ADDRESS, CODE_END), '.e_rodata': (CODE_ADDRESS, CODE_END)}


def code_spans(cfg):
    """Validated (name, start, end, sources) spans; empty name is legacy layout."""
    spec = (cfg or {}).get('region_e_code')
    if not spec:
        return []
    if spec == {"placement": "auto"}:
        rows = (cfg or {}).get("_region_e_resolved", [])
        if not rows:
            return []
        spec = {"spans": rows}
    multi = 'spans' in spec
    if multi and set(spec) != {'spans'}:
        raise ValueError('multi-span E config cannot mix legacy fields')
    rows = spec['spans'] if multi else [spec]
    if not isinstance(rows, list) or not rows:
        raise ValueError('region_e_code needs nonempty spans')
    spans, names, stems = [], set(), set()
    for row in rows:
        name = row.get('name', '') if multi else ''
        if multi and (not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', name)):
            raise ValueError('invalid E span name')
        lo, hi = int(row['address'], 16), int(row['end'], 16)
        if lo % 4 or hi % 4 or not any(a <= lo < hi <= b for a, b in code_ranges(cfg)):
            raise ValueError('E span outside known in-container erased ranges or unaligned')
        if not multi and (lo, hi) != (CODE_ADDRESS, CODE_END):
            raise ValueError('legacy E layout must use [0x1a6000,0x1a9600)')
        if name in names or any(lo < b and a < hi for _, a, b, _ in spans):
            raise ValueError('duplicate name or overlapping E spans')
        sources = row['sources']
        if not isinstance(sources, list) or not sources:
            raise ValueError('E span needs source objects')
        for src in sources:
            if not isinstance(src, str) or Path(src).suffix != '.c' or Path(src).stem in stems:
                raise ValueError('invalid or duplicate E source object stem')
            stems.add(Path(src).stem)
        names.add(name)
        spans.append((name, lo, hi, sources))
    return spans


def e_code_stems(cfg):
    return [Path(s).stem for _, _, _, sources in code_spans(cfg) for s in sources]


def section_name(kind, name):
    return '.e_' + kind + ('_' + name if name else '')


def code_sections(cfg):
    return [section_name('text', name) for name, _, _, _ in code_spans(cfg)]


def linker_clause(cfg, features, work, active_stems=None):
    out = ''
    mode = (cfg or {}).get('catalog_descriptor_storage')
    if mode is not None and 'catalog_c' in features:
        if mode != 'region_e_1a4000':
            raise ValueError('unknown catalog descriptor storage: ' + str(mode))
        # The descriptors come from whichever catalog object this link has (own_catalog_entries with stock_in_place).
        stem = 'own_catalog_entries' if (Path(work) / 'own_catalog_entries.o').exists() and (active_stems is None or 'own_catalog_entries' in active_stems) else 'catalog_target'
        out += f'.catalog_ext {ADDRESS:#x} : {{ {work}/{stem}.o(.rodata.ext_desc_*) }}\n'
    for name, lo, hi, sources in code_spans(cfg):
        # Canonical per-feature links contain only that feature's objects.
        stems = [Path(s).stem for s in sources if (Path(work) / (Path(s).stem + '.o')).exists() and (active_stems is None or Path(s).stem in active_stems)]
        if not stems:
            continue
        text, rodata = section_name('text', name), section_name('rodata', name)
        out += f'{text} {lo:#x} : {{ ' + ' '.join(f'{work}/{s}.o(.text .text.*)' for s in stems) + ' }\n'
        out += f'{rodata} ALIGN(4) : {{ ' + ' '.join(f'{work}/{s}.o(.rodata .rodata.*)' for s in stems) + ' }\n'
        out += f'ASSERT(ADDR({rodata}) + SIZEOF({rodata}) <= {hi:#x}, "E span {name or "legacy"} overflow")\n'
    return out


def extract(cfg, work, gcc_bin, *, require_catalog=True):
    """Extract each configured ELF section with a separate checked payload range."""
    spans = code_spans(cfg)
    if not cfg.get('catalog_descriptor_storage') and not spans:
        return []
    if cfg.get('catalog_descriptor_storage') not in (None, 'region_e_1a4000'):
        raise ValueError('unknown catalog descriptor storage')
    elf = max((p for p in work.glob('*.elf') if not p.name.endswith('.disassembly.elf')), key=lambda q: q.stat().st_mtime)
    hdr = subprocess.check_output([str(gcc_bin / 'nds32le-elf-objdump'), '-h', str(elf)], text=True)
    specs = [('.catalog_ext', ADDRESS, END, True, 'immutable own effect descriptor arrays')]
    for name, lo, hi, _ in spans:
        specs += [(section_name('text', name), lo, hi, True, 'C code executed in place from region E (code room step 3)'),
                  (section_name('rodata', name), lo, hi, False, 'read-only data of the region-E C code')]
    blobs = []
    for section, lo, hi, at_start, reason in specs:
        m = re.search(r'\s' + re.escape(section) + r'\s+([0-9a-f]+)\s+([0-9a-f]+)', hdr)
        if not m:
            if section == '.catalog_ext' and cfg.get('catalog_descriptor_storage') and require_catalog:
                raise ValueError('missing external catalog section')
            continue
        size, address = (int(x, 16) for x in m.groups())
        if not size:
            continue
        if address < lo or (at_start and address != lo) or address + size > hi:
            raise ValueError(f'{section} exceeds its reservation [{lo:#x},{hi:#x}): {address:#x}+{size:#x}')
        out = work / (section.strip('.') + '.bin')
        subprocess.run([str(gcc_bin / 'nds32le-elf-objcopy'), '-O', 'binary', '-j', section, str(elf), str(out)], check=True)
        raw = out.read_bytes()
        if len(raw) != size:
            raise ValueError(section + ' size mismatch')
        blobs.append(dict(region='e', section=section, address=address, offset=address-FILE_BASE,
                          bytes=raw, sha256=hashlib.sha256(raw).hexdigest(), reason=reason))
    return blobs


def apply(parent_e, blobs, cfg=None):
    result = bytearray(parent_e)
    used = set()
    for b in blobs:
        address, raw, offset = b['address'], b['bytes'], b['offset']
        inside = any(lo <= address < address+len(raw) <= hi for lo, hi in ((ADDRESS, END), *code_ranges(cfg)))
        if b['region'] != 'e' or offset != address-FILE_BASE or not inside:
            raise ValueError('invalid external region/range')
        span = set(range(offset, offset+len(raw)))
        if used & span or len(result[offset:offset+len(raw)]) != len(raw):
            raise ValueError('overlapping or truncated external span')
        if bytes(result[offset:offset+len(raw)]) != b'\xff'*len(raw):
            raise ValueError('external destination is not erased')
        if hashlib.sha256(raw).hexdigest() != b['sha256']:
            raise ValueError('external payload identity')
        result[offset:offset+len(raw)] = raw
        used |= span
    return bytes(result)
