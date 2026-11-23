"""Offline runner: execute a built overlay payload in the project's Thumb/VFP interpreter.

Uses prototype/pre_cost_interp.PreCPU (the interpreter validated on all stock PRE overlays)
with the group's slot base and the stock call ABI. Pure Python; never touches a device.
Reports instructions executed per call, which is comparable across overlays run the same way.
"""
import json
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'prototype'))
import pre_cost_interp as pi  # noqa: E402
import octa_interp as oi      # noqa: E402

RAM=oi.RAM_BASE
SAMPLES,PARAMS,ENABLE,PERIOD,ARG7,R3PTR=RAM,RAM+0x1000,RAM+0x1100,RAM+0x1104,RAM+0x1108,RAM+0x1180
# Group 4/9 init ABI: r1 = &content pointer (N->S: the selected slot's 2,696-byte record, 0x6f34).
CONTENT_PTR,CONTENT=RAM+0x1110,RAM+0x2000


class _CPU(pi.PreCPU):
    """PreCPU plus caller-supplied memory regions (for diagnostic effects that address the
    coprocessor window or another slot). extra: list of (base, bytearray)."""
    extra=()
    faultmask=0          # Probe v4: set by `cpsid f`, cleared by `cpsie f`

    def _loc(self,addr,size):
        for base,buffer in self.extra:
            o=addr-base
            if 0<=o and o+size<=len(buffer):return buffer,o
        return super()._loc(addr,size)

    # --- Probe v4 fault-safe-read model -------------------------------------------------------
    # With FAULTMASK set and SCB->CCR.BFHFNMIGN (0xe000ed14 bit8) set, a data load from an
    # unmapped address must NOT raise: the hardware would ignore the bus fault, record it in
    # CFSR/BFAR and return an UNKNOWN value. We model that by recording the fault and returning 0.
    # Without both conditions an unmapped access still raises, exactly as before.
    def _bf_armed(self):
        if not self.faultmask:return False
        try:return bool(oi.OctaCPU.r32(self,0xe000ed14)&0x100)
        except oi.Unsupported:return False

    def _bf_record(self,addr):
        try:
            cfsr=oi.OctaCPU.r32(self,0xe000ed28)
            oi.OctaCPU.w32(self,0xe000ed28,cfsr|(1<<9)|(1<<15))   # BFSR.PRECISERR + BFARVALID
            oi.OctaCPU.w32(self,0xe000ed38,addr&0xffffffff)       # BFAR
        except oi.Unsupported:pass

    def w32(self,addr,val):
        # CFSR is write-1-to-clear on real hardware; model it so the probe's status-clear works.
        if addr&0xffffffff==0xe000ed28:
            try:
                old=oi.OctaCPU.r32(self,0xe000ed28)
                oi.OctaCPU.w32(self,0xe000ed28,old&~(val&0xffffffff))
                return
            except oi.Unsupported:pass
        return oi.OctaCPU.w32(self,addr,val)

    def r32(self,addr):
        try:return oi.OctaCPU.r32(self,addr)
        except oi.Unsupported:
            if self._bf_armed():self._bf_record(addr);return 0
            raise

    def r16(self,addr):
        try:return oi.OctaCPU.r16(self,addr)
        except oi.Unsupported:
            if self._bf_armed():self._bf_record(addr);return 0
            raise

    def r8(self,addr):
        try:return oi.OctaCPU.r8(self,addr)
        except oi.Unsupported:
            if self._bf_armed():self._bf_record(addr);return 0
            raise

    def decode(self,addr,itcond=None):
        # Probe v4 system instructions: FAULTMASK control and memory barriers.
        hw0=self.r16(addr)
        if itcond is None and hw0&0xffe0==0xb660 and hw0&1:      # cps{id,ie} f
            im=hw0>>4&1;cpu=self
            def act():cpu.faultmask=1 if im else 0
            return 2,('cpsid f' if im else 'cpsie f'),act
        if itcond is None and hw0&0xffe0==0xb660 and hw0&2:      # cps{id,ie} i (PRIMASK): no-op here
            im=hw0>>4&1
            def act():pass
            return 2,('cpsid i' if im else 'cpsie i'),act
        if itcond is None and hw0==0xf3bf:                       # dsb/dmb/isb barriers: no-op here
            hw2=self.r16(addr+2)
            if hw2&0xff00==0x8f00:
                def act():pass
                return 4,('isb' if hw2&0xf0==0x60 else 'dsb'),act
        # cmp of two registers where one is lr (clang holds the peek address in lr); the base
        # interpreter rejects any high register >= 13. sp/pc (13/15) stay rejected.
        if itcond is None and hw0&0xff00==0x4500:
            rn,rm=(hw0&7)|(hw0>>4&8),hw0>>3&15
            if rn not in (13,15) and rm not in (13,15) and (rn==14 or rm==14):
                R=self.r;cpu=self
                def act():cpu.addc(R[rn],~R[rm]&0xffffffff,1)
                return 2,'cmp r%d, r%d'%(rn,rm),act
        # uxth.w/uxtb.w (unrotated) into any register incl. lr, which clang uses as scratch in the
        # v4 bulk code (the base interpreter's own uxth/uxtb cover only low registers).
        if itcond is None and hw0 in (0xfa1f,0xfa5f):
            hw2=self.r16(addr+2)
            if hw2&0xf0f0==0xf080:
                rd,rm=hw2>>8&15,hw2&15;R=self.r
                if rd not in (13,15) and rm not in (13,15):
                    mask=0xffff if hw0==0xfa1f else 0xff
                    name='uxth.w' if hw0==0xfa1f else 'uxtb.w'
                    def act():R[rd]=R[rm]&mask
                    return 4,'%s r%d, r%d'%(name,rd,rm),act
        return self._decode_v3(addr,itcond)

    def _decode_v3(self,addr,itcond=None):
        # The base interpreter refuses `vmov` between a single register and lr; clang uses lr
        # as a scratch register in leaf code. Same semantics as for r0..r12 (raw 32-bit move).
        hw=self.r16(addr)
        if itcond is None and hw&0xfff0==0xfa50 and (hw&15)!=15:
            # UXTAB Rd, Rn, Rm, ROR #rot (T1); was a local copy in scripts/verify_long_echo.py.
            hw2=self.r16(addr+2)
            if hw2&0xf0c0==0xf080:
                rn,rd,rot,rm=hw&15,(hw2>>8)&15,8*((hw2>>4)&3),hw2&15;R=self.r
                def act():
                    v=R[rm];v=((v>>rot)|(v<<(32-rot)))&0xffffffff if rot else v
                    R[rd]=(R[rn]+(v&255))&0xffffffff
                self._lastcost=(1,0);return 4,'uxtab r%d, r%d, r%d'%(rd,rn,rm),act
        if itcond is None and hw&0xffe0==0xf840:
            # LDR/STR (word) imm8 pre/post-indexed with writeback (T4); was a local copy in
            # scripts/verify_resident_resources.py.
            hw2=self.r16(addr+2)
            if hw2&0x900==0x900 and (hw&15)!=15 and (hw2>>12)!=15 and (hw&15)!=(hw2>>12):
                load=bool(hw&0x10);rn=hw&15;rt=hw2>>12;pre=bool(hw2&0x400);up=bool(hw2&0x200);imm=hw2&255;R=self.r;cpu=self
                def act():
                    new=(R[rn]+(imm if up else -imm))&0xffffffff;a=new if pre else R[rn]
                    if load:R[rt]=cpu.r32(a)
                    else:cpu.w32(a,R[rt])
                    R[rn]=new
                self._lastcost=(2 if load else 1,0)
                return 4,('ldr' if load else 'str')+'.w r%d, [r%d] imm8 wb'%(rt,rn),act
        if itcond is None and hw&0xffd0==0xf380:
            # USAT Rd, #sat, Rn{, LSL/ASR #n} (T1). Q flag not modelled (never read by SDK code).
            hw2=self.r16(addr+2)
            if hw2&0x8020==0:
                rn,rd,sat,R=hw&15,(hw2>>8)&15,hw2&31,self.r
                sh=(hw>>5)&1;n=((hw2>>12)&7)<<2|((hw2>>6)&3)
                if not (sh and n==0):
                    def act():
                        v=R[rn]-(1<<32) if R[rn]&0x80000000 else R[rn]
                        v=v>>n if sh else v<<n
                        R[rd]=min(max(v,0),(1<<sat)-1)&0xffffffff
                    self._lastcost=(1,0);return 4,'usat r%d, #%d, r%d'%(rd,sat,rn),act
        if itcond is None and hw&0xffe0==0xee00:
            hw2=self.r16(addr+2)
            if hw2&0x0f7f==0x0a10 and hw2>>12==14:
                to_core,sn=hw>>4&1,((hw&0xf)<<1)|(hw2>>7&1);R,S=self.r,self.s
                def act():
                    if to_core:R[14]=S[sn]
                    else:S[sn]=R[14]
                return 4,('vmov lr, s%d' if to_core else 'vmov s%d, lr')%sn,act
        # Two integer forms clang emits for the extended probe (Probe v3): zero-extend byte and
        # test against a small immediate. Only the unrotated, in-range shapes are accepted.
        if itcond is None and hw==0xfa5f:
            hw2=self.r16(addr+2)
            if hw2&0xf0f0==0xf080:
                rd,rm=hw2>>8&15,hw2&15;R=self.r
                if max(rd,rm)<15 and rd!=13 and rm!=13:
                    def act():R[rd]=R[rm]&0xff
                    return 4,'uxtb.w r%d, r%d'%(rd,rm),act
        if itcond is None and hw&0xfbf0==0xf010 and hw>>10&1==0:
            hw2=self.r16(addr+2)
            if hw2&0xff00==0x0f00:                      # tst.w rn, #imm8 (imm3 = 0: plain byte, carry unchanged)
                rn,imm=hw&15,hw2&0xff;R=self.r;cpu=self
                if rn<13:
                    def act():
                        res=R[rn]&imm;cpu.n,cpu.z=0,int(res==0)
                    return 4,'tst.w r%d, #%d'%(rn,imm),act
        # Single-register push/pop through the stack pointer (clang saves r8..r11 this way).
        if itcond is None and hw in (0xf84d,0xf85d):
            hw2=self.r16(addr+2);rt=hw2>>12;R=self.r;cpu=self
            if hw==0xf84d and hw2&0x0fff==0x0d04 and rt<13:
                def act():
                    R[13]=(R[13]-4)&0xffffffff;cpu.w32(R[13],R[rt])
                return 4,'str.w r%d, [sp, #-4]!'%rt,act
            if hw==0xf85d and hw2&0x0fff==0x0b04 and rt<13:
                def act():
                    R[rt]=cpu.r32(R[13]);R[13]=(R[13]+4)&0xffffffff
                return 4,'ldr.w r%d, [sp], #4'%rt,act
        return super().decode(addr,itcond)


class OverlayRunner:
    def __init__(self,payload,base,span,init,process,extra=()):
        self.cpu=_CPU(bytes(payload),base,span);self.cpu.extra=tuple(extra)
        self.init_address,self.process_address=init,process
        self.process_steps=[]

    @classmethod
    def from_build(cls,directory,extra=()):
        directory=Path(directory);m=json.loads((directory/'manifest.json').read_text())
        return cls((directory/'payload.bin').read_bytes(),int(m['slot_base'],16),m['slot_bytes'],int(m['init_callback'],16),int(m['process_callback'],16),extra)

    def _set(self,params,period_ms):
        self.cpu.ram[PARAMS-RAM:PARAMS-RAM+32]=struct.pack('<8f',*params)
        struct.pack_into('<I',self.cpu.ram,PERIOD-RAM,period_ms)

    def init(self,params,period_ms=500):
        self._set(params,period_ms);self.cpu.call(self.init_address,(PARAMS,PERIOD))

    def init_content(self,params,content):
        """Group-9 (N->S) init: r1 = &pointer to `content` (bytes), or to a null pointer if None."""
        self._set(params,500)
        if content is not None:
            self.cpu.ram[CONTENT-RAM:CONTENT-RAM+len(content)]=content
        struct.pack_into('<I',self.cpu.ram,CONTENT_PTR-RAM,CONTENT if content is not None else 0)
        self.cpu.call(self.init_address,(PARAMS,CONTENT_PTR))

    def process(self,frames,params,enable=1,period_ms=500):
        """frames: list of (left,right) floats -> list of (left,right) float32 values."""
        n=len(frames);c=self.cpu
        c.ram[0:8*n]=struct.pack(f'<{2*n}f',*[v for f in frames for v in f])
        self._set(params,period_ms);c.ram[ENABLE-RAM]=enable&0xff
        before=c.steps
        c.call(self.process_address,(SAMPLES,n,PARAMS,R3PTR),(ENABLE,PERIOD,ARG7))
        self.process_steps.append(c.steps-before)
        flat=struct.unpack(f'<{2*n}f',bytes(c.ram[0:8*n]))
        return list(zip(flat[0::2],flat[1::2]))

    def run_mono(self,samples,params,block=64,enable=1):
        out=[]
        for i in range(0,len(samples),block):
            out+=[l for l,_ in self.process([(x,x) for x in samples[i:i+block]],params,enable)]
        return out
