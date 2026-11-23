"""Independent bounded NDS scheduler/cache/display oracle; no device IO."""
import struct
MASK=0xffffffff
STATE_BYTES=96
FIELDS='requested pending valid timeout sent received rxseq sentvalid arm flags arm_last arm_peak dsp_last dsp_peak dsp_count dsp_block frames progress admit_tick admit_valid last_kind ui_tick ui_valid reserved'.split()
def delta(a,b):return (a-b)&MASK
def state(**kw):
 d=dict.fromkeys(FIELDS,0);d.update(kw);return [d[k] for k in FIELDS]
def valid_fields(f):
 arm,flags,al,ap,dl,dp,dc,db,frames=f
 if flags&~15:return False
 if not flags&1 and (arm or al or ap or frames or flags&8):return False
 if flags&1 and (ap<al or not flags&8):return False
 if not flags&2 and (dl or dp or dc or db):return False
 if flags&2 and dp<dl:return False
 if flags&4 and (flags&3!=3 or db!=arm):return False
 if flags&8 and (not flags&1 or frames!=64):return False
 if not flags&8 and frames:return False
 return True
def frame(fields,**kw):
 b=bytearray(struct.pack('<BBH',0,48,0x100)+struct.pack('<HHI9I',0x60f0,44,1,*fields))
 for k,v in kw.items():b[int(k)]=v
 return bytes(b)
def service(s,l,now,p=0,c=0,busy=0,result=0):
 s=s.copy();l=l.copy();sent=-1
 for a,timeout in [(s,1000),(l,500)]:
  if a[1] and delta(now,a[4])>=timeout:a[1]=0;a[3]=1
 if s[1] or l[1] or s[19] and delta(now,s[18])<500 or busy or p!=c or p>=12:return s,l,sent
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
def receive(s,b,count,now,busy=0,length=16,ptr=1,cmd=0x60f0):
 s=s.copy();released=0
 if count!=48 or len(b)<48 or b[1:8]!=bytes([48,0,1,0xf0,0x60,44,0]) or struct.unpack_from('<I',b,8)[0]!=1:return s,released
 f=list(struct.unpack_from('<9I',b,12))
 if not valid_fields(f):return s,released
 diff=delta(f[0],s[8]);s[17]=(32 if diff==0 else 64 if diff>=0x80000000 else 0)if s[2] else 0
 s[5]=now;s[8:17]=f;s[6]=delta(s[6],-1);s[2]=1
 if s[1] and busy and length>=16 and ptr and cmd==0x60f0:s[1]=s[3]=0;released=1
 return s,released
def host(s,now):
 s=s.copy();status=s[2]|s[1]<<1|s[0]<<2|s[3]<<3
 if s[2]:
  status|=s[17];age=delta(now,s[5]);seq=s[6];f=s[8:17]
  if age>=1000:status|=16
 else:age=MASK;seq=0;f=[0]*9
 b=struct.pack('<4B11I',0x12,0x51,1,status,seq,age,*f);s[0]=1
 return s,b
def raw_text(mode,raw):
 n=raw*100//262244
 return ('ARM'if mode==1 else'DSP')+'~'+('HIGH'if n>=1000 else f'{n//100}.{n%100:02d}')
def refresh(s,now,mode):
 s=s.copy()
 if not mode:return s,None
 if not s[22] or delta(now,s[21])>=500:s[0]=1;s[21]=now;s[22]=1
 label='ARM'if mode==1 else'DSP'
 if not s[2]:return s,label+' --'
 if s[3]:return s,label+' ERR'
 if delta(now,s[5])>=1000:return s,label+' OLD'
 if s[17]:return s,label+' HOLD'
 if not s[9]&1:return s,label+' --'
 if mode==1:
  raw=s[10]
 else:
  if not s[9]&4:return s,label+' IDLE'
  raw=s[12]
 return s,raw_text(mode,raw)
