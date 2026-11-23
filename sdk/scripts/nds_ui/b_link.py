"""Stable B link adapter. Proposals are committed by the completed image builder.

Code uses verified holes or bounded tail; data uses tail only. Each tail input
has its own output section, so raw mergeable-string sizes are conservative and
no reservation depends on cross-section string merging. No mutable C state.
"""
import hashlib
import json
import re
from pathlib import Path
from .b_placement import plan


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_previous(path, root):
    if not path.exists():
        return None
    ledger = json.loads(path.read_text())
    provenance = ledger.get('validated_artifacts')
    if not provenance:
        raise ValueError('B ledger lacks validated build provenance')
    for name, digest in provenance.items():
        p = root / name
        if not p.is_file() or sha(p) != digest:
            raise ValueError('B ledger validated artifact changed: ' + name)
    return ledger


def propose(map_text, objects, aligns, sizes, holes, base, limit, previous=None, repack=False):
    # Only kept inputs, after E selection. Discarded/GC inputs precede this marker.
    body = map_text.split('Linker script and memory map', 1)[1]
    rows = re.findall(r'^ (\.(?:text|rodata)\S*)\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+(\S+\.o)$', body, re.M)
    by_path = {str(o): o for o in objects}
    if len({p.name for p in objects}) != len(objects):
        raise ValueError('B object basenames must be unique')
    pools = [dict(id=f'hole_{lo:x}', start=lo, end=hi) for lo,hi,_ in holes]
    pools.append(dict(id='tail', start=base, end=limit))
    items = []; sources = {}; seen = set()
    for sec, at, size, obj in rows:
        if not base <= int(at,16) < 0x190000:
            continue
        if obj not in by_path:
            raise ValueError('unknown live B object: ' + obj)
        key = Path(obj).name + ':' + sec
        if key in seen:
            raise ValueError('duplicate live B input: ' + key)
        seen.add(key)
        size = sizes[obj][sec]  # raw size; shared-map strings may have merged
        if not size: continue
        allowed = [p['id'] for p in pools if sec.startswith('.text') or p['id']=='tail']
        items.append(dict(id=key, size=size, align=max(2 if sec.startswith('.text') else 1, aligns[obj][sec]), pools=allowed))
        sources[key] = (obj,sec)
    ledger = plan(items,pools,previous,repack=repack)
    placed = {}; clauses = []
    for row in sorted(ledger['allocations'],key=lambda r:r['address']):
        obj,sec = sources[row['id']]; lo=row['address']; cap=row['capacity']
        if row['pool'] != 'tail':
            start = next(p['start'] for p in pools if p['id']==row['pool'])
            placed.setdefault(start,[]).append((obj,sec,row['size'],lo))
            row['output'] = '.hole_' + format(start,'x')
        else:
            kind = '.text' if sec.startswith('.text') else '.rodata'
            name = kind + '.b_' + hashlib.sha256(row['id'].encode()).hexdigest()[:20]
            row['output'] = name
            clauses.append(f'{name} {lo:#x} : {{ {obj}({sec}) }}\nASSERT(SIZEOF({name}) <= {cap}, "B reservation overflow: {row["id"]}")')
    for lo,rows in sorted(placed.items()):
        body = ' '.join(f'. = {at-lo:#x}; {obj}({sec})' for obj,sec,_,at in rows)
        end = rows[-1][3] + rows[-1][2]
        clauses.append(f'.hole_{lo:x} {lo:#x} : {{ {body} }}\nASSERT(SIZEOF(.hole_{lo:x}) <= {end-lo}, "B hole overflow")')
    return ledger,placed,'\n'.join(clauses)+'\n'


def commit(path, proposal, artifacts, root):
    """Atomic publication only after caller's link/container/section checks pass."""
    ledger = dict(proposal, validated_artifacts={str(p.relative_to(root)):sha(p) for p in artifacts})
    if not ledger['validated_artifacts']:
        raise ValueError('B ledger commit needs validation artifacts')
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(ledger,indent=2)+'\n')
    temp.replace(path)
    return ledger
