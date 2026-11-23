"""MOD035 oracle: drawn GR meter on the edit page + 10 Hz admission while shown. No IO."""
import struct
from sdk.telemetry.nds import model as m
from sdk.telemetry.nds.model_gr import *     # noqa: F401,F403
from sdk.telemetry.nds import model_gr as mg
STATE_BYTES=144
FIELDS=mg.FIELDS+['meter','meter_pad']
def state(**kw):
 d=dict.fromkeys(FIELDS,0);d.update(kw);return [d[k] for k in FIELDS]
def service(s,l,now,p=0,c=0,busy=0,result=0):
 s=s.copy();l=l.copy();sent=-1;iv=100 if s[23] else 500
 for a,timeout in [(s,1000),(l,500)]:
  if a[1] and m.delta(now,a[4])>=timeout:a[1]=0;a[3]=1
 if s[1] or l[1] or s[19] and m.delta(now,s[18])<iv or busy or p!=c or p>=12:return s,l,sent
 if s[0] and (not l[0] or s[20]==0):kind=1;a=s
 elif l[0]:kind=0;a=l
 else:return s,l,sent
 sent=kind
 if not result:
  a[0]=0;a[1]=1;a[3]=0;a[4]=now
  if kind:s[7]=1
  else:l[9]=1
  s[18]=now;s[19]=1;s[20]=kind
 return s,l,sent
def meter_value(s,now):
 """(bar tenths 0..200, value text)."""
 if not s[2]:return 0,'--'
 if s[3]:return 0,'ERR'
 if m.delta(now,s[5])>=1000:return 0,'OLD'
 if not s[33]:return 0,'--'
 lb=struct.pack('<9I',*s[24:33])
 if not lb[0] or lb[32]>=11 or not lb[33]&1:return 0,'NONE'
 if not lb[33]&2:return 0,'OFF'
 t=(min(struct.unpack_from('<H',lb,30)[0],6000)+5)//10
 return min(t,200),f'{t//10}.{t%10}'
def editor(s,now,idx,group,ordinal,assign,label=1):
 """Returns (state, events). Events: build, bar=v, text=t, delete, restore."""
 s=s.copy();ev=[]
 if assign:
  if s[34]:ev.append('delete');s[34]=0;s[23]=0
  return s,ev
 if idx<10 and group==1 and ordinal==mg.GR_ORDINAL:
  if not label:return s,ev
  if not s[34]:ev.append('build');s[34]=0x30000000;s[23]=1
  if not s[22] or m.delta(now,s[21])>=100:s[0]=1;s[21]=now;s[22]=1
  v,t=meter_value(s,now);ev+=[f'bar={v}',f'text={t}'];return s,ev
 if s[23]:
  if s[34]:ev.append('delete')
  s[34]=0;s[23]=0;ev.append('restore')
 return s,ev
