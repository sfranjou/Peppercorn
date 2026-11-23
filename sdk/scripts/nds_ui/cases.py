"""Oracle case generator for the nds_ui feature set (telemetry, home_meter, mem_page, gr_meter,
admission). Ported from scripts/prepare_nds_cpu_pct_cases.py (MOD037) with the same seeds and
order, so the full set equals MOD037's cases.json; tag() assigns each case to the modules
whose code or data it executes, which drives tier-a selection.
Oracles: sdk/telemetry/nds/model*.py (pure Python, no IO besides the admission cost table)."""
import itertools,json,random,struct
from sdk.telemetry.nds.model import valid_fields,raw_text,delta
from sdk.telemetry.nds.model_gr_meter import *
from sdk.telemetry.nds.model_cpu_pct import state,refresh,editor,mdata,FIELDS,est_pct
from sdk.telemetry.nds import admission_costs as AC
import functools
GR_ORDINAL=15
# AC.predict() re-reads six JSON files per call when no table is passed (~200k calls here).
# Memoize in this process only; the oracle file is unchanged and the output hash is pinned
# (tests/test_cases.py: identical to MOD037's cases.json, 00345a01...).
# (admission_costs.table() now caches per table version itself.)

def generate():
 cases=[]
 def add(kind,s=None,l=None,**kw):
  s=state()if s is None else (s+[0]*(37-len(s)));l=[0]*16 if l is None else l;now=kw.get('now',0)
  row=dict(kind=kind,state=s,legacy=l,**kw)
  if kind=='service':
   after,legacy,sent=service(s,l,**kw);row.update(after=after,legacy_after=legacy,sent=sent)
  if kind=='receive':
   b=kw.pop('frame');row['frame']=b.hex();after,release=receive(s,b,**kw);row.update(after=after,release=release)
  if kind=='host':
   after,b=host(s,now);row.update(after=after,serialized=b.hex())
  if kind=='refresh':
   md=kw.pop('md',None) or mdata();row['mdata']=md.hex();row.pop('md',None);after,text=refresh(s,md=md,**kw);row.update(after=after,text=text)
  cases.append(row)
 for req,lreq,last,p,c,busy,result in itertools.product([0,1],[0,1],[0,1],[0,1,11,12,65535],[0,1,11,12,65535],[0,1],[0,1]):
  s=state(requested=req,last_kind=last);l=[0]*16;l[0]=lreq
  add('service',s,l,now=0,p=p,c=c,busy=busy,result=result)
 for tick in [0,99,100,101,499,500]:
  s=state(requested=1,admit_valid=1,admit_tick=0,reserved=1);l=[0]*16
  add('service',s,l,now=tick,p=0,c=0,busy=0,result=0)
 for kind in [0,1]:
  for tick in [0,1,499,500,999,1000,1001,0xffffff00,0xffffffff]:
   for sent in [0,0xfffffff0]:
    s=state(requested=1,admit_valid=1,admit_tick=sent,sent=sent,pending=kind,sentvalid=1);l=[0]*16;l[0]=1;l[1]=1-kind;l[4]=sent;l[9]=1
    add('service',s,l,now=tick,p=0,c=0,busy=0,result=0)
 f=[123,15,173000,200000,26000,30000,17,123,64];LB=lease_block(1,4,166440,{0:(1,0,0),1:(3,2,0),6:(2,0,8),7:(2,0,156)});good=frame(f,LB)
 for valid,pending,timeout,seq,arm in itertools.product([0,1],[0,1],[0,1],[0,0xffffffff],[122,123,124,0x8000007b]):
  s=state(valid=valid,pending=pending,timeout=timeout,rxseq=seq,arm=arm)
  for busy,length,ptr,cmd in [(0,16,1,0x60f0),(1,15,1,0x60f0),(1,16,0,0x60f0),(1,16,1,0x6002),(1,16,1,0x60f0)]:add('receive',s,frame=good,count=84,now=5,busy=busy,length=length,ptr=ptr,cmd=cmd)
 for count in [0,16,44,48,83,85,100]:add('receive',frame=good,count=count,now=0)
 for i in range(1,12):
  b=bytearray(good);b[i]^=1;add('receive',frame=bytes(b),count=84,now=0)
 for flags in range(32):
  for arm in [0,123]:
   for frames in [0,64,128]:
    fields=f.copy();fields[0]=arm;fields[1]=flags;fields[8]=frames;add('receive',frame=frame(fields),count=84,now=0)
 for i in range(9):
  for v in [0,1,0xffffffff,0x80000000]:
   fields=f.copy();fields[i]=v;add('receive',frame=frame(fields),count=84,now=0)
 for fields in [[0]*9,[0,2,0,0,5,6,0,0,0],[0,15,1,2,3,4,0,0,64],[1,9,1,2,0,0,0,0,64]]:add('receive',frame=frame(fields),count=84,now=0)
 for valid,pending,requested,timeout,progress,now,received,mode in itertools.product([0,1],[0,1],[0,1],[0,1],[0,32,64],[0,499,500,999,1000,0xffffffff],[0,0xfffffff0],[0,1,2]):
  s=state(valid=valid,pending=pending,requested=requested,timeout=timeout,progress=progress if valid else 0,received=received,rxseq=0xffffffff,ui_valid=1,ui_tick=0,arm=123,flags=15,arm_last=173000,arm_peak=200000,dsp_last=26000,dsp_peak=30000,dsp_count=17,dsp_block=123,frames=64)
  if not valid:s[8:17]=[0]*9
  if mode==0:add('host',s,now=now)
  add('refresh',s,now=now,mode=mode)
 for flags in [0,1,2,3,9,11,15]:
  for mode in [1,2]:add('refresh',state(valid=1,flags=flags),now=0,mode=mode)
 lrng=random.Random(0x1ea5e)
 blocks=[lease_block(0),LB,lease_block(1,0,0,{}),lease_block(1,9,7680,{6:(2,0,8)}),lease_block(1,1,0,{1:(3,1,0),2:(3,3,0),3:(3,4,0),4:(3,7,0)}),
  lease_block(1,2,0,{g:(2,0,[0,1,9,10,99,100,101,255,163,1,2][g]) for g in range(11)}),lease_block(1,3,0,{5:(1,0,0),8:(0,0,0),10:(2,0,255)})]
 for _ in range(40):blocks.append(lease_block(1,lrng.randrange(65536),lrng.randrange(2**32),{g:(lrng.randrange(4),lrng.randrange(16),lrng.randrange(256)) for g in range(11) if lrng.random()<.4}))
 for blk in blocks:add('receive',frame=frame(f,blk),count=84,now=7)
 for blk in blocks:
  for valid,timeout,now,lv in [(1,0,10,1),(0,0,10,1),(1,1,10,1),(1,0,1500,1),(1,0,10,0)]:
   s=state(valid=valid,timeout=timeout,received=0,ui_valid=1,ui_tick=0,arm=123,flags=15,arm_last=173000,arm_peak=200000,frames=64)
   s[24:33]=list(__import__('struct').unpack('<9I',blk));s[33]=lv
   add('refresh',s,now=now,mode=3)
 for mode in [0,1,2,3]:add('refresh',state(valid=1,flags=15,arm=1,arm_last=5,arm_peak=5,frames=64,ui_valid=1),now=600,mode=mode)
 grng=random.Random(0x6752)
 mblocks=[meter(LB,h,g,fl) for h in (0,4,5,94,95,99,100,199,200,986,999,1000,1999,2000,2100,6000,6001,65535) for g,fl in ((1,3),(1,1),(1,2),(0xff,0),(11,3),(0,3))]
 mblocks+=[meter(lease_block(0),500,1,3)]+[meter(LB,grng.randrange(65536),grng.choice([0,1,6,10,11,0xff]),grng.randrange(256)) for _ in range(60)]
 for blk in mblocks:
  for valid,timeout,now,lv in [(1,0,10,1),(0,0,10,1),(1,1,10,1),(1,0,1500,1),(1,0,10,0)]:
   s=state(valid=valid,timeout=timeout,received=0,ui_valid=1,ui_tick=0,arm=123,flags=15,arm_last=173000,arm_peak=200000,frames=64)
   s[24:33]=list(__import__('struct').unpack('<9I',blk));s[33]=lv
   for idx,group,ordinal,assign,label,shownm in [(0,1,15,0,1,0),(0,1,15,0,1,1),(0,1,15,1,1,0),(0,1,15,1,1,1),(0,1,14,0,1,1),(0,1,14,0,1,0),(0,6,15,0,1,1),(12,1,15,0,1,1),(0,1,15,0,0,0)]:
    s2=s+[0]*(37-len(s));s2[23]=shownm;s2[34]=0x30000000 if shownm else 0
    after,events=editor(s2,now,idx,group,ordinal,assign,label)
    cases.append(dict(kind='editor',state=s2,legacy=[0]*16,now=now,idx=idx,group=group,ordinal=ordinal,assign=assign,label=label,after=after,events=events,mdata=mdata().hex()))
 for blk in mblocks[:20]:add('receive',frame=frame(f,blk),count=84,now=9)
 # MOD036 admission: chains around the threshold, unknown ids, Ping Pong bypass, redraw-on-change.
 tbl=AC.table()[0];arng=random.Random(0xad31)
 def ids_for(choice):
  ids=[0]*10
  for g in range(10):ids[g]=choice.get(g,arng.choice([0,0x03000000,0x07000001,0x0a000001]))
  return ids
 heavy={0:0x1b,1:0x01000021,6:0x04000000,7:0x0b000009,8:0x0c000000}
 mds=[mdata(),mdata(0x3ff,ids_for(heavy)),mdata(0b11000011,ids_for(heavy)),mdata(0b01000011,ids_for(heavy)),mdata(0,ids_for({7:AC.PING_PONG_ID})),mdata(0x80,ids_for({7:AC.PING_PONG_ID})),
  mdata(0b11000010,ids_for({1:0x0100007c,6:0x04000000,7:0x0b000009})),mdata(0x3ff,ids_for({0:0xdeadbeef,1:0xffffffff,6:0x0400007e,7:0x0b0000f4,8:0x12345678})),mdata(0xfffffc00,ids_for(heavy)),mdata(0xffffffff,ids_for(heavy))]
 for _ in range(400):
  ch={g:arng.choice([i for i,_ in tbl[g]]+[arng.randrange(2**32)]) for g in AC.ARM_GROUPS}
  mds.append(mdata(arng.randrange(2**32) if arng.random()<.2 else arng.randrange(1024),ids_for(ch)))
 # exact threshold neighbours: search random chains whose estimate is 949/950/951 or close
 seen=set()
 for _ in range(200000):
  ch={g:arng.choice([i for i,_ in tbl[g]]) for g in AC.ARM_GROUPS};m_=arng.randrange(1024);md=mdata(m_,ids_for(ch));e,_=AC.predict(m_,struct.unpack_from('<10I',md,14))
  if e in (931,940,941,944,945,949,950,951,955,994,995,1004,1005) and e not in seen:seen.add(e);mds.append(md)
 for md in mds:
  e,u=AC.predict(*[struct.unpack_from('<I',md,0)[0],struct.unpack_from('<10I',md,14)])
  for mode in (1,2,3):add('refresh',state(valid=1,flags=15,arm=123,arm_last=173000,arm_peak=200000,frames=64,ui_valid=1),now=10,mode=mode,md=md)
  add('refresh',state(),now=10,mode=1,md=md)
  for raw in (0,1,170000,249131,249132,254376,262244,262245,2622439,2622440,0xffffffff,arng.randrange(2**32)):add('refresh',state(valid=1,flags=15,arm=123,arm_last=raw,arm_peak=raw,frames=64,ui_valid=1),now=10,mode=1,md=md)
  for idx,group,ordinal,assign,label in [(0,1,14,0,1),(0,6,3,0,1),(12,1,15,0,1),(0,1,15,0,1),(0,1,15,1,1),(0,6,3,1,1),(0,6,3,0,0)]:
   pk=est_pct(md)[0]*2|u
   for warn,key,shownm in [(0,0,0),(1,pk,0),(1,pk^2,0),(1,0,0),(0,0,1),(1,pk,1)]:
    s2=state(valid=1,flags=15,arm=123,frames=64,ui_valid=1,warn=warn,warn_key=key);s2[23]=shownm;s2[34]=0x30000000 if shownm else 0
    after,events=editor(s2,10,idx,group,ordinal,assign,label,md=md)
    cases.append(dict(kind='editor',state=s2,legacy=[0]*16,now=10,idx=idx,group=group,ordinal=ordinal,assign=assign,label=label,after=after,events=events,mdata=md.hex()))
 # Tick wrap-around (2026-10-19, C port): the asm compares tick differences unsigned (slti);
 # the GR meter and MEM page had no wrapped-tick cases, so a signed C comparison went unnoticed.
 LB2=meter(LB,250,1,3)
 for now,ui_tick,rx in [(0xffffffff,0,0xfffffffe),(5,0xfffffff0,0xfffffff8),(0,1,0),(99,0xffffffff,5),(1000,0,0xffffffff),(0x80000000,0x7fffffff,0x80000000),(0,0,1),(5,0,100),(10,0,0x80000005)]:
  s=state(valid=1,received=rx,ui_valid=1,ui_tick=ui_tick,arm=123,flags=15,arm_last=173000,arm_peak=200000,frames=64)
  s[24:33]=list(struct.unpack('<9I',LB2));s[33]=1
  add('refresh',s,now=now,mode=3)
  for idx,group,ordinal,assign,label,shownm in [(0,1,15,0,1,1),(0,1,15,0,1,0)]:
   s2=s+[0]*(37-len(s));s2[23]=shownm;s2[34]=0x30000000 if shownm else 0
   after,events=editor(s2,now,idx,group,ordinal,assign,label)
   cases.append(dict(kind='editor',state=s2,legacy=[0]*16,now=now,idx=idx,group=group,ordinal=ordinal,assign=assign,label=label,after=after,events=events,mdata=mdata().hex()))
 # Flag range check isolated (2026-10-19, C port): all other fields zero, so only `flags < 16`
 # decides acceptance (earlier flag sweeps were rejected by field checks first).
 for fl in (16,17,20,24,31,32,0x80000000):
  fields=[0]*9;fields[1]=fl;add('receive',frame=frame(fields),count=84,now=0)
 rng=random.Random(0x60f0);formats=[]
 for raw in [0,1,2622,2623,262243,262244,262245,2622439,2622440,0xffffffff]+[rng.randrange(2**32)for _ in range(100)]:
  for mode in [1,2]:formats.append(dict(mode=mode,raw=raw,text=raw_text(mode,raw)))
 return dict(cases=cases,formats=formats)

def tag(row):
 """Modules whose code/data a case executes (refresh cases enter through mem_page's router)."""
 k=row['kind']
 if k in('enable_gate','select_gate','footswitch_gate'):return {'refuse'}
 if row.get('refuse'):return tag({x:v for x,v in row.items() if x!='refuse'})|{'refuse'}   # editor with a refusal state
 if k in('service','receive','host'):return {'telemetry'}
 if k=='refresh':
  m=row.get('mode',0);t={'mem_page'}
  if m in(0,1,2):t.add('home_meter')
  if m==1:t.add('admission')
  return t
 if k=='editor':
  t={'gr_meter'}
  if not row['assign'] and not(row['idx']<10 and row['group']==1 and row['ordinal']==GR_ORDINAL):t.add('admission')
  return t
 raise ValueError(k)
