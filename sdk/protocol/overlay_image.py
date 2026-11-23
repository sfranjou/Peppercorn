"""Offline exact parser/serializer for the V1.1.0 effect containers. No device access.

Region g (ARM overlays) and the catalog inside region e (at +0x10000) share one
container: five header words, eleven group offsets, per-group blocks of
(count, record offsets), then contiguous records. Records are kept as exact byte
blobs; typed views (overlay record, catalog descriptor) parse and rebuild a blob
exactly, so edits can be made on named fields while every unknown byte is carried.

Evidence: analysis/firmware/ARM_MAPPING.md, DSP_LOADER.md (six-word overlay
record; loader copies record+word0), protocol/catalog.py (descriptor fields).
Header words whose meaning is not established are preserved verbatim and listed
in Container.unknown_words so a size-changing edit cannot silently ignore them.
"""
from __future__ import annotations
from dataclasses import dataclass,field,replace
import struct

GROUPS=11


class ImageError(ValueError):
    pass


@dataclass
class Container:
    word0: int
    word2: int
    word3: int
    word4: int
    groups: list  # eleven entries: list of record blobs, or None when the group offset is 0
    word2_is_first_record: bool
    payload_size_words: tuple=()  # which of word2/word3 equal total length minus first record offset
    directory_pad: int=0  # zero bytes between the last group block and the first record
                          # (g: 0; e catalog: 12 = room for the absent eleventh block)
    trailing: bytes=b''

    @property
    def unknown_words(self):
        names=dict(word0=self.word0)
        if 3 not in self.payload_size_words:names['word3']=self.word3
        if not self.word2_is_first_record and 2 not in self.payload_size_words:names['word2']=self.word2
        return names

    def records(self):
        return [r for g in self.groups if g is not None for r in g]


def parse_container(data: bytes) -> Container:
    data=bytes(data)
    if len(data)<0x40:raise ImageError('too short')
    w0,total,w2,w3,w4=struct.unpack_from('<5I',data,0)
    if w4!=0x0b0001ff:raise ImageError('unexpected directory marker')
    if not 0x40<=total<=len(data):raise ImageError('bad total length')
    offsets=struct.unpack_from('<11I',data,0x14)
    tables=[];cursor=0x40
    for o in offsets:
        if o==0:tables.append(None);continue
        if o!=cursor:raise ImageError('group blocks are not contiguous in group order')
        count=struct.unpack_from('<I',data,o)[0]
        if not 1<=count<=255:raise ImageError('implausible record count')
        tables.append(struct.unpack_from(f'<{count}I',data,o+4));cursor=o+4+4*count
    if any(t is None for t in tables[:-1]) and any(t is not None for t in tables[tables.index(None):]):
        raise ImageError('absent group before a present one')
    flat=[r for t in tables if t is not None for r in t]
    if not flat or flat!=sorted(set(flat)):raise ImageError('record offsets not strictly increasing in directory order')
    if flat[0]<cursor or any(data[cursor:flat[0]]):
        raise ImageError('records overlap the directory or nonzero directory padding')
    bounds=flat+[total];blobs=[data[a:b] for a,b in zip(bounds,bounds[1:])]
    groups=[];i=0
    for t in tables:
        if t is None:groups.append(None);continue
        groups.append(blobs[i:i+len(t)]);i+=len(t)
    sized=tuple(i for i,w in ((2,w2),(3,w3)) if w==total-flat[0])
    return Container(w0,w2,w3,w4,groups,w2==flat[0],sized,flat[0]-cursor,data[total:])


def build_container(c: Container) -> bytes:
    if len(c.groups)!=GROUPS:raise ImageError('eleven group entries required')
    present=[g for g in c.groups if g is not None]
    if any(not g for g in present):raise ImageError('present group needs at least one record')
    first=0x40+sum(4+4*len(g) for g in present)+c.directory_pad
    offsets=[];blocks=b'';cursor=0x40;position=first
    for g in c.groups:
        if g is None:offsets.append(0);continue
        offsets.append(cursor);table=[]
        for blob in g:
            if len(blob)%4:raise ImageError('record length must be a multiple of four')
            table.append(position);position+=len(blob)
        blocks+=struct.pack(f'<I{len(g)}I',len(g),*table);cursor+=4+4*len(g)
    word2=first if c.word2_is_first_record else position-first if 2 in c.payload_size_words else c.word2
    word3=position-first if 3 in c.payload_size_words else c.word3
    head=struct.pack('<5I',c.word0,position,word2,word3,c.word4)+struct.pack('<11I',*offsets)+blocks
    return head+bytes(first-len(head))+b''.join(c.records())+c.trailing


# --- g overlay record -------------------------------------------------------

@dataclass(frozen=True)
class Overlay:
    init_callback: int      # word4, Thumb address inside the primary payload
    process_callback: int   # word5
    prefix: bytes           # bytes between the six header words and the primary payload
    primary: bytes          # copied to the group's execution slot
    secondary: bytes        # copied to the secondary destination (coprocessor program) if any


def parse_overlay(blob: bytes) -> Overlay:
    if len(blob)<24:raise ImageError('overlay record too short')
    w0,w1,w2,w3,w4,w5=struct.unpack_from('<6I',blob,0)
    if w0<24 or w0+w1!=w2 or w2+w3!=len(blob):raise ImageError('overlay word relations do not hold')
    return Overlay(w4,w5,blob[24:w0],blob[w0:w2],blob[w2:])


def build_overlay(o: Overlay) -> bytes:
    w0=24+len(o.prefix);w2=w0+len(o.primary)
    blob=struct.pack('<6I',w0,len(o.primary),w2,len(o.secondary),o.init_callback,o.process_callback)+o.prefix+o.primary+o.secondary
    if len(blob)%4:raise ImageError('overlay record length must be a multiple of four')
    return blob


# --- e catalog descriptor ---------------------------------------------------

@dataclass(frozen=True)
class DescriptorParameter:
    name: str
    minimum_bits: int
    maximum_bits: int
    step_bits: int
    default_bits: int
    storage_index: int
    knob: int
    flags: int
    display_code: int
    lead: int=0xffff      # u16 before the name offset


@dataclass(frozen=True)
class Descriptor:
    public_id: int
    word1: int
    count_word: int       # low byte = parameter count, upper bytes carried verbatim
    name: str
    type_name: str        # equal texts share one pooled string (e.g. Gate: type = name)
    parameters: tuple
    padding: bytes        # ff fill after the strings


def _pool(texts):
    """String pool as the stock tables are laid out: first-use order, equal texts shared.
    latin-1 keeps the few non-ASCII bytes (e.g. CAB '1 x 8' inch mark) exact."""
    pool=b'';offsets={}
    for t in texts:
        if t not in offsets:
            if '\0' in t:raise ImageError('NUL inside string')
            offsets[t]=len(pool);pool+=t.encode('latin-1')+b'\0'
    return pool,[offsets[t] for t in texts]


def parse_descriptor(blob: bytes) -> Descriptor:
    public_id,word1,count_word,name_off,type_off=struct.unpack_from('<IIIHH',blob,0)
    n=count_word&0xff
    if n>8:raise ImageError('too many parameters')
    strings=16+24*n
    params=[];offs=[name_off,type_off]
    for i in range(n):
        lead,off,lo,hi,step,default,alg,knob,flags,code=struct.unpack_from('<HH4I4B',blob,16+24*i)
        params.append((lead,lo,hi,step,default,alg,knob,flags,code));offs.append(off)
    texts=[]
    for off in offs:
        end=blob.find(b'\0',strings+off)
        if end<0:raise ImageError('unterminated string')
        texts.append(blob[strings+off:end].decode('latin-1'))
    pool,expected=_pool(texts)
    if expected!=offs or blob[strings:strings+len(pool)]!=pool:raise ImageError('string pool is not in first-use shared order')
    padding=blob[strings+len(pool):]
    if any(b!=0xff for b in padding):raise ImageError('unexpected bytes after strings')
    return Descriptor(public_id,word1,count_word,texts[0],texts[1],
        tuple(DescriptorParameter(nm,lo,hi,step,default,alg,knob,flags,code,lead) for nm,(lead,lo,hi,step,default,alg,knob,flags,code) in zip(texts[2:],params)),padding)


def build_descriptor(d: Descriptor,padding: bytes|None=None) -> bytes:
    n=len(d.parameters)
    if n>8 or n!=d.count_word&0xff:raise ImageError('parameter count does not match count word')
    pool,offs=_pool([d.name,d.type_name]+[p.name for p in d.parameters])
    blob=struct.pack('<IIIHH',d.public_id,d.word1,d.count_word,offs[0],offs[1])
    for p,off in zip(d.parameters,offs[2:]):
        blob+=struct.pack('<HH4I4B',p.lead,off,p.minimum_bits,p.maximum_bits,p.step_bits,p.default_bits,p.storage_index,p.knob,p.flags,p.display_code)
    return blob+pool+(d.padding if padding is None else padding)


def pad_descriptor(d: Descriptor) -> Descriptor:
    """Recompute ff padding to the next multiple of four (for edited descriptors).
    Stock padding lengths are carried verbatim by parse/build and are not all minimal."""
    bare=len(build_descriptor(d,b''))
    return replace(d,padding=b'\xff'*(-bare%4))
