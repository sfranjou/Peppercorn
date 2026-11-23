import assert from 'node:assert/strict';
import {Pedal} from '../gp50/pedal.mjs';
import {splitMessage,decodePacket,Reassembler} from '../gp50/wire.mjs';
import * as C from '../gp50/components.mjs';
for(const s of [0x75,0x7f,-1,1.5,true]) assert.throws(()=>C.readComponentMessage(s));
assert.deepEqual([...C.writeComponentMessage(0x76,Uint8Array.of(1,2))],[17,118,1,2]);
assert.throws(()=>C.writeComponentMessage(0x76,new Uint8Array(41)));
for(const format of [{},{schema:0,length:5},{schema:1,length:41},{schema:1,length:-1}]) assert.throws(()=>C.validateFormat(format));
class Fake {
 constructor(mode='ok'){this.mode=mode;this.n=0;this.rx=new Reassembler();}
 onReceive(cb){this.cb=cb;}
 send(packet){this.n++;const m=this.rx.feed(decodePacket(packet));if(!m||this.mode==='silence')return;
  const r=this.mode==='reject'?Uint8Array.of(20,8,1):m[0]===17?Uint8Array.of(20,8,0):Uint8Array.of(18,m[1],this.mode==='bad'?2:1,0x78,0x56,0x34,0x12);
  queueMicrotask(()=>splitMessage(r).forEach(p=>this.cb(p)));
 }
}
const id={features:0x100};
{const f=new Fake(),p=new Pedal(f,{gapMs:0,timeoutMs:20});
 await assert.rejects(p.componentStatus({features:0}));
 await assert.rejects(p.readComponent(id,0x76,{schema:1,length:500}));assert.equal(f.n,0);
 const results=await Promise.all([p.componentStatus(id),p.componentStatus(id)]);
 assert.deepEqual(results,[{tick:0x12345678},{tick:0x12345678}]);
 await p.writeComponent(id,0x77,Uint8Array.of(1));assert.equal(f.n,3);
}
for(const mode of ['silence','reject','bad']){const f=new Fake(mode),p=new Pedal(f,{gapMs:0,timeoutMs:20});await assert.rejects(p.componentStatus(id));assert.equal(p.halted,true);const n=f.n;await assert.rejects(p.componentStatus(id));assert.equal(n,f.n);}
{const f=new Fake('reject'),p=new Pedal(f,{gapMs:0,timeoutMs:20});await assert.rejects(p.writeComponent(id,0x76,new Uint8Array()));assert.equal(p.halted,true);}
// fs_block (ABI 3, 0x79)
assert.deepEqual([...C.fsBlockPayload(7)],[7]);assert.deepEqual([...C.fsBlockPayload(0xff)],[255]);
for(const b of [10,-1,1.5,'7',254]) assert.throws(()=>C.fsBlockPayload(b));
assert.deepEqual(C.parseFsBlock(Uint8Array.of(1,7,1)),{block:7,enabled:true});
assert.deepEqual(C.parseFsBlock(Uint8Array.of(1,255,0)),{block:null,enabled:false});
for(const bad of [Uint8Array.of(2,7,1),Uint8Array.of(1,10,0),Uint8Array.of(1,7,2),Uint8Array.of(1,7)]) assert.throws(()=>C.parseFsBlock(bad));
{class FsFake{constructor(){this.sent=[];this.rx=new Reassembler();}onReceive(cb){this.cb=cb;}
  send(packet){const m=this.rx.feed(decodePacket(packet));if(!m)return;this.sent.push([...m]);
   const r=m[0]===17?Uint8Array.of(20,8,0):Uint8Array.of(18,0x79,1,8,1);queueMicrotask(()=>splitMessage(r).forEach(p=>this.cb(p)));}}
 const f=new FsFake(),p=new Pedal(f,{gapMs:0,timeoutMs:20});
 assert.deepEqual(await p.fsBlock(id),{block:8,enabled:true});
 await p.setFsBlock(id,null);await p.setFsBlock(id,3);
 assert.deepEqual(f.sent,[[0x12,0x79],[0x11,0x79,0xff],[0x11,0x79,3]]);
 await assert.rejects(p.setFsBlock(id,12));assert.equal(f.sent.length,3);
}
// cpu_load (ABI 3, 0x7a)
assert.deepEqual(C.parseCpuLoad(Uint8Array.of(1,47,0)),{percent:47});
assert.deepEqual(C.parseCpuLoad(Uint8Array.of(1,0x6b,0)),{percent:107});
assert.deepEqual(C.parseCpuLoad(Uint8Array.of(1,0xff,0xff)),{percent:null});
for(const bad of [Uint8Array.of(2,47,0),Uint8Array.of(1,47)]) assert.throws(()=>C.parseCpuLoad(bad));
{class CpuFake{constructor(){this.sent=[];this.rx=new Reassembler();}onReceive(cb){this.cb=cb;}
  send(packet){const m=this.rx.feed(decodePacket(packet));if(!m)return;this.sent.push([...m]);
   queueMicrotask(()=>splitMessage(Uint8Array.of(18,0x7a,1,52,0)).forEach(p=>this.cb(p)));}}
 const f=new CpuFake(),p=new Pedal(f,{gapMs:0,timeoutMs:20});
 assert.deepEqual(await p.cpuLoad(id),{percent:52});assert.deepEqual(f.sent,[[0x12,0x7a]]);
}
// auto_wah (ABI 3, 0x7b)
assert.deepEqual(C.parseAutoWah(Uint8Array.of(1,1,1,1,0)),{active:true,ownsBypass:true,heel:true,timing:false});
for(const bad of [Uint8Array.of(2,0,0,0,0),Uint8Array.of(1,2,0,0,0),Uint8Array.of(1,0,0,0)]) assert.throws(()=>C.parseAutoWah(bad));
// gr_meter (ABI 3, 0x7c)
assert.deepEqual(C.parseGrMeter(Uint8Array.of(1,0,0x60,1)),{status:'ok',gainReductionDb:3.52});
assert.deepEqual(C.parseGrMeter(Uint8Array.of(1,5,0,0)),{status:'bypassed',gainReductionDb:null});
for(const bad of [Uint8Array.of(1,6,0,0),Uint8Array.of(2,0,0,0),Uint8Array.of(1,0,0)]) assert.throws(()=>C.parseGrMeter(bad));
console.log('component API: bounds/schema/feature guard, tick decode, serialized read/write, refusal/timeout stop passed');
