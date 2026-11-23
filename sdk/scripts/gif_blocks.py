"""Minimal GIF89a block parser/splicer (offline). Frames = (GCE bytes, image descriptor+data bytes)."""
import struct
def parse(b):
 assert b[:6]==b'GIF89a';w,h,flags,bg,aspect=struct.unpack_from('<HHBBB',b,6)
 gct=3*(2<<(flags&7)) if flags&0x80 else 0;pos=13+gct;head=b[:pos];frames=[];exts=[];gce=None
 while True:
  t=b[pos]
  if t==0x3b:return dict(head=head,frames=frames,pre=exts,trailer_at=pos,w=w,h=h,gct=b[13:13+gct])
  if t==0x21:
   label=b[pos+1];q=pos+2
   while b[q]:q+=b[q]+1
   blk=b[pos:q+1]
   if label==0xf9:gce=blk
   elif not frames:exts.append(blk)
   else:raise ValueError('extension between frames unsupported: %#x'%label)
   pos=q+1;continue
  if t==0x2c:
   x,y,fw,fh,f=struct.unpack_from('<HHHHB',b,pos+1);q=pos+10+(3*(2<<(f&7)) if f&0x80 else 0)+1
   while b[q]:q+=b[q]+1
   frames.append(dict(gce=gce,img=b[pos:q+1],x=x,y=y,w=fw,h=fh,local=bool(f&0x80),delay=struct.unpack_from('<H',gce,4)[0] if gce else None,disposal=(gce[3]>>2)&7 if gce else None,transp=(gce[3]&1,gce[6]) if gce else None));gce=None;pos=q+1;continue
  raise ValueError('bad block %#x at %d'%(t,pos))
def build(g,frames):
 return g['head']+b''.join(g['pre'])+b''.join((f['gce'] or b'')+f['img'] for f in frames)+b'\x3b'
