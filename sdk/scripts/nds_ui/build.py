"""Generate the NDS UI segment for a feature set: compose feature sections in the configured
layout, link labels, encode with nds_ui.asm, and derive hook patches from the features.

Outputs (work/nds_ui/<id>/): code.bin (BASE..end incl. data, 0xff padding), labels.json,
spec.tsv, source.nds, data.json, patch_spec.tsv, patches.json (old bytes from the parent),
layout.json, modules.json (per-module normalized byte hashes used by the test cache).
"""
import hashlib, importlib, json, os, re, struct, subprocess, sys, zlib
from pathlib import Path
from .asm import Source, assemble_rows, encode, resolve
from . import build_cache as BC

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
REGS = 's0 s1 s2 s3 s4 s5 s6 s7 s8 lp'.split()
ALL_FEATURES = ('telemetry', 'telemetry_c', 'home_meter', 'home_meter_c', 'mem_page', 'mem_page_c', 'gr_meter', 'gr_meter_c', 'admission', 'admission_c', 'refuse_c', 'catalog_c', 'ui_input_c', 'legacy_ui_c', 'host_layer_c', 'diagnostics_c', 'protocol_scalars_c', 'application_helpers_c', 'application_more_c', 'home_tick_c', 'tap_safe_c', 'data_access_c', 'userdata_access_c', 'userdata_events_c', 'userdata_fields_c', 'home_value_c', 'ui_render_c', 'parameter_tables_c', 'parameter_formats_c', 'ui_open_c', 'userdata_services_c', 'home_callbacks_c', 'window_common_c', 'data_control_c', 'widget_builders_c', 'widget_adapters_c', 'ui_consolidated_c', 'application_bulk_c', 'remaining_application_c', 'capture_status_c', 'footswitch_ab_c', 'external_components_c')
# C features (analysis/firmware/NDS_C_PLAN.md): compiled with the pinned local GCC, linked after the
# asm code+data, entry symbols added to the label table so asm hooks can `jal @symbol`.
GCC_BIN = ROOT / 'tools/nds32/prefix/bin'
C_FLAGS = ['-Os', '-ffreestanding', '-fno-common', '-ffunction-sections', '-fdata-sections', '-fno-builtin',
           '-mno-ext-perf2', '-mno-ext-string', '-mcmodel=large', '-fstack-usage', '-Wall', '-Wextra', '-Werror', '-std=c11']


def tag_name(f):
    """Case-tag name a feature answers to (a C port keeps its asm original's oracle cases)."""
    return getattr(feature(f), 'PROVIDES', f)


# Hard-float C (cfg "c_hard_float", 2026-10-22): the stock ABI passes/returns floats in fs0/fs1 and keeps fs6..fs11
# callee-saved. Only FPU forms whose emulation semantics are validated against GCC (work/nds_fpu_semantics) are allowed,
# and fs6..fs11 require explicit stack save/restore; fs12+ are forbidden. GCC passes -mabi=v2fp+, which this binutils spells v2fpp, so hard-float
# sources are compiled to assembly and assembled explicitly.
HARD_FLOAT = ['-mfloat-abi=hard', '-mext-fpu-sp']
VALIDATED_FPU = {'fcpysd', 'fmfdr', 'fmtdr', 'fadds', 'fsubs', 'fmuls', 'fdivs', 'fsqrts', 'fabss', 'fcpyss', 'fcpynss', 'fcmpeqs', 'fcmplts', 'fcmples', 'fcmpuns',
                 'fcmovns', 'fcmovzs', 'fsi2s', 'fui2s', 'fs2si.z', 'fs2ui.z', 'fmfsr', 'fmtsr', 'flsi', 'fssi', 'fls', 'fss'}


def fpu_instruction_bad(t, hard):
    m = t.split()[0] if t.split() else ''
    if not m.startswith('f') or m in ('fexti33',): return False
    if not hard: return True
    # fd0..fd2 alias caller-saved fs0..fs5; a double constant load is
    # permitted for the typed variadic adapter, independently of stack saves.
    if m == 'fldi' and re.fullmatch(r'fldi\s+\$fd[012], \[\$(?:r(?:[0-9]|[12][0-9]|3[01])|sp)(?: \+ #(?:0x[0-9a-f]+|[0-9]+))?\]', t): return False
    if m in ('fsdi', 'fldi'): return not re.fullmatch(r'f[sl]di\s+\$fd[345], \[\$sp( \+ #(0x[0-9a-f]+|\d+))?\]', t)   # fs6..fs11 save/restore only
    if m not in VALIDATED_FPU: return True
    return bool(re.search(r'\$fs(1[2-9]|[23][0-9])\b|\$fd([6-9]|[12][0-9]|3[01])\b', t))   # fs12+ never; fd0..fd2 are caller-saved double/variadic transport; fd3..fd5 require saves below


def compiler_identity(cfg=None):
    v = subprocess.run([str(GCC_BIN / 'nds32le-elf-gcc'), '-v'], capture_output=True, text=True).stderr
    extra = ' hard-float-features ' + ' '.join(HARD_FLOAT) if (cfg or {}).get('c_hard_float') else ''
    if (cfg or {}).get('c_named_stock_calls'): extra += ' named-stock-calls -mcmodel=medium -mconfig-fpu=0 -ffixed-$fs6 -ffixed-$fs7'
    return hashlib.sha256((v + ' '.join(C_FLAGS) + extra).encode()).hexdigest()


def _subset_fit(items,holes,reverse=False):

 rows={lo:[]for lo,_,_ in holes}
 remaining=sorted(items,key=lambda x:(-x[2],x[1],x[0]))
 for lo,hi,_ in sorted(holes,key=lambda h:((-(h[1]-h[0])if reverse else h[1]-h[0]),h[0])):
  start=(lo+1)&~1;cap=(hi-start)//2
  if cap<=0:continue
  eligible=[i for i in remaining if i[3]<=2 and i[2]%2==0 and i[2]<=cap*2]
  reachable=1;states=[];mask=(1<<(cap+1))-1
  for item in eligible:
   states.append((item,reachable));reachable=(reachable|(reachable<<(item[2]//2)))&mask
   if reachable&(1<<cap):break
  target=reachable.bit_length()-1;chosen=[]
  for item,previous in reversed(states):
   if not (previous&(1<<target)):
    chosen.append(item);target-=item[2]//2
  assert target==0
  at=start
  for obj,sec,size,al in reversed(chosen):rows[lo].append((obj,sec,at,size));at+=size
  chosen=set(chosen);remaining=[i for i in remaining if i not in chosen]
 # Leftovers of all alignments can consume remaining tails safely.
 tails=[((rows[lo][-1][2]+rows[lo][-1][3])if rows[lo]else lo,hi,lo)for lo,hi,_ in holes]
 extra=_first_fit(remaining,tails,'best')
 for start,hi,lo in tails:rows[lo].extend(extra[start])
 return rows


def _first_fit(items, holes, policy="first"):
    """Code room step 2: place movable .text input sections (obj, section, size, align) into holes [(lo, hi, entry)],
    first or best fit by decreasing size (deterministic order); returns {hole lo: [(obj, section, address, size)]}."""
    assert policy in ('first', 'best', 'subset'), policy
    if policy == 'subset':
        choices=[_first_fit(items,holes,'best'),_subset_fit(items,holes),_subset_fit(items,holes,True)]
        return max(choices,key=lambda rows:sum(x[3]for v in rows.values()for x in v))
    cursor = {lo: lo for lo, _, _ in holes}; out = {lo: [] for lo, _, _ in holes}
    for obj, sec, size, al in sorted(items, key=lambda x: (-x[2], x[1], x[0])):
        candidates = holes if policy == 'first' else sorted(holes, key=lambda h: (h[1] - ((cursor[h[0]] + al - 1) & ~(al - 1)) - size, h[0]))
        for lo, hi, _ in candidates:
            at = (cursor[lo] + al - 1) & ~(al - 1)
            if at + size <= hi: out[lo].append((obj, sec, at, size)); cursor[lo] = at + size; break
    return out


def _kept_text_sections(map_text):
    """(object, section, size) of every .text* input section kept in the output .text (ld -Map)."""
    body = map_text.split('Linker script and memory map', 1)[1]
    body = body.split('\n.text ', 1)[1].split('\n.rodata', 1)[0]
    return [(m.group(4), m.group(1), int(m.group(3), 16)) for m in re.finditer(r'^ (\.text\S*)\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+(\S+\.o)$', body, flags=re.M)
            if int(m.group(3), 16)]


def _section_align(obj):
    hdr = subprocess.run([str(GCC_BIN / 'nds32le-elf-objdump'), '-h', obj], capture_output=True, text=True).stdout
    return {m.group(1): 1 << int(m.group(2)) for m in re.finditer(r'^\s*\d+ (\S+)\s+[0-9a-f]+\s+[0-9a-f]+\s+[0-9a-f]+\s+[0-9a-f]+\s+2\*\*(\d+)', hdr, flags=re.M)}


def _section_sizes(obj):
    hdr = subprocess.check_output([str(GCC_BIN / 'nds32le-elf-objdump'), '-h', obj], text=True)
    return {m.group(1): int(m.group(2),16) for m in re.finditer(r'^\s*\d+ (\S+)\s+([0-9a-f]+)\s+[0-9a-f]+', hdr, flags=re.M)}


def c_artifact_name(features):
    """Stable filesystem-safe name; preserve earlier candidates' short names."""
    joined = '_'.join(features)
    return joined if len(joined.encode('utf-8')) <= 250 else 'features_' + hashlib.sha256(joined.encode('utf-8')).hexdigest()[:24]


from . import stock_in_place as SIP


def compile_c(f, base, work, cfg=None, canonical=False, asm_labels=None, parent_b=None, holes=None):
    """Compile and link C features at `base` (f: one name or a list linked together, so C
    features may call each other). Returns (bytes, symbols, insns, stack_usage).
    Gates: no undefined symbols beyond the stock-API map, no .data/.bss, no gp-relative or FPU forms.
    canonical=True (per-module cache hash): links one feature alone, other features' symbols at 0."""
    fs = [f] if isinstance(f, str) else list(f); work.mkdir(parents=True, exist_ok=True)
    sources = [(x, s) for x in fs for s in SIP.sources_of(feature(x), cfg) if s not in SIP.reverted(feature(x), cfg)[0]]
    active_stems = {Path(s).stem for _, s in sources}
    if len(active_stems) != len(sources):
        raise ValueError('C source object-name collision across core/components: ' + repr([s for _, s in sources]))
    if not canonical:
        from .catalog_storage import code_spans
        missing = {s for _, _, _, ss in code_spans(cfg) for s in ss} - {s for _, s in sources}
        if missing:
            raise ValueError('E sources absent from active features: ' + repr(sorted(missing)))
    for p in work.glob('*.su'):
        if p.stem not in active_stems: p.unlink()   # never mix stack usage from an earlier source set
    cache_implementation = BC.implementation(ROOT, GCC_BIN)
    for x in fs:
        for name, text in (feature(x).c_headers(cfg, parent_b) if hasattr(feature(x), 'c_headers') else {}).items(): (work / name).write_text(text)
    # sdk/nds/components last: gp50.h for ABI 3 authors
    inc = ['-I', str(ROOT / 'sdk/nds'), '-I', str(work), '-I', str(ROOT / 'sdk/nds/components')] + ['-D' + d for d in (cfg or {}).get('c_defines', ())]   # config-wide switches (e.g. GP50_FS_AB=1), same in canonical links
    objs = []; f = c_artifact_name(fs); entries = [e for x in fs for e in (feature(x).c_entries(cfg) if hasattr(feature(x), 'c_entries') else feature(x).C_ENTRIES)
               if e not in SIP.reverted(feature(x), cfg)[2]]   # GC roots: every linked entry must be one, or the canonical module hash misses it
    named_targets = set()
    named_mode = bool((cfg or {}).get('c_named_stock_calls'))
    if named_mode:
        from . import holes as HL, named_calls
        allowed_targets = set(HL.stock_facts()[2])
    for x, src in sources:   # c_sources: per-config list (MOD052 chains)
        o = work / (Path(src).stem + '.o'); objs.append(o)
        input_source = ROOT / src
        callback_flags = ['-include', str(work / 'component_callbacks.h'), '-fno-jump-tables'] if x == 'external_components_c' else []   # no .text jump tables (C round-trip gate, stack audit)
        model_flags = callback_flags + (['-mcmodel=medium', '-mconfig-fpu=0', '-ffixed-$fs6', '-ffixed-$fs7'] if named_mode else [])
        hard_source = bool((cfg or {}).get('c_hard_float') and getattr(feature(x), 'C_HARD_FLOAT', False) and src in getattr(feature(x), 'C_HARD_FLOAT_SOURCES', (src,)))
        hard_flags = HARD_FLOAT + list(getattr(feature(x), 'C_EXTRA_FLAGS', ())) if hard_source else []
        # Preprocessing on every build catches transitive/generated headers, macros and include resolution.
        r = subprocess.run([str(GCC_BIN / 'nds32le-elf-gcc'), *C_FLAGS, *model_flags, *hard_flags, *inc, '-E', str(input_source)], capture_output=True, text=True, cwd=work)
        if r.returncode: raise ValueError('C preprocessing failed: ' + r.stderr)
        preprocessed = r.stdout
        if named_mode:
            rewritten, targets = named_calls.rewrite(preprocessed, allowed_targets)
            named_targets |= targets
            input_source = o.with_suffix('.i'); input_source.write_text(rewritten)
        object_key = BC.key(cache_implementation, src, rewritten if named_mode else preprocessed, C_FLAGS, model_flags, hard_flags, inc, named_mode)
        receipt = o.with_suffix('.compile_cache.json')
        if BC.load(receipt, object_key) is not None:
            continue
        for stale in (o, o.with_suffix('.su'), o.with_suffix('.s')):
            stale.unlink(missing_ok=True)
        if (cfg or {}).get('c_hard_float') and getattr(feature(x), 'C_HARD_FLOAT', False) and src in getattr(feature(x), 'C_HARD_FLOAT_SOURCES', (src,)):   # per-source list (MOD053): integer-only modules stay soft-float
            # Per-feature hard float: GCC's assembly carries .abi_2fp_plus, which ld will not link with the soft-float
            # features; the directive is dropped so the object keeps the default ABI tag. Sound because no soft-float C
            # calls these functions: only stock code does, through hook sites, with the stock fs0 convention.
            s = o.with_suffix('.s')
            r = subprocess.run([str(GCC_BIN / 'nds32le-elf-gcc'), *C_FLAGS, *model_flags, *HARD_FLOAT, *getattr(feature(x), 'C_EXTRA_FLAGS', ()), *inc, '-S', str(input_source), '-o', str(s)], capture_output=True, text=True, cwd=work)
            if not r.returncode:
                s.write_text(''.join(l for l in s.read_text().splitlines(True) if l.strip() != '.abi_2fp_plus'))
                r = subprocess.run([str(GCC_BIN / 'nds32le-elf-as'), '-mfpu-sp-ext', str(s), '-o', str(o)], capture_output=True, text=True, cwd=work)
        else:
            r = subprocess.run([str(GCC_BIN / 'nds32le-elf-gcc'), *C_FLAGS, *model_flags, *inc, '-c', str(input_source), '-o', str(o)], capture_output=True, text=True, cwd=work)
        if r.returncode: raise ValueError('C compile failed: ' + r.stderr)
        BC.save(receipt, object_key, True, [p for p in (o, o.with_suffix('.su'), o.with_suffix('.s')) if p.exists()])
    stock = re.sub(r'SECTIONS\s*\{.*\}', '', (ROOT / 'sdk/nds/stock_api.ld').read_text(), flags=re.S)
    if named_mode:
        stock += '\n' + named_calls.definitions(named_targets)
        (work / 'named_stock_calls.json').write_text(json.dumps({f'gp50_absolute_{a:x}': hex(a) for a in sorted(named_targets)}, indent=2) + '\n')
    # Code room step 1 (MOD055+): parent-resident MOD026 helpers that are now C link to the C functions (feature
    # LINK_ALIASES); a canonical per-module link without the defining feature leaves them unresolved (0).
    for x in (cfg or {}).get('features') or ():
        if x in ALL_FEATURES:
            for name, sym in getattr(feature(x), 'LINK_ALIASES', {}).items():
                stock = re.sub(rf'^{name} = 0x[0-9a-fA-F]+;$', '' if canonical and x not in fs else f'{name} = {sym};', stock, flags=re.M)
    # _SDA_BASE_ pinned to the stock gp: C may not use gp (gate below), and the default value can land inside .text,
    # where objdump then splits an instruction at the symbol (MOD050, 2026-10-21). No code bytes depend on it.
    elf = work / (f + '.elf')
    def link(hole_sections=''):
        from .catalog_storage import linker_clause
        external = linker_clause(cfg, fs, work, active_stems)
        ordered = external + hole_sections if (cfg or {}).get('b_placement') else hole_sections + external
        (work / 'link.ld').write_text(stock + '\n_SDA_BASE_ = 0x20011658;' + f'\nSECTIONS {{ {ordered}. = {base:#x}; .text : {{ *(.text*) }} .rodata : {{ . = ALIGN(4); *(.rodata*) }}\n  .data : {{ *(.data*) *(.sdata*) }} .bss : {{ *(.bss*) *(.sbss*) *(COMMON) }}\n  /DISCARD/ : {{ *(.comment) *(.note*) }} }}\n')
        r = subprocess.run([str(GCC_BIN / 'nds32le-elf-ld'), '-T', str(work / 'link.ld'), '--gc-sections', *(['--unresolved-symbols=ignore-all'] if canonical else ['--no-undefined']),
                            *[str(o) for o in objs], '-o', str(elf), *sum([['-u', e] for e in entries], []), *(['-Map', str(work / 'link.map')] if holes is not None or (cfg or {}).get('region_e_code') == {'placement': 'auto'} else []),
                            *sum([['--defsym', f'{k}={v:#x}'] for k, v in (asm_labels or {}).items()], [])], capture_output=True, text=True)
        if r.returncode: raise ValueError('C link failed (undefined symbol outside the stock-API map?): ' + r.stderr)
    link()
    auto_report = None
    if not canonical and (cfg or {}).get('region_e_code') == {'placement': 'auto'}:
        from . import auto_place as AP, catalog_storage as ES
        if cfg.get('_region_e_resolved'):
            raise ValueError('automatic E plan must be derived from the current complete link')
        ledger = work / 'e_placement.json'
        auto_report = AP.from_link_map((work / 'link.map').read_text(), [s for _, s in sources],
                                      {str(o): _section_align(str(o)) for o in objs},
                                      ES.code_ranges(cfg), AP.load_previous(ledger),
                                      section_sizes={str(o): _section_sizes(str(o)) for o in objs})
        cfg['_region_e_resolved'] = AP.spans(auto_report)
        link()
    placed = {}; b_report = None
    if not canonical and (cfg or {}).get('b_placement'):
        from . import b_link as BL
        if holes is None: raise ValueError('stable B requires verified hole inventory')
        bc = cfg['b_placement']
        previous = BL.load_previous(ROOT / bc['ledger'], ROOT)
        b_report, placed, clauses = BL.propose((work / 'link.map').read_text(), objs,
            {str(o): _section_align(str(o)) for o in objs}, {str(o): _section_sizes(str(o)) for o in objs},
            holes, base, int(cfg['segment']['limit'],16), previous, bc.get('repack',False))
        link(clauses)
    elif holes is not None:   # code room step 2 (cfg code_holes): second link with .text input sections placed into dead stock bodies
        aligns = {str(o): _section_align(str(o)) for o in objs}
        items = [(obj, sec, size, max(2, aligns[obj].get(sec, 4))) for obj, sec, size in _kept_text_sections((work / 'link.map').read_text())]
        placed = {lo: v for lo, v in _first_fit(items, holes, (cfg or {}).get('code_holes', {}).get('placement', 'first')).items() if v}
        link(''.join(f'.hole_{lo:x} {lo:#x} : {{ ' + ' '.join(f'{obj}({sec})' for obj, sec, _, _ in v) + ' }\n  ' for lo, v in sorted(placed.items())))
    hdr = subprocess.run([str(GCC_BIN / 'nds32le-elf-objdump'), '-h', str(elf)], capture_output=True, text=True).stdout
    hole_blobs = []
    for lo, v in sorted(placed.items()):
        mm = re.search(rf'\s\.hole_{lo:x}\s+([0-9a-f]+)\s+([0-9a-f]+)', hdr); size, vma = int(mm.group(1), 16), int(mm.group(2), 16)
        hi = next(h for l, h, _ in holes if l == lo)
        if vma != lo or lo + size > hi or size != v[-1][2] + v[-1][3] - lo: raise ValueError(f'hole {lo:#x}: linked {vma:#x}+{size:#x} does not match the placement (hole end {hi:#x})')
        out = work / f'hole_{lo:x}.bin'; subprocess.run([str(GCC_BIN / 'nds32le-elf-objcopy'), '-O', 'binary', '-j', f'.hole_{lo:x}', str(elf), str(out)], check=True)
        hole_blobs.append(dict(address=lo, end=hi, entry=next(e for l, _, e in holes if l == lo), bytes=out.read_bytes(), sections=[dict(object=Path(o).name, section=s, address=hex(a), size=z) for o, s, a, z in v]))
    for sec in ('.data', '.bss'):
        mm = re.search(r'\s' + re.escape(sec) + r'\s+([0-9a-f]+)', hdr)
        if mm and int(mm.group(1), 16): raise ValueError(f'C feature {f} has {sec}; state must live in nds_ui_state')
    raw = work / (f + '.bin'); subprocess.run([str(GCC_BIN / 'nds32le-elf-objcopy'), '-O', 'binary', *(['--gap-fill', '0xff'] if b_report is not None else []), '-j', '.text*', '-j', '.rodata*', str(elf), str(raw)], check=True)
    if b_report is not None:
        # All tail outputs must be planned; reject live wildcard/orphan surprises.
        live = [(name,int(size,16),int(at,16)) for name,size,at in re.findall(r'^\s*\d+\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)',hdr,re.M)
                if name.startswith(('.text','.rodata')) and int(size,16)]
        expected = {r['output'] for r in b_report['allocations'] if r['pool']=='tail'}
        if {name for name,_,_ in live} != expected: raise ValueError('unplanned live B tail output')
        if live:
            start = min(at for _,_,at in live)
            raw.write_bytes(b'\xff'*(start-base)+raw.read_bytes())
        # Bind final section addresses/sizes, including linker relaxation/strings.
        for row in b_report['allocations']:
            if row['pool']!='tail': continue
            name,size,at = next(x for x in live if x[0]==row['output'])
            if at!=row['address'] or size>row['capacity']: raise ValueError('B output does not match reservation')
            row['linked_size']=size
        (work/'b_placement.proposed.json').write_text(json.dumps(b_report,indent=2)+'\n')
    nm = subprocess.run([str(GCC_BIN / 'nds32le-elf-nm'), str(elf)], capture_output=True, text=True).stdout
    in_hole = lambda a: any(h['address'] <= a < h['address'] + len(h['bytes']) for h in hole_blobs)
    syms = {n: int(a, 16) for a, t, n in (l.split() for l in nm.splitlines() if len(l.split()) == 3) if t in 'TtRr' and (base <= int(a, 16) or in_hole(int(a, 16))) and n not in (asm_labels or {})}
    from .catalog_storage import code_sections
    code_secs = (re.findall(r'^\s*\d+\s+(\.text\S*)',hdr,re.M) if b_report is not None else ['.text']) + [f'.hole_{h["address"]:x}' for h in hole_blobs] + code_sections(cfg)
    code_secs = [s for s in code_secs if re.search(r'\s' + re.escape(s) + r'\s', hdr)]   # region-E code passes the same gates; a feature wholly in E has no .text
    from .disassembly import mapped_view
    dis_elf, dis_secs = mapped_view(elf, code_secs, GCC_BIN / 'nds32le-elf-objcopy')
    dis = ''; ends = {}
    for sec in code_secs:
        dis += subprocess.run([str(GCC_BIN / 'nds32le-elf-objdump'), '-d', '-j', dis_secs[sec], '--no-show-raw-insn', str(dis_elf)], capture_output=True, text=True).stdout
        mm = re.search(r'\s' + re.escape(sec) + r'\s+([0-9a-f]+)\s+([0-9a-f]+)', hdr); ends[sec] = int(mm.group(1), 16) + int(mm.group(2), 16)
    insns = []
    for line in dis.splitlines():
        mm = re.match(r'\s+([0-9a-f]+):\s+(\S.*)$', line)
        if mm: insns.append((int(mm.group(1), 16), mm.group(2).split('!')[0].strip()))
    hard = bool((cfg or {}).get('c_hard_float'))
    bad = [t for _, t in insns if (re.search(r'\.gp\b|\$gp', t) and not t.startswith(('push25', 'pop25'))) or fpu_instruction_bad(t, hard)]
    # Callee-saved fs6..fs11 (stock and GCC ABI; the stock entries save fd3..fd5 the same way, e.g. 0x4557e): a function
    # may use one only if it stores the containing fd3..fd5 to its frame and loads it back (MOD052, 2026-10-22).
    if hard:
        for fn, body in re.findall(r'<([^>]+)>:\n((?:\s+[0-9a-f]+:.*\n?)*)', dis):
            ops = [l.split(':', 1)[1].split('!')[0].strip() for l in body.splitlines() if ':' in l]
            used = ({int(n) // 2 for n in re.findall(r'\$fs([6-9]|1[01])\b', ' '.join(ops))}
                    | {int(n) for n in re.findall(r'\$fd([345])\b', ' '.join(ops))})
            saved = {int(n) for o in ops if o.startswith('fsdi') for n in re.findall(r'\$fd([345])\b', o)}
            restored = {int(n) for o in ops if o.startswith('fldi') for n in re.findall(r'\$fd([345])\b', o)}
            if not used <= saved or saved != restored: bad.append(f'{fn}: callee-saved fs6..fs11 without save/restore (fd {sorted(used)} saved {sorted(saved)} restored {sorted(restored)})')
    if bad: raise ValueError(f'C feature {f}: gp-relative, unvalidated FPU or callee-saved FPU register use {bad[:5]}')
    sec_end = lambda a: min(e for e in ends.values() if e > a)
    # Instruction length from its encoding (NDS32: first byte bit 7 set = 16-bit), so alignment padding before an aligned
    # function (objdump "...") is not counted into the preceding instruction (MOD089: ret5 + 2 zero bytes, 2026-10-29).
    first = {}
    for sec in code_secs:
        for mm in re.finditer(r'^\s+([0-9a-f]+):\s+([0-9a-f]{2}) ', subprocess.run([str(GCC_BIN / 'nds32le-elf-objdump'), '-d', '-j', dis_secs[sec], str(dis_elf)],
                              capture_output=True, text=True).stdout, flags=re.M):
            first[int(mm.group(1), 16)] = int(mm.group(2), 16)
    sizes = []
    for i, (a, t) in enumerate(insns):
        nxt = insns[i + 1][0] if i + 1 < len(insns) and insns[i + 1][0] < sec_end(a) and insns[i + 1][0] > a else sec_end(a)
        n = nxt - a
        if a in first and n > (2 if first[a] & 0x80 else 4): n = 2 if first[a] & 0x80 else 4
        sizes.append((a, n, t))
    su = {}
    for p in work.glob('*.su'):
        for l in p.read_text().splitlines():
            name, n, kind = l.split('\t'); su[name.split(':')[-1]] = int(n)
    for e in entries:
        if e not in syms: raise ValueError('C entry missing: ' + e)
    if auto_report is not None:
        (work / 'e_placement.json').write_text(json.dumps(auto_report, indent=2) + '\n')
    if holes is not None: return raw.read_bytes(), syms, sizes, su, hole_blobs
    return raw.read_bytes(), syms, sizes, su


def feature(name):
    return importlib.import_module('nds_ui.features.' + name)


class Ctx:
    def __init__(self, cfg, parent_b, enabled):
        self.cfg = cfg; self.parent_b = parent_b; self.enabled = enabled
        seg = cfg['segment']
        self.BASE = int(seg['base'], 16); self.STATE = int(seg['state'], 16); self.STATE_BYTES = seg['state_bytes']
        self.LEGACY = int(seg['legacy_cache'], 16); self.LEASE = self.STATE + seg['lease_offset']
        self.s = Source(); self.owner = {}; self.labels = {}; self.blobs = []; self.pc = None
        self._owner_stack = []

    # Frame helpers shared by all features (identical to the per-MOD generators).
    def begin(self, name, size=48):
        self.s.label(name); self.s.emit(f'addi sp,sp,-{size}')
        for i, r in enumerate(REGS): self.s.emit(f'swi {r},[sp + {i * 4}]')

    def end(self, size=48, tail=None):
        for i, r in enumerate(REGS): self.s.emit(f'lwi {r},[sp + {i * 4}]')
        self.s.emit(f'addi sp,sp,{size}'); self.s.emit(f'j {tail:#x}' if tail else 'ret5 lp')

    def addr(self, r, label):
        self.s.emit(f'sethi {r},@hi_{label}\nori {r},{r},@lo_{label}')

    def _run(self, owner, fn):
        start = len(self.s.rows); self._owner_stack.append(owner); fn(self); self._owner_stack.pop()
        for i in range(start, len(self.s.rows)): self.owner.setdefault(i, owner)

    def hook(self, name):
        """Inline extension point: every enabled feature providing HOOKS[name] emits here."""
        for f in self.enabled:
            fn = getattr(feature(f), 'HOOKS', {}).get(name)
            if fn: self._run(f, fn)

    # Data placement (after code).
    def align(self, n):
        self.pc = (self.pc + n - 1) & ~(n - 1)

    def data(self, label, raw):
        self.labels[label] = self.pc; self.blobs.append((self.pc, raw, self._owner_stack[-1])); self.pc += len(raw)


def resolve_features(names):
    for n in names:
        if n not in ALL_FEATURES: raise ValueError('unknown feature ' + n)
        for x in getattr(feature(n), 'CONFLICTS', ()):
            if x in names: raise ValueError(f'{n} conflicts with {x}')
        for r in feature(n).REQUIRES:
            if r not in names and r not in {tag_name(x) for x in names}: raise ValueError(f'{n} requires {r}')
    return [n for n in ALL_FEATURES if n in names]


def default_layout(enabled):
    code, data = [], []
    for f in enabled:
        m = feature(f); code += [f'{f}.{k}' for k in m.CODE]; data += [f'{f}.{k}' for k in m.DATA]
    return code, data


def generate(cfg, parent_b):
    # The admission cost table is part of the image: apply the config's version here, not only in the CLI
    # (MOD088's paired build skipped the CLI and silently baked the default v1 instead of its declared v4).
    from sdk.telemetry.nds import admission_costs as AC
    AC.use(cfg.get('admission_table', 'v1'), cfg.get('admission_estimate_overrides', ()))
    enabled = resolve_features(cfg['features'])
    code_order, data_order = default_layout(enabled)
    if 'layout' in cfg:
        code_order, data_order = cfg['layout']['code'], cfg['layout']['data']
        for item in code_order + data_order:
            if item.split('.')[0] not in enabled: raise ValueError('layout names disabled feature ' + item)
        want = set(default_layout(enabled)[0] + default_layout(enabled)[1])
        if set(code_order + data_order) != want: raise ValueError('layout must list every section of the enabled features exactly once: ' + str(sorted(want ^ set(code_order + data_order))))
    c = Ctx(cfg, parent_b, enabled)
    for item in code_order:
        f, sec = item.split('.'); c._run(f, feature(f).CODE[sec])
    pc = c.BASE
    for i, (name, line, size) in enumerate(c.s.rows):
        if name:
            if name in c.labels: raise ValueError('duplicate label ' + name)
            c.labels[name] = pc
        else: pc += size
    code_end = pc; c.pc = pc
    for item in data_order:
        f, sec = item.split('.'); c._owner_stack.append(f); feature(f).DATA[sec](c); c._owner_stack.pop()
    c.c_parts = []; c.hole_blobs = []; c.hole_rows = None; c.restores = []
    cf = [f for f in enabled if getattr(feature(f), 'C_SOURCES', None) and has_c(f, cfg)]
    if cf:
            f = cf[0]; c.align(4); base = c.pc
            c.hole_rows, hole_list = code_holes(cfg, parent_b, enabled) if cfg.get('code_holes') else (None, None)
            res = compile_c(cf, base, ROOT / 'work/nds_ui' / cfg['id'] / 'c' / 'linked', cfg,
                            asm_labels={k: v for k, v in c.labels.items() if not k.startswith(('hi_', 'lo_'))}, parent_b=parent_b, holes=hole_list)
            raw, syms, insns, su = res[:4]; c.hole_blobs = res[4] if len(res) > 4 else []
            # Parent hooks inside replaced bodies (features' SUPERSEDED) that no hole blob overwrites get their stock bytes
            # back: dead code either way, but no stale pointer into the old segment stays in the image.
            # Any overlap supersedes the entire instruction: a 2-byte-aligned blob may overwrite
            # half of a former 4-byte hook. Never restore that hook over live compiled code.
            sup = sorted({a for x in enabled for a in superseded_of(x, cfg)})
            stock_b = (ROOT / 'work/v110/decoded_b.bin').read_bytes()
            c.restores = [a for a in sup if not any(h['address'] < a + 4 and a < h['address'] + len(h['bytes']) for h in c.hole_blobs)
                          and parent_b[a - 0x10000:a - 0x10000 + 4] != stock_b[a - 0x10000:a - 0x10000 + 4]] if cfg.get('code_holes') else []
            for n, v in syms.items():
                if n in c.labels: raise ValueError('C symbol collides with asm label ' + n)
                c.labels[n] = v
            c._owner_stack.append(f); c.blobs.append((base, raw, f)); c._owner_stack.pop(); c.pc = base + len(raw)
            for x in cf:   # C entries standing in for asm entry names the harness/oracles use
                for alias, sym in getattr(feature(x), 'LABEL_ALIASES', {}).items(): c.labels[alias] = c.labels[sym]
            c.c_parts.append(dict(feature='+'.join(cf), base=base, end=c.pc, insns=insns, stack_usage=su, symbols={n: hex(v) for n, v in syms.items()},
                                  holes=[dict(address=hex(h['address']), end=hex(h['end']), entry=hex(h['entry']), used=len(h['bytes']), sections=h['sections']) for h in c.hole_blobs]))
    end = c.pc
    for n, v in list(c.labels.items()): c.labels['hi_' + n] = v >> 12; c.labels['lo_' + n] = v & 4095
    code, spec = assemble_rows(c.s.rows, c.BASE, c.labels)
    image = bytearray(b'\xff' * (end - c.BASE)); image[:len(code)] = code
    for at, raw, _ in c.blobs: image[at - c.BASE:at - c.BASE + len(raw)] = raw
    limit = int(cfg['segment']['limit'], 16)
    if end > limit: raise ValueError(f'segment end {end:#x} beyond limit {limit:#x}')
    patches = []
    for f in enabled:
        _, gone, names = SIP.reverted(feature(f), cfg)
        if gone: check_stock_bodies(f, gone, parent_b)
        placeholder = [n for n in names if n not in c.labels]   # patches() formats every entry; reverted ones are dropped below
        for n in placeholder: c.labels[n] = 0
        try: rows = feature(f).patches(c)
        finally:
            for n in placeholder: del c.labels[n]
        rows = [r for r in rows if r[0] not in gone] + (feature(f).stock_in_place_patches(c) if hasattr(feature(f), 'stock_in_place_patches') else [])
        for site, text, why in rows:
            new = encode(site, text); old = parent_b[site - 0x10000:site - 0x10000 + len(new)]
            patches.append(dict(address=f'{site:x}', old=old.hex(), new=new.hex(), assembly=text, feature=f, reason=why))
    check_revived_bodies(cfg, enabled, parent_b, patches + [dict(address=hex(a), new='00' * 4) for a in c.restores])
    from .catalog_storage import extract
    external = extract(cfg, ROOT / 'work/nds_ui' / cfg['id'] / 'c' / 'linked', GCC_BIN)
    return dict(ctx=c, enabled=enabled, code=bytes(image), code_end=code_end, end=end, spec=spec, patches=patches, holes=c.hole_blobs, restores=c.restores, external=external,
                layout=dict(code=code_order, data=data_order), modules=module_hashes(c, enabled, cfg, parent_b))


def check_revived_bodies(cfg, enabled, parent_b, patches):
    """stock_in_place: in every revived stock body, each parent byte that differs from stock is a theme colour swap or
    is rewritten by a patch of this build. No stale parent hook (pointing into the old segment) stays live."""
    entries = set()
    for f in enabled:
        m = feature(f)
        if hasattr(m, '_reverted_entries'): entries |= m._reverted_entries(cfg)
        else: entries |= SIP.reverted(m, cfg)[1]
    if not entries: return
    stock = (ROOT / 'work/v110/decoded_b.bin').read_bytes()
    covered = {int(p['address'], 16) + i for p in patches for i in range(len(p['new']) // 2)}
    palette = SIP.palette_sites([feature(f) for f in enabled], cfg) | SIP.parent_edits([feature(f) for f in enabled])
    for e in sorted(entries):
        body = SIP.body_of(e)
        theme = SIP.theme_sites(stock, parent_b, body[0], body[1]) | palette
        stale = [a for a in range(body[0], body[1] + 1) if parent_b[a - 0x10000] != stock[a - 0x10000] and a not in theme and a not in covered]
        if stale: raise ValueError(f'stock_in_place entry {e:#x}: parent bytes at {[hex(a) for a in stale[:4]]} stay live without a patch')


def check_stock_bodies(f, entries, parent_b):
    """stock_in_place: each reverted body in the parent equals stock (palette sites of the feature's SUPERSEDED aside)."""
    from .holes import stock_facts
    stock = (ROOT / 'work/v110/decoded_b.bin').read_bytes(); bodies = stock_facts()[2]
    sites = [a for a, v in getattr(feature(f), 'SUPERSEDED', {}).items() if 'palette' in v]
    for e in sorted(entries):
        body = next((r for r in bodies.get(e, []) if r[0] <= e <= r[1]), None)
        if not body: raise ValueError(f'{f}: stock_in_place entry {e:#x} has no function body in the index')
        theme = SIP.theme_sites(stock, parent_b, body[0], body[1]) | SIP.hook_windows()   # declared hooks: checked re-patched later
        bad = [a for a in range(body[0], body[1] + 1) if parent_b[a - 0x10000] != stock[a - 0x10000] and a not in theme and not any(s <= a < s + 4 for s in sites)]
        if bad: raise ValueError(f'{f}: stock_in_place entry {e:#x}: parent differs from stock at {[hex(x) for x in bad[:4]]}')


def has_c(f, cfg):
    """False when stock_in_place reverted every source of the feature (it then contributes no C)."""
    m = feature(f)
    return bool([s for s in SIP.sources_of(m, cfg) if s not in SIP.reverted(m, cfg)[0]])


def superseded_of(f, cfg):
    """A feature's superseded parent hooks for this config (stock_in_place keeps some bodies live)."""
    m = feature(f)
    if hasattr(m, 'superseded'): return m.superseded(cfg)
    stems = SIP.stems(m, cfg); gone = SIP.reverted(m, cfg)[1]
    keep = m.restore_inside(cfg) if hasattr(m, 'restore_inside') else set()
    out = {a: v for a, v in getattr(m, 'SUPERSEDED', {}).items() if not any(s + '.c' in v for s in stems) and (not SIP.inside(a, gone) or a in keep)}
    out.update({e: 'stock_in_place: a parent redirect at this reverted entry is restored to stock' for e in gone})
    return out


def redirected_entries(cfg, enabled):
    """Stock entries this config redirects to C with a 4-byte `j` (catalog/chains, UI input, host layer)."""
    out = set()
    for f in enabled:
        m = feature(f)
        out |= set(m.hooked(cfg) if hasattr(m, 'hooked') else set(getattr(m, 'HOOKED', ())) - SIP.reverted(m, cfg)[1])
    return out


def code_holes(cfg, parent_b, enabled):
    """Code room step 2 (cfg code_holes = {"min": bytes}): rows of nds_ui.holes.analyse for the redirected entries and the
    usable holes. Hook sites come from the features' patch lists under placeholder labels (sites do not depend on labels)."""
    from . import holes as HL
    from .stock_api import API
    n = Ctx(cfg, parent_b, enabled); n.labels = _Placeholder()
    sites = [(site, len(encode(site, text))) for f in enabled for site, text, _ in feature(f).patches(n)]
    sites += [(API.hook_bss_end, 4), (API.hook_heap_start, 4), (API.version_string, 8)]
    rows = HL.analyse(redirected_entries(cfg, enabled), parent_b, n.BASE, sites, cfg['code_holes'].get('min', HL.MIN))
    # A redirected function may retain a terminal assembly continuation. Never
    # reclaim its body merely because parent-side references cannot see new C.
    kept = [(lo, hi, why) for f in enabled
            for lo, hi, why in getattr(feature(f), 'KEPT_CODE_RANGES', ())]
    for row in rows:
        if not row.get('usable'): continue
        lo, hi = map(lambda x: int(x, 16), row['hole'])
        overlap = [why for a, b, why in kept if lo < b and a < hi]
        if overlap:
            row['usable'] = 0
            row['reason'] = 'retained continuation: ' + '; '.join(overlap)
    return rows, HL.holes(rows)


class _Placeholder(dict):
    """Labels for normalized module assembly: own labels at canonical addresses, every
    external label at a stable name-derived address near the module."""
    def __missing__(self, key):
        if key.startswith(('hi_', 'lo_')):
            v = self[key[3:]]; return v >> 12 if key.startswith('hi_') else v & 4095
        return 0x102000 + (zlib.crc32(key.encode()) & 0x3ff) * 2


def module_hashes(c, enabled, cfg, parent_b):
    """Position-independent bytes per module: its rows assembled contiguously at 0x100000 with
    placeholder external labels, its data blobs regenerated under placeholder labels, and its
    patch texts encoded at their sites under placeholder labels."""
    # Canonical modules have different GC roots from the complete image. Their
    # live sections must not inherit the final image's reservations or addresses.
    # Normalize auto-placed modules in B; retain the separate catalog convention.
    if cfg.get('region_e_code') == {'placement': 'auto'}:
        cfg = dict(cfg, _region_e_resolved=[])
    out = {}
    canonical_inputs = sorted({p for base in ('sdk', 'firmware/reconstructed')
                               for p in (ROOT / base).rglob('*') if p.is_file() and p.suffix in ('.h', '.c', '.ld', '.json', '.py')})
    canonical_key = BC.key(BC.implementation(ROOT, GCC_BIN), cfg, BC.digest(parent_b),
                           [(str(p.relative_to(ROOT)), BC.digest(p.read_bytes())) for p in canonical_inputs])
    for f in enabled:
        rows = [r for i, r in enumerate(c.s.rows) if c.owner.get(i) == f]
        lab = _Placeholder(); pc = 0x100000
        for name, line, size in rows:
            if name: lab[name] = pc
            else: pc += size
        code, _ = assemble_rows(rows, 0x100000, lab)
        n = Ctx(cfg, parent_b, enabled); n.labels = lab; n.pc = 0x110000
        m = feature(f)
        for sec in m.DATA:
            n._owner_stack.append(f); m.DATA[sec](n); n._owner_stack.pop()
        data = b''.join(raw for _, raw, _ in n.blobs)
        if getattr(m, 'C_SOURCES', None) and has_c(f, cfg):
            canonical_work = ROOT / 'work/nds_ui' / cfg['id'] / 'c' / (f + '_canonical')
            receipt = canonical_work / 'canonical_cache.json'
            feature_key = BC.key(canonical_key, f, m.c_headers(cfg, parent_b) if hasattr(m, 'c_headers') else {})
            suffix = BC.load(receipt, feature_key)
            if suffix is None:
                craw, _, _, _ = compile_c(f, 0x110000, canonical_work, cfg, canonical=True, parent_b=parent_b)
                suffix = b'|C|' + craw + compiler_identity(cfg).encode()
                from .catalog_storage import extract
                for payload in extract(cfg, canonical_work, GCC_BIN, require_catalog=f == 'catalog_c'):
                    suffix += (b'|external-catalog|' if payload['section'] == '.catalog_ext' else b'|external-e-code|') + payload['bytes']
                BC.save(receipt, feature_key, suffix.hex())
            else:
                suffix = bytes.fromhex(suffix)
            data += suffix
        pt = b''.join(site.to_bytes(4, 'little') + encode(site, text) for site, text, _ in m.patches(n))
        h = hashlib.sha256(code + b'|' + data + b'|' + pt).hexdigest()
        out[f] = dict(normalized_sha256=h, code_bytes=len(code), data_bytes=len(data), rows=len([r for r in rows if r[1]]))
    return out


def write_outputs(out_dir, cfg, g, parent_name):
    c = g['ctx']; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'code.bin').write_bytes(g['code'])
    (out_dir / 'labels.json').write_text(json.dumps(c.labels, indent=2) + '\n')
    (out_dir / 'spec.tsv').write_text('\n'.join(f'{a:x}\t{z}\t{t}' for a, z, t in g['spec']) + '\n')
    (out_dir / 'source.nds').write_text('\n'.join(n + ':' if n else '  ' + t for n, t, _ in c.s.rows) + '\n')
    (out_dir / 'data.json').write_text(json.dumps([dict(address=hex(a), hex=raw.hex()) for a, raw, _ in c.blobs], indent=2) + '\n')
    (out_dir / 'patch_spec.tsv').write_text('\n'.join(f'{p["address"]}\t{len(p["new"]) // 2}\t{p["assembly"]}' for p in g['patches']) + '\n')
    (out_dir / 'patches.json').write_text(json.dumps(g['patches'], indent=2) + '\n')
    (out_dir / 'external_data.json').write_text(json.dumps([
        dict(region=b['region'], address=hex(b['address']), offset=hex(b['offset']),
             hex=b['bytes'].hex(), sha256=b['sha256'], reason=b['reason'])
        for b in g.get('external', [])], indent=2) + '\n')
    lay = dict(base=c.BASE, code_end=g['code_end'], end=g['end'], state=c.STATE, state_bytes=c.STATE_BYTES, lease_cache=c.LEASE,
               legacy_cache=c.LEGACY, features=g['enabled'], layout=g['layout'], parent_b=parent_name,
               code_sha256=hashlib.sha256(g['code']).hexdigest(), instructions=len(g['spec']))
    for f in ('admission', 'admission_c', 'refuse_c'):
        if f in g['enabled']: lay['admission'] = feature(f).layout_info()
    if 'admission' in lay:
        from sdk.telemetry.nds import admission_costs as AC
        lay['admission']['table'] = AC.active()
    if c.c_parts:
        lay['c'] = [dict(feature=p['feature'], base=hex(p['base']), end=hex(p['end']), bytes=p['end'] - p['base'], instructions=len(p['insns']),
                         stack_usage=p['stack_usage'], symbols=p['symbols'], compiler_sha256=compiler_identity(cfg), hard_float=bool(cfg.get('c_hard_float'))) for p in c.c_parts]
        (out_dir / 'c_spec.tsv').write_text(''.join(f'{a:x}\t{z}\t{t}\n' for p in c.c_parts for a, z, t in p['insns']))
        for p in lay['c']: p['holes'] = next(q for q in c.c_parts if q['feature'] == p['feature'])['holes']
    elif (out_dir / 'c_spec.tsv').exists(): (out_dir / 'c_spec.tsv').unlink()
    if getattr(c, 'hole_rows', None) is not None:
        lay['holes'] = dict(min=cfg['code_holes'].get('min', 64), file='holes.json', used=sum(len(h['bytes']) for h in c.hole_blobs),
                            available=sum(r['usable'] for r in c.hole_rows), count=len(c.hole_blobs))
        (out_dir / 'holes.json').write_text(json.dumps(dict(rows=c.hole_rows, blobs=[dict(address=hex(h['address']), end=hex(h['end']), entry=hex(h['entry']),
                                                       sections=h['sections'], hex=h['bytes'].hex()) for h in c.hole_blobs], restored=[hex(a) for a in c.restores]), indent=1) + '\n')
    elif (out_dir / 'holes.json').exists(): (out_dir / 'holes.json').unlink()
    (out_dir / 'layout.json').write_text(json.dumps(lay, indent=2) + '\n')
    (out_dir / 'modules.json').write_text(json.dumps(g['modules'], indent=2) + '\n')
    return lay
