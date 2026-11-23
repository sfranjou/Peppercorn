"""Persistent B reservation planner. Pure reservation proposals; linker integration lives in b_link.py.

Pools must come from the reviewed B-hole inventory and bounded B tail. Item keys
are stable input-section identities, never linker output ordinals. Callers own
ELF liveness/alignment discovery, pinned hooks and commit-after-validation.
"""
import copy

SCHEMA = 1


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid B reservation integer')
    return value


def _pools(rows):
    pools = {}
    for row in rows:
        name = row['id']
        if not isinstance(name, str) or not name or name in pools:
            raise ValueError('duplicate/invalid B pool identity')
        lo, hi = _integer(row['start']), _integer(row['end'])
        if hi <= lo: raise ValueError('empty B pool')
        pools[name] = (lo, hi)
    spans = sorted(pools.values())
    if any(b[0] < a[1] for a,b in zip(spans,spans[1:])):
        raise ValueError('overlapping B pools')
    return pools


def _rows(rows, pools):
    result = {}
    for row in rows:
        key=row['id'];at=_integer(row['address']);cap=_integer(row['capacity'],1)
        align=_integer(row['align'],1);size=_integer(row['size'],1)
        if not isinstance(key,str) or not key or key in result:
            raise ValueError('duplicate/invalid B section identity')
        if align & (align-1) or at % align or size > cap:
            raise ValueError('invalid B section alignment/size')
        if row['pool'] not in pools or not (pools[row['pool']][0] <= at < at+cap <= pools[row['pool']][1]):
            raise ValueError('B reservation outside pool')
        result[key]=dict(row)
    spans=sorted((r['address'],r['address']+r['capacity']) for r in result.values())
    if any(b[0] < a[1] for a,b in zip(spans,spans[1:])):
        raise ValueError('overlapping B reservations')
    return result


def plan(items, pools, previous=None, *, repack=False):
    """Return a proposal; never mutate/commit caller state or silently repack.

    Keep fitting reservations including their slack. Release removed sections;
    new/grown sections use aligned best fit. Growth may relocate its own section.
    Previous ledgers are fully validated even when explicit repack is requested.
    """
    pools=copy.deepcopy(pools);current=_pools(pools);old={}
    if previous is not None:
        if previous.get('schema') != SCHEMA: raise ValueError('incompatible B ledger schema')
        old=_rows(previous['allocations'],_pools(previous['pools']))
    live={}
    for source in items:
        row=dict(source);key=row['id'];size=_integer(row['size'],1);align=_integer(row['align'],1)
        if not isinstance(key,str) or not key or key in live: raise ValueError('duplicate/invalid B section identity')
        if align & (align-1): raise ValueError('invalid B section alignment')
        eligible=row.get('pools', list(current))
        if not eligible or len(set(eligible)) != len(eligible) or any(p not in current for p in eligible):
            raise ValueError('invalid eligible B pools')
        live[key]=dict(id=key,size=size,align=align,pools=list(eligible))
    kept={}
    if not repack:
        for key,item in sorted(live.items()):
            prior=old.get(key)
            if prior is None: continue
            lo,hi=current.get(prior['pool'],(0,0));at=prior['address'];cap=prior['capacity']
            if prior['pool'] in item['pools'] and lo <= at < at+cap <= hi and item['size'] <= cap and at % item['align'] == 0:
                kept[key]=dict(item,address=at,capacity=cap,pool=prior['pool'])
    # Guard even changed pool inventories before allocating any fresh sections.
    _rows(kept.values(),current)
    def gaps():
        free=[]
        for name,(lo,hi) in sorted(current.items()):
            cursor=lo
            for row in sorted((r for r in kept.values() if r['pool']==name),key=lambda r:r['address']):
                if row['address'] > cursor: free.append((cursor,row['address'],name))
                cursor=row['address']+row['capacity']
            if cursor<hi: free.append((cursor,hi,name))
        return free
    for key,item in sorted(live.items(),key=lambda kv:(-kv[1]['size'],-kv[1]['align'],kv[0])):
        if key in kept:continue
        options=[]
        for lo,hi,name in gaps():
            at=(lo+item['align']-1)&-item['align']
            if name in item['pools'] and at+item['size'] <= hi:options.append((hi-lo,at,name))
        if not options:
            free=gaps();total=sum(hi-lo for lo,hi,_ in free);largest=max((hi-lo for lo,hi,_ in free),default=0)
            raise ValueError(f'B placement exhausted for {key}: needs {item["size"]} bytes aligned {item["align"]}; free {total}, largest span {largest}; explicit repack may help fragmentation')
        _,at,name=min(options)
        kept[key]=dict(item,address=at,capacity=item['size'],pool=name)
    _rows(kept.values(),current)
    free=gaps()
    return dict(schema=SCHEMA,pools=pools,allocations=[kept[k] for k in sorted(kept)],
                free_bytes=sum(hi-lo for lo,hi,_ in free),largest_free_span=max((hi-lo for lo,hi,_ in free),default=0),
                retained=sum(k in old and old[k]['address']==r['address'] and old[k]['capacity']==r['capacity'] for k,r in kept.items()),
                repacked=bool(repack))
