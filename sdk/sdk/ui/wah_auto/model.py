"""Heel bypass policy reference. Time is the reviewed millisecond counter."""
from dataclasses import dataclass, asdict
@dataclass
class State:
    active:int=0
    preset:int=0
    timing:int=0
    start:int=0
    owned:int=0
    heel:int=0
    spare0:int=0
    spare1:int=0

def step(s, *, now, preset=13, model=7, option=1, exp_mode=0,
         exp_enabled=1, target=1, parameter=3, low=100, high=4000,
         sample=100, enabled=1):
    """Return None or requested PRE enable state. Explicit manual off stays off."""
    def reset():
        s.active=s.timing=s.owned=s.heel=0
    if model!=7:
        reset();return None
    if s.active and s.preset!=preset:
        reset()
    valid=(option==1 and exp_mode==0 and exp_enabled==1 and target==1 and parameter==3 and high-low>=100)
    if not valid:
        restore=bool(s.active and s.owned and not enabled)
        reset();return 1 if restore else None
    if not s.active:
        s.active=1;s.preset=preset;s.timing=s.heel=0;s.owned=int(not enabled)
    span=high-low
    enter=low+max(1,span//100)
    leave=low+max(2,span//50)
    if sample<=enter:s.heel=1
    elif sample>=leave:s.heel=0
    if not s.heel:
        s.timing=0
        if s.owned:
            s.owned=0
            return 1 if not enabled else None
        return None
    if not enabled:
        if not s.owned:s.timing=0
        return None
    s.owned=0
    if not s.timing:
        s.timing=1;s.start=now
        return None
    if (now-s.start)&0xffffffff>=200:
        s.timing=0;s.owned=1
        return 0
    return None
