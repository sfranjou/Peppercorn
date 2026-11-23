"""Automatic, deterministic placement of ordinary C objects into checked E pools.

A saved ledger preserves fitting reservations. New/grown objects are allocated by
best fit; objects that do not fit stay in B, whose existing section allocator runs
next. SDK sources carry no memory-region annotations or placement lists.
"""
import json
import re
from pathlib import Path


def allocate(objects, pools, previous=(), reserved=()):
    """Pure allocator. Sizes include conservative linker alignment allowances."""
    pools = sorted(pools)
    if any(lo >= hi or lo % 4 or hi % 4 for lo, hi in pools) or any(a[1] > b[0] for a,b in zip(pools,pools[1:])):
        raise ValueError('invalid automatic E pools')
    objects = {x['object']: dict(x) for x in objects}
    free = list(pools)
    for lo, hi in reserved:
        if lo >= hi:
            raise ValueError('invalid fixed reservation')
        lo, hi = lo & ~3, (hi+3) & ~3
        free = [(x,y) for a,b in free for x,y in ((a,min(b,lo)),(max(a,hi),b)) if x < y]
    capacity = sum(b-a for a,b in free)
    placed = {}

    def claim(lo, hi):
        for i, (a,b) in enumerate(free):
            if a <= lo < hi <= b:
                free[i:i+1] = [(x,y) for x,y in ((a,lo),(hi,b)) if x < y]
                return
        raise ValueError('overlapping/out-of-pool automatic E ledger')

    seen = set()
    for old in previous:
        key = old['object']; lo, hi = old['address'], old['end']
        if key in seen or lo % 4 or hi % 4 or not any(a <= lo < hi <= b for a,b in pools):
            raise ValueError('invalid automatic E ledger')
        seen.add(key)
        # Validate even obsolete reservations so a damaged ledger cannot pass.
        if any(lo < x['end'] and x['address'] < hi for x in previous if x is not old):
            raise ValueError('overlapping automatic E ledger')
        if key in objects and objects[key]['required'] <= hi-lo and any(a <= lo < hi <= b for a,b in free):
            claim(lo,hi)
            placed[key] = dict(objects[key], address=lo, end=hi, retained=True)
    for key, obj in sorted(objects.items(), key=lambda kv: (-kv[1]['required'],kv[0])):
        if key in placed:
            continue
        need = (obj['required']+3) & ~3
        if need <= 0:
            raise ValueError('empty automatic E object')
        candidates = [(b-a-need,a) for a,b in free if b-a >= need]
        if candidates:
            _, lo = min(candidates)
            claim(lo,lo+need)
            placed[key] = dict(obj,address=lo,end=lo+need,retained=False)
    rows = sorted(placed.values(),key=lambda x:x['address'])
    return dict(schema=1, allocations=rows,
                fallback_b=sorted(set(objects)-set(placed)),
                capacity_bytes=capacity,
                reserved_bytes=sum(x['end']-x['address'] for x in rows),
                free_bytes=sum(b-a for a,b in free),
                largest_free_bytes=max((b-a for a,b in free),default=0),
                free_ranges=[dict(address=a,end=b) for a,b in free],
                retained_objects=sum(x['retained'] for x in rows))


def from_link_map(map_text, sources, alignments, pools, previous=(), section_sizes=None):
    """Count GC-live text/rodata only, excluding the separate catalog reservation."""
    source_by_stem = {Path(s).stem: s for s in sources}
    body = map_text.split('Linker script and memory map',1)[1]
    body = re.sub(r'(^ [.]\S+)\n\s+(0x)',r'\1 \2',body,flags=re.M)
    # Only default B output sections: catalog data is separately reserved.
    body = '\n'.join(part for part in re.split(r'(?=^\.\S+)', body, flags=re.M)
                     if re.match(r'^\.(?:text|rodata)\s', part))
    sizes = {}
    for m in re.finditer(r'^ (\.(?:text|rodata)\S*)\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+(\S+\.o)$',body,re.M):
        sec, address, size, obj = m.groups(); size = int(size,16)
        # Merged strings can have shortened/zero map sizes in the shared B
        # output, then expand when each object has a separate E output section.
        # Reserve the unmerged input size for every live section instead.
        if section_sizes is not None:
            size = max(size, section_sizes[obj][sec])
        if not size:
            continue
        # Each section can add up to alignment-1 padding; another 3 bytes cover
        # the text-to-rodata boundary. Overestimation is intentional and reported.
        sizes[obj] = sizes.get(obj,3) + size + max(4,alignments[obj].get(sec,4))-1
    objects = [dict(object=Path(o).name,source=source_by_stem[Path(o).stem],required=n) for o,n in sizes.items()]
    catalog = re.search(r'^\.catalog_ext\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)', map_text, re.M)
    reserved = []
    if catalog:
        address, size = (int(v,16) for v in catalog.groups())
        if size:
            reserved.append((address,address+size))
    return allocate(objects,pools,previous,reserved)


def spans(report):
    return [dict(name='obj_'+Path(x['object']).stem,address=hex(x['address']),end=hex(x['end']),sources=[x['source']])
            for x in report['allocations']]


def load_previous(path):
    if not path.exists():
        return []
    saved = json.loads(path.read_text())
    if saved.get('schema') != 1:
        raise ValueError('unknown automatic E ledger schema')
    return saved['allocations']
