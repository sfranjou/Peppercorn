#!/usr/bin/env python3
"""Build one SDK effect into an exact g overlay record and an e catalog descriptor.

Offline only. Compiles with the system clang (Thumb target) and links with the installed Arm
GNU binutils for the group's execution slot (the Arm GNU gcc itself cannot start on this Mac:
its x86_64 cc1 needs an x86_64 libzstd that is not installed), then checks the result against what stock overlays do before accepting it:
payload + .bss fit the slot, both callbacks are inside the payload, no undefined
symbols or relocations out of the slot, every instruction mnemonic occurs in a stock
overlay, and no fused multiply-add. Writes record/descriptor blobs and a manifest.

An effect in a group that owns a coprocessor program slot (DST, group 2) must also provide the
program: effect.json "copro": {"module": "program.py"}, a Python module with SOURCE (a list for
sdk/copro/asm.py), CELLS (name -> data word index) and optionally ALLOWED_NON_X. The program
is assembled at the slot's PC base, checked by sdk/copro/frame.py (stock entry/exit frame,
size, executed forms only) and becomes the record's secondary payload. CELLS are handed to the
C source as COPRO_CELL_<NAME> in a generated copro_cells.h; literal addresses in the ARM code
may then also lie in the group's data cells. See analysis/firmware/COPRO_EFFECTS.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from protocol.overlay_image import Overlay,build_overlay,parse_overlay,Descriptor,DescriptorParameter,build_descriptor,parse_descriptor,pad_descriptor,parse_container

ROOT=Path(__file__).resolve().parent.parent
SDK=ROOT/'sdk'
BIN=Path('/Applications/ArmGNUToolchain/14.2.rel1/arm-none-eabi/bin')
LD,OBJCOPY,OBJDUMP,NM=(BIN/('arm-none-eabi-'+x) for x in ('ld','objcopy','objdump','nm'))
CLANG='/usr/bin/clang'
# analysis/firmware/DSP_LOADER.md: (slot base, slot bytes) for the ARM-side groups.
SLOTS={0:(0x10000000,0xc00),1:(0x10000c00,0x2c00),6:(0x1000a000,0x2000),7:(0x1000c000,0xc400),
       8:(0x10018400,0x7000)}   # RVB: SDK effects have count_word byte 1 = 0xff, so the loader does not
                                  # load the shared stock engine (group 10) over the slot (c 0x667c..0x668c)
# Groups with a coprocessor program slot: rules in sdk/copro/frame.py (first: DST).
from sdk.copro import asm as copro_asm,frame as copro_frame  # noqa: E402
SLOTS.update({g:(v['primary_base'],v['primary_bytes']) for g,v in copro_frame.SLOTS.items()})
SLOTS.update({g:(v['primary_base'],v['primary_bytes']) for g,v in copro_frame.STOCK_SLOTS.items()})

# Optional managed-tail requirements (effect.json "tail": {"bytes", "alignment", "required"}).
# Carried after the stub in the record prefix, which loader 5328 never copies (record word0 = 64);
# see sdk/resources/gp50_resident.h and analysis/firmware/RESIDENT_RESOURCES.md. Effects without
# "tail" build byte-identically. Needs a resident lease adapter that no installed image has yet.
REQ_MAGIC,REQ_ABI,REQ_FLAG_REQUIRED=0x51523547,1,1
POOL_BASE,POOL_END=0x290d7580,0x290fffb0
TAIL_REGION=(0x290d7580,0x29100000)   # [start, end]: end may appear as a bound literal
RESIDENT_BASE=0x20003ae8
RESIDENT_VIEW=lambda group:RESIDENT_BASE+108+16*group
CFLAGS=['--target=thumbv7em-none-eabihf','-mcpu=cortex-m4','-mfpu=fpv4-sp-d16','-mfloat-abi=hard','-Os','-ffreestanding','-fno-builtin',
        '-ffp-contract=off','-fno-math-errno','-fno-jump-tables','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-ffunction-sections','-fdata-sections',
        '-Wall','-Wextra','-Werror','-Wdouble-promotion','-Wfloat-conversion']
FORBIDDEN=re.compile(r'^(vfm|vfnm|vml|vnml|bl$|blx$|svc|bkpt|cps|msr|mrs|wfi|wfe|udf)')
# Diagnostic effects may opt in (effect.json "allow_system_instructions": true, default off) to a
# relaxed rule that permits the three system instructions needed by the fault-safe read primitive
# (cpsid/cpsie for FAULTMASK, and msr/mrs). Everything else in FORBIDDEN stays banned. Effects
# without the key use FORBIDDEN unchanged and build byte-identically. See analysis/firmware/PROBE_V4.md.
FORBIDDEN_SYS_OK=re.compile(r'^(vfm|vfnm|vml|vnml|bl$|blx$|svc|bkpt|wfi|wfe|udf)')
# Opt-in "allow_internal_calls": {"max_init_stack": N, "max_process_stack": N} (NS Capture v6, slot room): `bl` only to
# functions inside the payload, no recursion, no indirect calls (blx stays banned); worst-case stack per callback from
# the call graph and clang -fstack-usage must stay within the declared bounds (process runs in the audio PendSV handler).
FORBIDDEN_CALLS_OK=re.compile(r'^(vfm|vfnm|vml|vnml|blx$|svc|bkpt|cps|msr|mrs|wfi|wfe|udf)')


def run(cmd,**kw):
    q=subprocess.run([str(c) for c in cmd],capture_output=True,text=True,**kw)
    if q.returncode:raise SystemExit(f'{cmd[0]} failed:\n{q.stdout}{q.stderr}')
    return q.stdout


def mnemonics(blob,base):
    """Mnemonics objdump reports for a raw Thumb payload (data words decode too; callers filter)."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.bin') as f:
        f.write(blob);f.flush()
        text=run([OBJDUMP,'-D','-b','binary','-marm','-Mforce-thumb',f'--adjust-vma={base:#x}',f.name])
    return [m.group(1) for m in re.finditer(r'^\s*[0-9a-f]+:\t[0-9a-f ]+\t(\S+)',text,re.M)]


CONDITIONS=('eq','ne','cs','cc','hs','lo','mi','pl','vs','vc','hi','ls','ge','lt','gt','le')


def base_mnemonic(m,known=None):
    """Mnemonic without width/type suffix and, when that yields a known base, without the
    IT-block condition (vmovmi.f32 -> vmov)."""
    b=m.split('.')[0]
    if known is not None and b not in known and b[-2:] in CONDITIONS and b[:-2] in known:return b[:-2]
    return b


def stock_overlay_prefix(stock_g):
    with (stock_g or ROOT/'work/v110/decoded_g.bin').open('rb') as stream:
        stream.seek(5584)
        return stream.read(16)


def stock_mnemonics(stock_g=None):
    g=parse_container((stock_g or ROOT/'work/v110/decoded_g.bin').read_bytes());seen=set()
    for group in (0,1,6,7):
        for blob in g.groups[group]:
            seen.update(m.split('.')[0] for m in mnemonics(parse_overlay(blob).primary,SLOTS[group][0]))
    return seen


def f32bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]


def build_copro(effect_dir,meta,out,stock_g=None):
    """Assemble and check the effect's coprocessor program; write secondary.bin, its listing and
    copro_cells.h. Returns (secondary bytes, manifest part, module path, cell address range)."""
    import importlib.util
    group=meta['group']
    if 'stock_program' in meta['copro']:return build_stock_copro(effect_dir,meta,out,stock_g)
    slot=copro_frame.SLOTS.get(group) or (copro_frame.EQ_OWN if group==5 else None);path=effect_dir/meta['copro']['module']
    spec=importlib.util.spec_from_file_location(f'gp50_copro_program_{effect_dir.name}',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cells=dict(module.CELLS);lo,hi=slot['cells']
    if cells.get('ENABLE')!=slot['flag_cell']:raise SystemExit(f"CELLS['ENABLE'] must be the group's flag cell {slot['flag_cell']:#x}")
    bad=[k for k,v in cells.items() if not (isinstance(v,int) and lo<=v<hi) or not re.fullmatch(r'[A-Z][A-Z0-9_]*',k)]
    # MODE_EXCLUSIVE_CELLS (NS Capture v6): two cell maps share addresses on purpose (one per record format).
    if bad or (len(set(cells.values()))!=len(cells) and not getattr(module,'MODE_EXCLUSIVE_CELLS',False)):raise SystemExit(f'cells outside D[{lo:#x}..{hi-1:#x}], duplicated or badly named: {bad}')
    try:
        words=copro_asm.assemble(list(module.SOURCE),slot['pc'])
    except copro_asm.AsmError as e:
        if not getattr(module,'ALLOWED_NON_X',None):raise SystemExit(f'coprocessor program: {e}')
        raise SystemExit(f'coprocessor program: {e} (the assembler accepts executed forms only; ALLOWED_NON_X needs raw-word support that does not exist yet)')
    try:report=copro_frame.check_eq(words,getattr(module,'ALLOWED_NON_X',())) if group==5 else copro_frame.check(group,words,getattr(module,'ALLOWED_NON_X',()),getattr(module,'ALLOW_CALLS',False),getattr(module,'EXTERNAL_TARGETS',()))
    except copro_frame.FrameError as e:raise SystemExit(f'coprocessor program: {e}')
    stage_header=''
    # Mutually exclusive kernel, transported after the initial executable and
    # copied to the slot origin by init before any DSP execution.
    staged=getattr(module,'STAGED_SOURCE',None)
    if staged is not None:
        staged_words=copro_asm.assemble(list(staged),slot['pc'])
        try:staged_report=copro_frame.check(group,staged_words,(),getattr(module,'ALLOW_CALLS',False))
        except copro_frame.FrameError as e:raise SystemExit(f'staged coprocessor program: {e}')
        stage_pc=slot['pc']+len(words)
        if stage_pc+len(staged_words)>slot['next_pc']:raise SystemExit('staged transport exceeds program slot')
        stage_header=f'#define COPRO_STAGE_PC {stage_pc:#x}u\n#define COPRO_STAGE_WORDS {len(staged_words)}u\n'
        report['staged']={'pc':hex(stage_pc),'words':len(staged_words),'frame':staged_report}
        words+=staged_words
    secondary=struct.pack(f'<{len(words)}I',*words)
    (out/'secondary.bin').write_bytes(secondary);(out/'secondary.lst').write_text(copro_asm.listing(words,slot['pc'])+'\n')
    header='/* Generated by sdk/build_effect.py from '+str(path.relative_to(ROOT))+'. Do not edit. */\n#ifndef COPRO_CELLS_H\n#define COPRO_CELLS_H\n'
    header+=''.join(f'#define COPRO_CELL_{k} {v:#x}u\n' for k,v in cells.items())+stage_header+'#endif\n'
    (out/'copro_cells.h').write_text(header)
    report.update(module=str(path.relative_to(ROOT)),cells={k:f'{v:#x}' for k,v in cells.items()},destination=hex(0x28004000+4*slot['pc']),
        cell_address_range=[hex(0x28000000+4*lo),hex(0x28000000+4*hi)])
    # The ARM side may also write program-memory data in this slot's own program window above the code
    # (PROGRAM_DATA_PC in program.py, e.g. FFT twiddles / filter spectra): 0x28004000 + 4 * pc.
    pd=getattr(module,'PROGRAM_DATA_PC',None)
    if pd is not None:
        # MODE_CODE_PC (NS Capture v6): code from there up is mode-exclusive; the ARM may overwrite it in other modes,
        # because the stock loader copies the whole program again before every init. Code below it stays protected.
        protected=getattr(module,'MODE_CODE_PC',slot['pc']+len(words))
        if not (slot['pc']<=protected<=slot['pc']+len(words) and protected<=pd<slot['pc']+slot['capacity_bytes']//4):raise SystemExit(f'PROGRAM_DATA_PC {pd:#x} must lie above the code inside the slot')
        if protected!=slot['pc']+len(words):report['mode_exclusive_code']=[hex(protected),hex(slot['pc']+len(words))]
        report['program_data']=[hex(0x28004000+4*pd),hex(0x28004000+4*(slot['pc']+slot['capacity_bytes']//4))]
        return secondary,report,path,((0x28000000+4*lo,0x28000000+4*hi),(0x28004000+4*pd,0x28004000+4*(slot['pc']+slot['capacity_bytes']//4)))
    return secondary,report,path,(0x28000000+4*lo,0x28000000+4*hi)


def build_stock_copro(effect_dir,meta,out,stock_g=None):
    """Reuse a stock coprocessor program byte-for-byte (EQ): copied from the stock image's record,
    pinned by SHA-256; the effect's ARM code only writes the slot's cells."""
    group=meta['group'];slot=copro_frame.STOCK_SLOTS.get(group)
    if not slot or meta['copro'] != {'stock_program':slot['program']}:raise SystemExit(f'stock_program: group {group} offers only {slot and slot["program"]!r}')
    container=parse_container((stock_g or ROOT/'work/v110/decoded_g.bin').read_bytes())
    secondary=parse_overlay(container.groups[slot['stock_group']][slot['stock_record']]).secondary
    if hashlib.sha256(secondary).hexdigest()!=slot['program_sha256']:raise SystemExit('stock coprocessor program identity changed')
    (out/'secondary.bin').write_bytes(secondary)
    lo,hi=slot['cells']
    header='/* Generated by sdk/build_effect.py: cells of the stock '+slot['name']+' program (sdk/copro/frame.py STOCK_SLOTS). */\n#ifndef COPRO_CELLS_H\n#define COPRO_CELLS_H\n'
    header+=''.join(f'#define COPRO_CELL_{k} {v:#x}u\n' for k,v in slot['named_cells'].items())+'#endif\n'
    (out/'copro_cells.h').write_text(header)
    report=dict(slot=slot['name'],stock_program=slot['program'],program_sha256=slot['program_sha256'],words=len(secondary)//4,pc_base=slot['pc'],
        cells={k:f'{v:#x}' for k,v in slot['named_cells'].items()},destination=hex(0x28004000+4*slot['pc']),cell_address_range=[hex(0x28000000+4*lo),hex(0x28000000+4*hi)])
    return secondary,report,ROOT/'sdk/copro/frame.py',(0x28000000+4*lo,0x28000000+4*hi)


def internal_call_stack(listing,obj,symbols,base,end,meta):
    """allow_internal_calls: every `bl` targets a function inside the payload; no recursion; worst-case stack of the
    init/process callbacks (sum of -fstack-usage frames along the deepest call chain) within the declared bounds."""
    su={}
    for line in obj.with_suffix('.su').read_text().splitlines():
        loc,size,kind=line.split('\t');su[loc.split(':')[-1]]=int(size)
        if kind.strip()!='static':raise SystemExit(f'stack usage of {loc} is {kind.strip()}, not static')
    funcs={a&~1:n for n,(a,k) in symbols.items() if k in 'Tt' and base<=a&~1<end}
    calls={};cur=None
    for line in listing.splitlines():
        m=re.match(r'^([0-9a-f]+) <(\S+)>:',line)
        if m:cur=m.group(2);calls.setdefault(cur,set());continue
        m=re.match(r'^\s*[0-9a-f]+:\t[0-9a-f ]+\tbl\t(0x)?([0-9a-f]+)',line)
        if m:
            t=int(m.group(2),16)
            if t not in funcs:raise SystemExit(f'bl to {t:#x}: not a function inside the payload')
            calls[cur].add(funcs[t])
    def depth(f,seen=()):
        if f in seen:raise SystemExit(f'recursion through {f}')
        if f not in su:raise SystemExit(f'no stack usage for {f}')
        return su[f]+max((depth(g,seen+(f,)) for g in calls.get(f,())),default=0)
    lim=meta['allow_internal_calls'];out={}
    for key,name in (('init',meta['init']),('process',meta['process'])):
        out[key]=depth(name)
        if out[key]>int(lim[f'max_{key}_stack']):raise SystemExit(f'{key} worst-case stack {out[key]} B > max_{key}_stack {lim[f"max_{key}_stack"]}')
    return dict(worst_case_bytes=out,bounds={k:int(v) for k,v in lim.items()},call_graph={f:sorted(g) for f,g in calls.items() if g})


def author_input_name(path,effect_dir):
    """Preserve in-tree receipt names; allow author directories outside the SDK."""
    path=path.resolve()
    if path.is_relative_to(ROOT):return path.relative_to(ROOT).as_posix()
    return 'author_effect/'+path.relative_to(effect_dir.resolve()).as_posix()


def build(effect_dir,out,stock_g=None):
    meta=json.loads((effect_dir/'effect.json').read_text());group=meta['group']
    if group not in SLOTS:raise SystemExit('only ARM-side groups 0, 1, 6, 7, 8 (RVB), the DST group 2 and the EQ group 5 (stock program) are supported')
    if (group in copro_frame.SLOTS or group in copro_frame.STOCK_SLOTS)!=bool(meta.get('copro')):
        raise SystemExit('a coprocessor program ("copro") is required for, and only allowed in, a group that owns a program slot (2)')
    base,size=SLOTS[group];out.mkdir(parents=True,exist_ok=True)
    elf=out/'effect.elf';payload_path=out/'payload.bin'
    obj=out/'effect.o'
    secondary,copro,copro_path,cell_range=build_copro(effect_dir,meta,out,stock_g) if meta.get('copro') else (b'',None,None,(0,0))
    tail=meta.get('tail');prefix=stock_overlay_prefix(stock_g);tail_flags=[]
    if tail is not None:
        if set(tail)-{'bytes','alignment','required'}:raise SystemExit('tail: only bytes, alignment, required')
        tb,ta=int(tail['bytes']),int(tail.get('alignment',2))
        if tb<=0 or tb%2 or tb>POOL_END-POOL_BASE or ta<2 or ta>4096 or ta&(ta-1):raise SystemExit('tail: bytes even 2..pool, alignment power of two 2..4096')
        prefix=prefix+struct.pack('<6I',REQ_MAGIC,REQ_ABI,24,REQ_FLAG_REQUIRED if tail.get('required') else 0,tb,ta)
        tail_flags=['-I',SDK/'resources',f'-DGP50_EFFECT_GROUP={group}u']
    if meta.get('publish_meter') and not tail_flags:tail_flags=['-I',SDK/'resources',f'-DGP50_EFFECT_GROUP={group}u']
    # Optional stock-looper RAM borrowing (sdk/resources/gp50_looper.h), DLY only; see LOOPER_MEMORY.md 5.
    looper=bool(meta.get('looper_ring'))
    if looper and group!=7:raise SystemExit('looper_ring: only the DLY group (7) may borrow the looper RAM')
    if looper and not tail_flags:tail_flags=['-I',SDK/'resources',f'-DGP50_EFFECT_GROUP={group}u']
    # Opt-in "tail_region": the RVB effect owns the RAM above the looper (TAIL_REGION, 166 KB, outside the looper's
    # range: analysis/firmware/LOOPER_MEMORY.md). One owner per image: not with managed-tail leases ("tail").
    tail_region=bool(meta.get('tail_region'))
    if tail_region and (group!=8 or tail is not None or looper):raise SystemExit('tail_region: RVB group (8) only, not with "tail" or "looper_ring"')
    # Opt-in workaround when the IT/NOP gate below trips: IT blocks limited to one 16-bit instruction.
    it_flags=['-mllvm','-arm-restrict-it'] if meta.get('restrict_it') else []
    calls=meta.get('allow_internal_calls')
    run([CLANG,*CFLAGS,*it_flags,*(['-fstack-usage'] if calls else []),'-I',SDK/'include',*tail_flags,*(['-I',out] if copro else []),'-c',effect_dir/meta['source'],'-o',obj])
    run([LD,f'--defsym=SLOT_BASE={base:#x}',f'--defsym=SLOT_SIZE={size:#x}','-T',SDK/'overlay.ld','--gc-sections','--no-undefined',
         '-Map',out/'effect.map',obj,'-o',elf])
    run([OBJCOPY,'-O','binary','-j','.payload',elf,payload_path])
    payload=payload_path.read_bytes()
    symbols={}
    for line in run([NM,elf]).splitlines():
        address,kind,name=line.split();symbols[name]=(int(address,16),kind)
    undefined=[n for n,(a,k) in symbols.items() if k in 'Uw']
    if undefined:raise SystemExit(f'undefined symbols: {undefined}')
    start,end=symbols['__payload_start'][0],symbols['__payload_end'][0];bss_end=symbols['__bss_end'][0]
    if start!=base or end-start!=len(payload) or len(payload)%4:raise SystemExit('payload layout unexpected')
    if bss_end>base+size:raise SystemExit('payload + state exceed the slot')
    callbacks=[]
    for name in (meta['init'],meta['process']):
        address,kind=symbols[name]
        if kind not in 'Tt' or not base<=address&~1<end:raise SystemExit(f'{name} is not a function inside the payload')
        callbacks.append(address|1)  # nm prints Thumb function values without the Thumb bit
    init,process=callbacks
    listing=run([OBJDUMP,'-d','-j','.payload',elf]);(out/'effect.lst').write_text(listing)
    used=[m.group(1) for m in re.finditer(r'^\s*[0-9a-f]+:\t[0-9a-f ]+\t(\S+)',listing,re.M)]
    code=[m for m in used if not m.startswith('.')]
    stock=stock_mnemonics(stock_g)
    forbidden=FORBIDDEN_SYS_OK if meta.get('allow_system_instructions') else FORBIDDEN_CALLS_OK if calls else FORBIDDEN
    stack=internal_call_stack(listing,obj,symbols,base,end,meta) if calls else None
    bad=sorted({m for m in code if forbidden.match(base_mnemonic(m,stock))})
    unknown=sorted({m for m in code if base_mnemonic(m,stock) not in stock})
    if bad:raise SystemExit(f'forbidden instructions: {bad}')
    # Apple clang 17 can emit `it <c>; nop @ alignment hazard; v<op><c>`: the NOP consumes the IT
    # slot and the (condition-less Thumb VFP) instruction then runs unconditionally on hardware.
    # The interpreter executes this like hardware (found via the Thumb/native differential only once
    # the condition was exercised), so reject any NOP inside an IT block statically.
    rows=[(m.group(1),m.group(2)) for m in re.finditer(r'^\s*([0-9a-f]+):\t[0-9a-f ]+\t(\S+)',listing,re.M)]
    for k,(address,mnemonic) in enumerate(rows):
        it=re.fullmatch(r'it([te]{0,3})',mnemonic)
        if it and any(rows[k+j][1].startswith('nop') for j in range(1,len(it.group(1))+2) if k+j<len(rows)):
            raise SystemExit(f'NOP inside IT block at {address} (compiler alignment-hazard padding breaks the conditional)')
    # Floating-point instructions must be ones stock overlays use (FPU features are not otherwise
    # known); integer Thumb-2 instructions outside the stock set are allowed and reported.
    unknown_fp=[m for m in unknown if m.startswith('v')]
    if unknown_fp:raise SystemExit(f'floating-point instructions never used by a stock ARM-side overlay: {unknown_fp}')
    external={int(x,16) for x in meta.get('diagnostic_external_addresses',[])}  # diagnostic effects only
    view=range(RESIDENT_VIEW(group),RESIDENT_VIEW(group)+16) if tail is not None else range(0)
    meter={RESIDENT_BASE,RESIDENT_BASE+4,RESIDENT_BASE+288} if meta.get('publish_meter') else set()   # MOD034 meter mailbox
    ranges=cell_range if isinstance(cell_range[0],tuple) else (cell_range,)
    def inside(v):return (not 0x10000000<=v<0x30000000 or base<=v<base+size or v in external or any(r0<=v<r1 for r0,r1 in ranges)
                          or v in view or v in meter or (tail is not None and v in (POOL_BASE,POOL_END,RESIDENT_BASE,RESIDENT_BASE+4))
                          or (looper and v in (0x20003a4c,0x20003a4d,0x20003a74,0x20003a78,0x29000000))
                          or (tail_region and TAIL_REGION[0]<=v<=TAIL_REGION[1]))
    for _,low,high in re.findall(r'movw\t(\w+), #(\d+).*\n(?:.*\n){0,3}?.*movt\t\1, #(\d+)',listing):
        if not inside(int(high)<<16|int(low)):raise SystemExit(f'reference outside the slot: {int(high)<<16|int(low):#x}')
    # Every literal-pool address must stay inside the slot (code, data or state).
    for m in re.finditer(r'\.word\t0x([0-9a-f]{8})',listing):
        v=int(m.group(1),16)
        if not inside(v):raise SystemExit(f'reference outside the slot: {v:#x}')
    record=build_overlay(Overlay(init,process,prefix,payload,secondary))
    if tail is not None:assert struct.unpack_from('<I',record,0)[0]==64 and struct.unpack_from('<I',record,40)[0]==REQ_MAGIC
    assert parse_overlay(record).primary==payload and parse_overlay(record).secondary==secondary
    params=tuple(DescriptorParameter(p['name'],f32bits(p['min']),f32bits(p['max']),f32bits(p['step']),f32bits(p['default']),p['storage_index'],p['knob'],p['flags'],p['display_code']) for p in meta['parameters'])
    if [p.storage_index for p in params]!=list(range(len(params))):raise SystemExit('this SDK version supports storage index = position only')
    if group==3 and 'linked_cab' not in meta:raise SystemExit('AMP effects need "linked_cab" (a stock cab id 0x0a0000xx): selecting an AMP rewrites CAB to its linked cab (NDS 0x45400); without one the pedal falls back to cab #0')
    word1=int(meta['linked_cab'],16) if group==3 else 0xffffffff
    descriptor=pad_descriptor(Descriptor(int(meta['public_id'],16),word1,0xffffff00|len(params),meta['name'],meta['type_name'],params,b''))
    blob=build_descriptor(descriptor);assert parse_descriptor(blob)==descriptor
    (out/'record.bin').write_bytes(record);(out/'descriptor.bin').write_bytes(blob)
    sha=lambda b:hashlib.sha256(b).hexdigest()
    manifest=dict(effect=meta,slot_base=hex(base),slot_bytes=size,payload_bytes=len(payload),state_bytes=bss_end-end,slot_bytes_free=base+size-bss_end,
        init_callback=hex(init),process_callback=hex(process),record_bytes=len(record),descriptor_bytes=len(blob),
        instruction_count=len(code),distinct_mnemonics=sorted(set(code)),integer_mnemonics_not_in_stock=unknown,
        diagnostic_external_addresses=sorted(hex(x) for x in external),compiler=run([CLANG,'--version']).splitlines()[0],linker=run([LD,'--version']).splitlines()[0],cflags=CFLAGS+(['-mllvm','-arm-restrict-it'] if meta.get('restrict_it') else []),
        sha256={'record.bin':sha(record),'descriptor.bin':sha(blob),'payload.bin':sha(payload),
                author_input_name(effect_dir/meta['source'],effect_dir):sha((effect_dir/meta['source']).read_bytes()),
                'sdk/include/gp50_effect.h':sha((SDK/'include/gp50_effect.h').read_bytes()),'sdk/overlay.ld':sha((SDK/'overlay.ld').read_bytes())})
    if stock_g is not None:manifest['stock_g_sha256']=sha(stock_g.read_bytes())
    if stack:manifest['internal_calls_stack']=stack
    if looper:manifest['looper_ring']=dict(object='0x20003a4c',base='0x29000000',cells=441024);manifest['sha256']['sdk/resources/gp50_looper.h']=sha((SDK/'resources'/'gp50_looper.h').read_bytes())
    if tail is not None:
        manifest['tail']=dict(bytes=tb,alignment=ta,required=bool(tail.get('required')),record_word0=64,requirements_offset=40,
            view_address=hex(RESIDENT_VIEW(group)),resident_adapter_installed=False)
        for n in ('gp50_tail.h','gp50_resident.h','gp50_resources.h'):manifest['sha256']['sdk/resources/'+n]=sha((SDK/'resources'/n).read_bytes())
    if copro:
        manifest['copro']=copro;manifest['secondary_bytes']=len(secondary)
        manifest['sha256'].update({'secondary.bin':sha(secondary),author_input_name(copro_path,effect_dir):sha(copro_path.read_bytes()),
            'sdk/copro/asm.py':sha((SDK/'copro/asm.py').read_bytes()),'sdk/copro/frame.py':sha((SDK/'copro/frame.py').read_bytes()),
            'protocol/copro_isa.py':sha((ROOT/'protocol/copro_isa.py').read_bytes()),'sdk/include/gp50_copro.h':sha((SDK/'include/gp50_copro.h').read_bytes())})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    global CLANG,LD,OBJCOPY,OBJDUMP,NM
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('effect_dir',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stock-g',type=Path,help='decoded g container from the supported user-supplied stock firmware')
    p.add_argument('--clang',help='Clang executable; default: %(default)s',default=CLANG)
    p.add_argument('--arm-bin',type=Path,help='directory containing arm-none-eabi ld/objcopy/objdump/nm',default=BIN)
    a=p.parse_args()
    CLANG=a.clang
    LD,OBJCOPY,OBJDUMP,NM=(a.arm_bin.resolve()/('arm-none-eabi-'+x) for x in ('ld','objcopy','objdump','nm'))
    if a.stock_g is not None and not a.stock_g.is_file():p.error('--stock-g must name an existing decoded container')
    m=build(a.effect_dir.resolve(),a.out.resolve(),a.stock_g.resolve() if a.stock_g else None)
    print(json.dumps({k:m[k] for k in ('payload_bytes','state_bytes','slot_bytes_free','init_callback','process_callback','record_bytes','descriptor_bytes','instruction_count','distinct_mnemonics')},indent=1))
if __name__=='__main__':main()
