"""First on-device meter: cached stock ratios, explicitly not admission budgets."""
from dataclasses import dataclass
import struct
MASK=0xffffffff
@dataclass
class State:
    mode:int=0
    poll_valid:int=0
    last_poll:int=0
    reserved:int=0

def ratio_text(mode,bits):
    label='ARM' if mode==1 else 'DSP'
    value=struct.unpack('<f',struct.pack('<I',bits))[0]
    if not 0<=value<float('inf'):return label+'~ERR'
    # Target integer arithmetic computes trunc(value*100) exactly for f32.
    whole=int(value*100)
    if whole>999:return label+'~HIGH'
    return label+f'~{whole//100}.{whole%100:02d}'

def refresh(s,*,now,valid=0,timed_out=0,received_at=0,arm=0,dsp=0):
    if not s.mode:return None,False
    request=not s.poll_valid or ((now-s.last_poll)&MASK)>=500
    if request:s.poll_valid=1;s.last_poll=now
    label='ARM' if s.mode==1 else 'DSP'
    if not valid:return label+' --',bool(request)
    if timed_out:return label+' ERR',bool(request)
    if ((now-received_at)&MASK)>=1000:return label+' OLD',bool(request)
    return ratio_text(s.mode,arm if s.mode==1 else dsp),bool(request)

def event(s,msg):
    if msg==0x30602:s.mode=(s.mode+1)%3;return 'restore' if s.mode==0 else 'refresh'
    if msg==0x40602:return 'consume'
    if msg==0x30302:
        if s.mode:s.mode=0;return 'restore'
        return 'back'
    return 'stock'
