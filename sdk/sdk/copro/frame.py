"""Frame rules for a coprocessor program that the stock loader copies into a group's program slot.

Offline only. Evidence and markings: analysis/firmware/COPRO_EFFECTS.md. The stock chain is one
program: DST at PC 0 -> jump 0x500 (AMP) -> jump 0xb00 (CAB) -> jump 0xe00 (EQ) -> end word.
A program we ship in a slot must look to its neighbours exactly like a stock one:

  entry      the five words every stock DST program has at its bypass test (nine of ten have
             them as words 0..4):  r0 = #0; D[0x10] = r0; r5 = #0x193; r6 = D[r5];
             skip 1 if bit 0 of r6; then a jump to the bypass exit
  work       in place on the left input window D[0x13..0x52]
  exit       `jump <next slot base>` on both paths (active and bypass); never the end word,
             never a fall-through, never a return without a call
  registers  nothing may be read before it is written (the previous stage leaves no promise),
             and the next stage is promised nothing

`check(group, words)` enforces this plus: size within the slot, every word a form executed on
the pedal (X) unless explicitly allowed, every branch target inside the program, direct data
addresses inside the group's cell range / the exchange window / the shared scratch buffer.
"""
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from protocol import copro_isa as isa  # noqa: E402

# DSP_LOADER.md slot table (secondary destination, clear bytes) and DSP_COPROCESSOR.md memory layout.
# cells: [first, end) data words owned by the group. DST: flag at D[0x193] (ARM 0x2800064c); stock DST
# code addresses up to D[0x274]; the AMP group's first cell is D[0x398].
SLOTS={2:dict(name='DST',pc=0x000,capacity_bytes=0x1400,next_pc=0x500,flag_cell=0x193,cells=(0x193,0x398),
              primary_base=0x10003800,primary_bytes=0x1000),
       # AMP (group 3): stock entry r5 = #0x398; r6 = D[r5]; skip if bit 0; jump <bypass> (29 of 32 stock
       # AMP programs), both exits `jump 0xb00` (CAB slot). Not loaded while N->S (group 9) is enabled:
       # N->S occupies the AMP+CAB slots. Descriptor word 1 = linked cab id (stock: 0x0a0000xx).
       3:dict(name='AMP',pc=0x500,capacity_bytes=0x1800,next_pc=0xb00,flag_cell=0x398,cells=(0x398,0x580),
              primary_base=0x10004800,primary_bytes=0x2c00,entry=(0x75060398,0xe6520000,0x96080001),bypass_index=3),
       # CAB (group 4): PC 0xb00, 0xc00 bytes, exits `jump 0xe00` (EQ). The stock CAB entry writes
       # D[0xf68] (CAB-internal, COPRO_EQ_SDK.md) and tests its flag with an unexecuted 174-word skip;
       # own programs use the proven AMP-style entry instead: r5 = #0x580; r6 = D[r5]; skip if bit 0;
       # jump <bypass>. Cells D[0x580..0xf9b] (below the EQ cells). Not loaded while N->S is enabled.
       4:dict(name='CAB',pc=0xb00,capacity_bytes=0xc00,next_pc=0xe00,flag_cell=0x580,cells=(0x580,0xf9c),
              primary_base=0x10007400,primary_bytes=0x1800,entry=(0x75060580,0xe6520000,0x96080001),bypass_index=3),
       # N->S (group 9): one record serves all 80 SnapTone slots; it occupies the AMP+CAB slots on both
       # processors (ARM 0x10004800 + 0x4400, program PC 0x500 + 0x2400 bytes, exits `jump 0xe00`), and
       # groups 3/4 are not loaded while it is enabled. Flag D[0x398] like AMP; stock cells 0x398..0xf6b,
       # CAB scalars up to 0xf9b are free with it. Init r1 = &content pointer (2,696-byte slot record,
       # 0x6f34). analysis/firmware/NS_SLOT.md.
       9:dict(name='N->S',pc=0x500,capacity_bytes=0x2400,next_pc=0xe00,flag_cell=0x398,cells=(0x398,0xf9c),
              primary_base=0x10004800,primary_bytes=0x4400,entry=(0x75060398,0xe6520000,0x96080001),bypass_index=3)}
# Slots whose stock program an effect reuses byte-for-byte (ARM primary computes the cells).
# EQ (group 5): one 93-word program shared by all five stock EQ models (inventory SHA below);
# flag D[0xf9c], five 10-word biquad sections D[0xf9d + 10k] = b0 b1 b2 a0 a1 a2 x1 x2 y1 y2
# (coprocessor scales by an approximate 1/a0; only a0 = 1.0 is hardware-measured: k = 0x3f7fffb7^2),
# output level target D[0xfcf] and current D[0xfd0] (ramped per block), then copy to both outputs.
STOCK_SLOTS={5:dict(name='EQ',program='eq',pc=0xe00,capacity_bytes=0x800,flag_cell=0xf9c,cells=(0xf9c,0xfd1),
                    primary_base=0x10008c00,primary_bytes=0x1400,stock_group=5,stock_record=0,
                    program_sha256='1600ca2b683aea720f9dff7a25010b8a81a941ff1de0ca6d7b07fc1dd1137bae',
                    named_cells=dict(ENABLE=0xf9c,BAND0=0xf9d,BAND1=0xfa7,BAND2=0xfb1,BAND3=0xfbb,BAND4=0xfc5,LEVEL_TARGET=0xfcf,LEVEL=0xfd0))}
STOCK_DST_ENTRY=(0x70060000,0x50080010,0x75060193,0xe6520000,0x96080001)
WINDOW=(0x13,0x53)          # left input window, processed in place by every stage
SCRATCH=(0x113,0x153)       # 64-word scratch buffer every stock stage uses freely (gain ramps)
REG=re.compile(r'r(\d+)')


class FrameError(ValueError):pass


def effects(word):
    """(reads, writes, kind) from the decoder text, or None for a word the decoder does not know.
    kind: None, ('jump',t), ('loop',t), ('call',t), ('skip',n), 'ret', 'end'."""
    full,status=isa.decode(word);text=full.split(';')[0].strip()
    if status=='?':return None
    m=re.match(r'^call (0x[0-9a-f]+)$',text)
    if m:
        link=re.search(r'link r(\d+)\.(?:hi|lo)',full)          # aR06: the return PC is written to rR.hi (r14 untracked)
        return set(),({int(link[1])} if link and int(link[1])!=14 else set()),('call',int(m[1],16))
    if text=='return':return set(),set(),'ret'
    m=re.match(r'^return to r(\d+)\.(?:hi|lo)$',text)
    if m:return ({int(m[1])} if int(m[1])!=14 else set()),set(),'ret'
    m=re.match(r'^skip (\d+) if r(\d+) != r(\d+)$',text)
    if m:return {int(m[2]),int(m[3])},set(),('skip',int(m[1]))
    m=re.match(r'^branch (-\d+) if r(\d+) != r(\d+)$',text)
    if m:return {int(m[2]),int(m[3])},set(),('skip',int(m[1]))   # a backward count: the scan pushes pc+1+n
    m=re.match(r'^skip (\d+) if r(\d+) >= r(\d+)$',text)
    if m:return {int(m[2]),int(m[3])},set(),('skip',int(m[1]))
    if text=='end':return set(),set(),'end'
    m=re.match(r'^jump (0x[0-9a-f]+)$',text)
    if m:return set(),set(),('jump',int(m[1],16))
    m=re.match(r'^loop r(\d+) -> (0x[0-9a-f]+)$',text)
    if m:return {int(m[1])},{int(m[1])},('loop',int(m[2],16))
    m=re.match(r'^skip (\d+) (?:if|unless) (negative|bit \d+ of r(\d+))$',text)
    if m:return ({int(m[3])} if m[3] and int(m[3])!=15 else set()),set(),('skip',int(m[1]))
    if text.startswith('block '):
        # Block words (executed 2026-10-12): reads r9, r10 (+ r8 when named, + r11 as destination pointer); writes r9..r11.
        reads={9,10}|({8} if 'r8' in text else set())|({11} if 'D[r11' in text or re.match(r'^block 0x',text) else set())
        if re.match(r'^block 0x',text):reads|={8}
        return reads,{9,10,11},None
    m=re.match(r'^D\[(.+?)\] = r(\d+)$',text)
    if m:
        reads={int(m[2])};writes=set();p=REG.match(m[1])
        if p:
            reads.add(int(p[1]))
            if m[1].endswith('++'):writes.add(int(p[1]))
        return reads,writes,None
    m=re.match(r'^r(\d+)(\.hi|\.lo)? (=|\+=|-=|\*=|&=|\|=|\^=) (.*)$',text)
    if m:
        d=int(m[1]);reads={int(x) for x in REG.findall(m[4])};writes={d}
        if m[3]!='=':reads.add(d)
        p=re.search(r'[DP]\[r(\d+)\+\+\]',m[4])
        if p:writes.add(int(p[1]))
        return reads,writes,None
    raise ValueError(f'cannot classify {word:#010x}: {text}')


def scan(words,base,entry=None,external=()):
    """Must-defined register dataflow from the entry. Calls are followed into the callee and the
    word after the call is entered with the call-site state (callee writes ignored: conservative).
    r14/r15 are not tracked. Unknown words read/write nothing here and are counted. A `jump` to an `external` target
    is an exit even inside the word range (NS Capture v6: USER_PC lies inside mode-exclusive GPTC code)."""
    n=len(words);entry=base if entry is None else entry
    state={entry:frozenset()};work=[entry];flagged={};unknown=set();unknown_touching={};exits=set()
    def push(pc,s):
        if not base<=pc<base+n:exits.add(pc);return
        old=state.get(pc);new=s if old is None else old&s
        if new!=old:state[pc]=new;work.append(pc)
    while work:
        pc=work.pop();s=state[pc];w=words[pc-base];e=effects(w)
        if e is None:
            unknown.add(pc);op,a,b=w>>28,w>>24&15,w>>20&15
            if op in (8,0xc,0xe,0xf,9,7,5):
                miss={r for r in (a,b) if r<14 and r not in s}
                if miss:unknown_touching[pc]=sorted(miss)
            push(pc+1,s);continue
        reads,writes,kind=e
        miss={r for r in reads if r<14 and r not in s}
        if miss:flagged.setdefault(pc,set()).update(miss)
        s2=s|frozenset(r for r in writes if r<14)
        if kind is None:push(pc+1,s2)
        elif kind=='end':exits.add('end')
        elif kind=='ret':pass
        elif kind[0]=='jump':
            if kind[1] in external:exits.add(kind[1])
            else:push(kind[1],s2)
        elif kind[0] in ('loop','call'):push(kind[1],s2);push(pc+1,s2)
        elif kind[0]=='skip':push(pc+1,s2);push(pc+1+kind[1],s2)
    return dict(read_before_write={f'{pc:#05x}':sorted(v) for pc,v in sorted(flagged.items())},
                unknown_words=len(unknown),unknown_touching={f'{pc:#05x}':v for pc,v in sorted(unknown_touching.items())},
                exits=sorted(f'{x:#05x}' if isinstance(x,int) else x for x in exits),reached=len(state))


# Own programs in the EQ slot (last stage, PC 0xe00, 0x800 bytes): stock entry words 0..2, word 3 a
# jump to the bypass path inside the program; every path must end in the end-of-block word (the
# only allowed non-X word: S in isolation, but stock EQ executes it at the end of every audio
# block); outputs D[0x93..0xd2] (L) and D[0xd3..0x112] (R) are read by the ARM host (E).
EQ_OWN=dict(name='EQ',pc=0xe00,capacity_bytes=0x800,flag_cell=0xf9c,cells=(0xf9c,0x1000),primary_base=0x10008c00,primary_bytes=0x1400)
STOCK_EQ_ENTRY=(0x75060f9c,0xe6520000,0x96080001)
END_WORD=0xa00e0000
OUTPUTS=(0x93,0x113)


def check_eq(words,allowed_non_x=()):
    """Frame rules for an own EQ-slot program (see EQ_OWN). Returns a report dict."""
    base=EQ_OWN['pc'];n=len(words);fail=[]
    if n<5:raise FrameError('program too short for the EQ frame')
    if 4*n>EQ_OWN['capacity_bytes']:fail.append(f'{4*n:#x} bytes exceed the EQ slot capacity')
    if tuple(words[:3])!=STOCK_EQ_ENTRY:fail.append('words 0..2 are not the stock EQ entry (r5 = #0xf9c; r6 = D[r5]; skip if bit 0)')
    w=words[3];t=w&0xfff
    if w>>16!=0xa008 or not base<t<base+n:fail.append('word 3 is not a jump to the bypass path inside the program')
    non_x=[];allowed={int(x) for x in allowed_non_x}|{END_WORD}
    for i,w in enumerate(words):
        text,status=isa.decode(w)
        if status!='X':
            non_x.append(dict(pc=f'{base+i:#05x}',word=f'{w:08x}',status=status,text=text))
            if w not in allowed:fail.append(f'PC {base+i:#05x}: {w:08x} ({text}) is not a form executed on the pedal')
        e=effects(w)
        if e is None:continue
        kind=e[2]
        if kind=='ret':fail.append(f'PC {base+i:#05x}: return (no calls are allowed by this checker)')
        if isinstance(kind,tuple) and kind[0] in ('jump','loop','call'):
            t=kind[1]
            if kind[0]=='call':fail.append(f'PC {base+i:#05x}: call (not allowed by this checker)')
            elif not base<=t<base+n:fail.append(f'PC {base+i:#05x}: target {t:#05x} outside the program')
            elif kind[0]=='loop' and t>base+i:fail.append(f'PC {base+i:#05x}: forward loop target')
        if w>>28==2 and (w>>16&15) not in (0,3,4,7,8,0xc,0xd):fail.append(f'PC {base+i:#05x}: block word not among the executed float forms')
        if w>>28==5:
            a=w&0xffff;lo,hi=EQ_OWN['cells']
            if not (WINDOW[0]<=a<OUTPUTS[1] or SCRATCH[0]<=a<SCRATCH[1] or lo<=a<hi):
                fail.append(f'PC {base+i:#05x}: direct data address D[{a:#x}] outside the EQ cells, windows and scratch')
    flow=scan(list(words),base)
    if flow['exits']!=['end']:fail.append(f'exits {flow["exits"]}: every path must end in the end-of-block word')
    if flow['read_before_write']:fail.append(f'register read before written: {flow["read_before_write"]}')
    if flow['reached']!=n:fail.append(f'{n-flow["reached"]} unreachable word(s)')
    if fail:raise FrameError('; '.join(fail))
    return dict(group=5,slot='EQ',pc_base=base,words=n,bytes=4*n,capacity_bytes=EQ_OWN['capacity_bytes'],non_x=non_x,dataflow=flow,
                note='end word: static-only in isolation, executed every block by the stock EQ program')


def check(group,words,allowed_non_x=(),allow_calls=False,external_targets=()):
    """Raise FrameError unless `words` is an acceptable program for the group's slot.
    allow_calls: one-level calls linking r14 (`ae06 4ttt` / `ae0a 4000`, executed in every probe harness), into
    the program, with no call inside a callee. Returns a report dict (sizes, statuses, non-X words used, dataflow)."""
    if group not in SLOTS:raise FrameError(f'no coprocessor program slot rules for group {group}')
    slot=SLOTS[group];base,nxt=slot['pc'],slot['next_pc'];n=len(words);fail=[]
    if not n:raise FrameError('empty program')
    if 4*n>slot['capacity_bytes']:fail.append(f'{4*n:#x} bytes exceed the slot capacity {slot["capacity_bytes"]:#x}')
    if base+n>nxt:fail.append('program reaches the next slot base')
    entry=slot.get('entry',STOCK_DST_ENTRY);bi=slot.get('bypass_index',5)
    if tuple(words[:len(entry)])!=tuple(entry):fail.append(f'words 0..{len(entry)-1} are not the stock {slot["name"]} entry / bypass test')
    jump_next=isa.jump(nxt)
    if n>bi:
        w=words[bi];t=w&0xfff
        if w>>16!=0xa008 or not base<=t<base+n or words[t-base]!=jump_next:fail.append(f'word {bi} is not a jump to a `jump next-slot` word (bypass exit)')
    else:fail.append('program too short for the frame')
    non_x=[];allowed={int(x) for x in allowed_non_x}
    for i,w in enumerate(words):
        text,status=isa.decode(w)
        if status!='X':
            non_x.append(dict(pc=f'{base+i:#05x}',word=f'{w:08x}',status=status,text=text))
            if w not in allowed:fail.append(f'PC {base+i:#05x}: {w:08x} ({text}) is not a form executed on the pedal and is not listed as allowed')
        e=effects(w)
        if e is None:continue
        kind=e[2]
        if kind=='end':fail.append(f'PC {base+i:#05x}: end-of-block word in a non-final slot')
        if kind=='ret' and not (allow_calls and w==isa.RETURN):fail.append(f'PC {base+i:#05x}: return (no calls are allowed by this checker)')
        if isinstance(kind,tuple) and kind[0] in ('jump','loop','call'):
            t=kind[1]
            if kind[0]=='call':
                if not allow_calls or w>>12!=0xae064:fail.append(f'PC {base+i:#05x}: call (only one-level r14 flavour-4 calls, with allow_calls)')
                elif not base<=t<base+n:fail.append(f'PC {base+i:#05x}: call target {t:#05x} outside the program')
                else:
                    for k in range(t-base,n):            # the callee, up to its return, must not call
                        if words[k]==isa.RETURN:break
                        if (effects(words[k]) or (0,0,None))[2] and isinstance(effects(words[k])[2],tuple) and effects(words[k])[2][0]=='call':
                            fail.append(f'PC {base+i:#05x}: the callee at {t:#05x} calls again (only one level was executed)');break
                    else:fail.append(f'PC {base+i:#05x}: callee at {t:#05x} has no return')
            elif not (base<=t<base+n or (kind[0]=='jump' and (t==nxt or t in external_targets))):fail.append(f'PC {base+i:#05x}: target {t:#05x} outside the program')
            elif kind[0]=='loop' and t>base+i:fail.append(f'PC {base+i:#05x}: forward loop target')
        if w>>28==2 and (w>>16&15) not in (0,3,4,7,8,0xc,0xd):fail.append(f'PC {base+i:#05x}: block word not among the executed float forms')
        if w>>28==5:
            a=w&0xffff;lo,hi=slot['cells']
            if not (a==0x10 or WINDOW[0]<=a<WINDOW[1] or SCRATCH[0]<=a<SCRATCH[1] or lo<=a<hi):
                fail.append(f'PC {base+i:#05x}: direct data address D[{a:#x}] outside the group cells, window and scratch')
    flow=scan(list(words),base,external=tuple(external_targets))
    exits=[e for e in flow['exits'] if not (e.startswith('0x') and int(e,16) in external_targets)]   # external_targets: e.g. NS Capture v5's jump into user code
    if exits!=[f'{nxt:#05x}']:fail.append(f'exits {flow["exits"]}: must be exactly the jump to {nxt:#05x}')
    if flow['read_before_write']:fail.append(f'register read before written: {flow["read_before_write"]}')
    if flow['reached']!=n:fail.append(f'{n-flow["reached"]} unreachable word(s)')
    if fail:raise FrameError('; '.join(fail))
    return dict(group=group,slot=slot['name'],pc_base=base,words=n,bytes=4*n,capacity_bytes=slot['capacity_bytes'],
                next_pc=nxt,non_x_words=non_x,dataflow=flow)
