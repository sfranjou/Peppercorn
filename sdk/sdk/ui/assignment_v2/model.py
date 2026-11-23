"""Volatile per-preset assignments; GUI-independent behavior reference."""
from dataclasses import dataclass,field,asdict
DRUM=0x30602;HOLD=0x40602;BACK=0x30302;PARA=3;PAGE=0x30202
ENCODERS=(0x103,0x203,0x303)
@dataclass
class State:
    phase:int=0;group:int=255;parameter:int=255;destination:int=255
    source_preset:int=13;source_model:int=2;owner:int=13
    maps:list=field(default_factory=lambda:[[0,0,0,0] for _ in range(3)])
def valid(s,dest,preset,models,counts,mode):
    if mode!=1 or not 0<=dest<3 or not s.maps[dest][0]:return None
    if preset!=s.owner:
        for m in s.maps:m[0]=0
        return None
    m=s.maps[dest];_,g,p,model=m
    if not 0<=g<10 or models[g]!=model or not p<counts[g]:m[0]=0;return None
    return g,p

def event(s,msg,*,group=6,page=1,layout=1,delta=1,preset=13,models=None,counts=None):
    models=models or [2]*10;counts=counts or [8]*10
    if msg==HOLD:return bool(s.phase or group<10),None
    if msg==PARA:return bool(s.phase),None
    if msg==PAGE:return False,'page' # Original page action is retained; phase unchanged.
    if msg==BACK:
        if not s.phase:return False,None
        s.phase=0;return True,'restore'
    if msg==DRUM:
        if s.phase==0:
            if group>=10:return False,None
            s.phase=1;s.group=s.parameter=s.destination=255;s.source_preset=preset
        elif s.phase==1:
            if s.parameter==255:return True,None
            s.phase=2
        elif s.phase==2:
            if s.destination==255:return True,None
            if preset!=s.source_preset:s.phase=0;return True,'restore'
            if s.owner!=preset:
                s.owner=preset
                for m in s.maps:m[0]=0
            if models[s.group]!=s.source_model or s.parameter>=counts[s.group]:s.phase=0;return True,'restore'
            s.maps[s.destination]=[1,s.group,s.parameter,s.source_model];s.phase=3
        else:s.phase=0;return True,'restore'
        return True,'render'
    if msg in ENCODERS:
        if not s.phase:return False,None
        if not delta:return True,None
        e=msg>>8
        if s.phase==1:
            p=e-3+page*3-layout
            if page==0:
                if layout or e!=3:return True,None
                p=0
            if group>=10 or not 0<=p<counts[group]:return True,None
            s.group=group;s.parameter=p;s.source_model=models[group];return True,'render'
        if s.phase==2:s.destination=e-1;return True,'render'
        return True,None
    return False,None
