"""First UI extension: capture-only assignment preview, no parameter writes/saves.

phase0 stock; phase1 select effect parameter; phase2 select destination encoder;
phase3 preview complete. BACK cancels; actual Stomp mapping is the next milestone.
"""
from dataclasses import dataclass

DRUM=0x30602
DRUM_HOLD=0x40602
BACK=0x30302
ENCODERS=(0x103,0x203,0x303)
PROMPTS={1:'Choose parameter\nTurn knob; DRUM next',2:'Choose Stomp knob\nTurn knob; DRUM next',3:'Preview captured\nBACK: exit',4:'Parameter selected\nDRUM: choose knob',5:'Knob selected\nDRUM: confirm'}
@dataclass
class State:
    phase:int=0
    group:int=255
    parameter:int=255
    destination:int=255

def event(state,message,*,group=6,page=1,layout=0,delta=1,count=8):
    """Return (consumed, presentation). None presentation preserves stock UI."""
    if message==DRUM_HOLD:return bool(state.phase or group<10),None
    if message==BACK:
        if not state.phase:return False,None
        state.phase=0
        return True,'restore'
    if message==DRUM:
        if state.phase==0:
            if group>=10:return False,None
            state.phase=1;state.group=state.parameter=state.destination=255
        elif state.phase==1:
            if state.parameter==255:return True,None
            state.phase=2
        elif state.phase==2:
            if state.destination==255:return True,None
            state.phase=3
        else:
            state.phase=0;return True,'restore'
        return True,PROMPTS[state.phase]
    if message in ENCODERS:
        if not state.phase:return False,None
        encoder=(message>>8)&255
        if not delta:return True,None
        if state.phase==1:
            parameter=encoder-3+page*3-layout
            if page==0:
                if layout!=0 or encoder!=3:return True,None
                parameter=0
            if group>=10 or parameter<0 or parameter>=count:return True,None
            state.group=group;state.parameter=parameter
            return True,PROMPTS[4]
        if state.phase==2:
            state.destination=encoder-1
            return True,PROMPTS[5]
        return True,None
    return False,None
