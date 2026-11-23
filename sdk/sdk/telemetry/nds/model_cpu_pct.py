"""MOD037 oracle: MOD036 with one safe-side CPU % on the home ARM page and a % edit strip. No IO."""
from sdk.telemetry.nds import model_admission as ma
from sdk.telemetry.nds.model_admission import state,mdata,estimate,service,receive,host,meter_value,FIELDS,STATE_BYTES,W,K  # noqa: F401
from sdk.telemetry.nds import model_gr as mg
WARN_PCT=95
def est_pct(md):
    e,u=estimate(md);return (e+9)//10,u
def meas_pct(raw):
    q,r=divmod(raw,262244)
    return 999 if q>=10 else min(999,q*100+(r*100+262243)//262244)
def refresh(s,now,mode,md=None):
    after,text=mg.refresh(s,now=now,mode=mode)
    if mode==1 and text is not None:
        p,u=est_pct(md or mdata())
        if text.startswith('ARM~'):p=max(p,meas_pct(s[10]))
        text=f'CPU {p}%'+('!' if p>=WARN_PCT else '')+('?' if u else '')
    return after,text
def editor(s,now,idx,group,ordinal,assign,label=1,md=None):
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
    p,u=est_pct(md or mdata())
    if p<WARN_PCT:
        if s[W]:s[W]=0;s[K]=0;ev.append('restore')
        return s,ev
    key=p*2|u
    if s[W] and s[K]==key:return s,ev
    ev.append(f'warn=CPU HIGH {p}%'+('?' if u else ''));s[W]=1;s[K]=key
    return s,ev
