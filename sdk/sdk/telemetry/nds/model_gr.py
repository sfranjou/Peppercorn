"""MOD034 oracle: MOD033 lease model + GR page (DRUM mode 4). No device IO."""
import struct
from sdk.telemetry.nds import model as m
from sdk.telemetry.nds.model_lease import *          # noqa: F401,F403 (state, frame, receive, host, service, lease_block, mem_text)
from sdk.telemetry.nds import model_lease as ml
def meter(blk,hold=0,group=0xff,flags=0):
 b=bytearray(blk);struct.pack_into('<H',b,30,hold);b[32]=group;b[33]=flags;return bytes(b)
def gr_text(s,now):
 if not s[2]:return 'GR --'
 if s[3]:return 'GR ERR'
 if m.delta(now,s[5])>=1000:return 'GR OLD'
 if not s[33]:return 'GR --'
 lb=struct.pack('<9I',*s[24:33])
 if not lb[0] or lb[32]>=11 or not lb[33]&1:return 'GR NONE'
 if not lb[33]&2:return 'GR OFF'
 hold=min(struct.unpack_from('<H',lb,30)[0],6000);t=(hold+5)//10;cells=min(10,(hold+100)//200)
 return f'GR {t//10}.{t%10}dB '+'#'*cells+'.'*(10-cells)
def refresh(s,now,mode):
 if mode!=4:return ml.refresh(s,now,mode)
 s=s.copy()
 if not s[22] or m.delta(now,s[21])>=500:s[0]=1;s[21]=now;s[22]=1
 return s,gr_text(s,now)
GR_ORDINAL=15
def editor(s,now,idx,group,ordinal,assign,label=1):
 """Window-4 tick wrapper oracle. Returns (state, text or None, restored)."""
 s=s.copy()
 if assign:return s,None,False
 if idx<10 and group==1 and ordinal==GR_ORDINAL:
  if not s[22] or m.delta(now,s[21])>=500:s[0]=1;s[21]=now;s[22]=1
  t=gr_text(s,now)
  if not label:return s,None,False
  s[23]=1;return s,t,False
 if s[23]:s[23]=0;return s,None,True
 return s,None,False
