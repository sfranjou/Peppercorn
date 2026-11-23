"""MOD033 oracle: schema-2 receive with lease cache and the MEM home page.
Extends model.py (unchanged scheduler/host/ARM/DSP semantics). No device IO."""
import struct
from sdk.telemetry.nds import model as m
MASK=m.MASK;STATE_BYTES=136;LEASE_WORDS=10   # 9 lease words + valid flag
FIELDS=m.FIELDS+[f'lease{i}' for i in range(9)]+['lease_valid']
ABBR='NR PREDSTAMPCABEQ MODDLYRVBNS AUX';REASONS='?DFXI'
def state(**kw):
 d=dict.fromkeys(FIELDS,0);d.update(kw);return [d[k] for k in FIELDS]
def lease_block(present=1,transitions=0,total=0,groups=None):
 b=bytearray(36)
 if present:
  b[0]=1;b[1]=11;struct.pack_into('<HI',b,2,transitions&0xffff,total)
  for g,(st,reason,kib) in (groups or {}).items():b[8+2*g]=(st<<4)|reason;b[9+2*g]=kib
 return bytes(b)
def frame(fields,lease=bytes(36),**kw):
 b=bytearray(struct.pack('<BBH',0,84,0x100)+struct.pack('<HHI9I',0x60f0,80,2,*fields)+lease)
 for k,v in kw.items():b[int(k)]=v
 return bytes(b)
def service(s,l,now,**kw):
 a,b,sent=m.service(s[:24],l,now,**kw);return a+s[24:],b,sent
def receive(s,b,count,now,busy=0,length=16,ptr=1,cmd=0x60f0):
 s=s.copy();released=0
 if count!=84 or len(b)<84 or b[1:8]!=bytes([84,0,1,0xf0,0x60,80,0]) or struct.unpack_from('<I',b,8)[0]!=2:return s,released
 f=list(struct.unpack_from('<9I',b,12))
 if not m.valid_fields(f):return s,released
 s[24:33]=list(struct.unpack_from('<9I',b,48));s[33]=1
 diff=m.delta(f[0],s[8]);s[17]=(32 if diff==0 else 64 if diff>=0x80000000 else 0)if s[2] else 0
 s[5]=now;s[8:17]=f;s[6]=m.delta(s[6],-1);s[2]=1
 if s[1] and busy and length>=16 and ptr and cmd==0x60f0:s[1]=s[3]=0;released=1
 return s,released
def host(s,now):
 a,b=m.host(s[:24],now);return a+s[24:],b
def mem_text(s,now):
 if not s[2]:return 'MEM --'
 if s[3]:return 'MEM ERR'
 if m.delta(now,s[5])>=1000:return 'MEM OLD'
 if not s[33]:return 'MEM --'
 lb=struct.pack('<9I',*s[24:33])
 if not lb[0]:return 'MEM NONE'
 out='MEM';n=0
 for g in range(11):
  if n>=3:break
  st=lb[8+2*g]>>4;reason=lb[8+2*g]&15;kib=lb[9+2*g]
  if st not in (2,3):continue
  out+=' '+ABBR[3*g:3*g+3].replace(' ','')
  out+=(f'{kib}K' if st==2 else '!'+REASONS[reason if reason<5 else 0]);n+=1
 return out if n else out+' 0K'
def refresh(s,now,mode):
 if mode!=3:
  a,t=m.refresh(s[:24],now,mode);return a+s[24:],t
 s=s.copy()
 if not s[22] or m.delta(now,s[21])>=500:s[0]=1;s[21]=now;s[22]=1
 return s,mem_text(s,now)
