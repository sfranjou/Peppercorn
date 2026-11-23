"""MOD036 oracle: MOD035 + admission warning (ARM page suffix, edit-page strip). No IO.

mdata: 54 bytes from 0x200106c5 (mask u32 LE, 10 order bytes, 10 id u32 LE)."""
import struct
from sdk.telemetry.nds import model_gr_meter as gm
from sdk.telemetry.nds.model_gr_meter import service,receive,host,meter_value  # noqa: F401
from sdk.telemetry.nds import model_gr as mg
from sdk.telemetry.nds import admission_costs as AC
STATE_BYTES=148
FIELDS=gm.FIELDS[:-1]+['warn','warn_key']
W,K=35,36
def state(**kw):
    d=dict.fromkeys(FIELDS,0);d.update(kw);return [d[k] for k in FIELDS]
def mdata(mask=0,ids=(0,)*10):
    return struct.pack('<I',mask)+bytes(range(10))+struct.pack('<10I',*ids)
def estimate(md):
    mask=struct.unpack_from('<I',md,0)[0];ids=struct.unpack_from('<10I',md,14)
    return AC.predict(mask,ids)
def refresh(s,now,mode,md=None):
    after,text=mg.refresh(s,now=now,mode=mode)
    if mode==1 and text is not None:
        est,unk=estimate(md or mdata())
        text+=' EST'+AC.fmt(est)+('!' if est>=AC.WARN else '')+('?' if unk else '')
    return after,text
def editor(s,now,idx,group,ordinal,assign,label=1,md=None):
    """Events: build, bar=v, text=t, delete, restore, warn=TEXT."""
    s=s.copy();ev=[]
    if assign:
        s[W]=0;s[K]=0
        if s[34]:ev.append('delete');s[34]=0;s[23]=0
        return s,ev
    if idx<10 and group==1 and ordinal==mg.GR_ORDINAL:
        if not label:return s,ev
        s[W]=0;s[K]=0
        if not s[34]:ev.append('build');s[34]=0x30000000;s[23]=1
        if not s[22] or mg.m.delta(now,s[21])>=100:s[0]=1;s[21]=now;s[22]=1
        v,t=meter_value(s,now);ev+=[f'bar={v}',f'text={t}'];return s,ev
    if s[23]:
        if s[34]:ev.append('delete')
        s[34]=0;s[23]=0;ev.append('restore')
    if not label:return s,ev
    est,unk=estimate(md or mdata())
    if est<AC.WARN:
        if s[W]:s[W]=0;s[K]=0;ev.append('restore')
        return s,ev
    key=(est*2|unk)&0xffffffff
    if s[W] and s[K]==key:return s,ev
    ev.append('warn=CPU HIGH '+AC.fmt(est)+('?' if unk else ''));s[W]=1;s[K]=key
    return s,ev
