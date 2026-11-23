"""Bind every live allocated B ELF section to the composed B and its ledger."""
import struct


def verify(elf,region_b,ledger,base=0x10000):
    assert elf[:6]==b'\x7fELF\x01\x01','expected ELF32 little endian'
    off=struct.unpack_from('<I',elf,32)[0]
    stride,count,names_index=struct.unpack_from('<HHH',elf,46)
    assert stride==40 and count and names_index<count
    headers=[struct.unpack_from('<10I',elf,off+i*stride)for i in range(count)]
    strings=headers[names_index];names=elf[strings[4]:strings[4]+strings[5]]
    expected={r['output'] for r in ledger['allocations']}; rows=[]
    for n,typ,flags,at,pos,size,*_ in headers:
        if not flags&2 or not size or at>=0x190000:continue
        name=names[n:names.index(b'\0',n)].decode('ascii')
        assert name in expected and typ==1 and not flags&1,('unplanned/invalid B section',name)
        assert base<=at<at+size<=base+len(region_b),(name,'B bounds')
        raw=elf[pos:pos+size]
        assert len(raw)==size and raw==region_b[at-base:at-base+size],(name,'ELF/image mismatch')
        reservations=[r for r in ledger['allocations'] if r['output']==name]
        if name.startswith('.hole_'):
            assert at==min(r['address'] for r in reservations) or at==next(p['start'] for p in ledger['pools'] if p['id']==reservations[0]['pool'])
            assert at+size==max(r['address']+r['size'] for r in reservations)
        else:
            assert len(reservations)==1
            r=reservations[0]
            assert at==r['address'] and size==r['linked_size'] and size<=r['capacity']
        assert not any(at<r['end'] and r['address']<at+size for r in rows),'B section overlap'
        rows.append(dict(name=name,address=at,end=at+size,executable=bool(flags&4)))
    assert {r['name']for r in rows}==expected,'missing B sections'
    return rows
