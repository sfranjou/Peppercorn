#!/usr/bin/env python3
"""Read-only GP-50 container verification, using independent table-driven CRC.

Supports the supplied raw V1.0.5 and LZO V1.1.0 layouts. Does not call packer,
load vendor code, open devices, or write firmware. Bounded decode <=4 MiB.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import struct

LZO='/opt/homebrew/Cellar/lzo/2.10/lib/liblzo2.2.dylib'

def require(condition,message):
    if not condition:raise ValueError(message)

def sha(data):return hashlib.sha256(data).hexdigest()

def crc16(data):
    table=[]
    for value in range(256):
        for _ in range(8):value=(value>>1)^(0xa001 if value&1 else 0)
        table.append(value)
    value=0xffff
    for byte in data:value=(value>>8)^table[(value^byte)&255]
    return value

def decode(image):
    require(len(image)>=0x8c and image[:4]==b'HTFW','HTFW container header missing')
    require(image[0x0c:0x1c].split(b'\0',1)[0]==b'GP-50','unexpected model')
    require(image[0x22]==5,'expected five region records')
    require(struct.unpack_from('<I',image,8)[0]==len(image),'file size mismatch')
    require(crc16(image[6:])==struct.unpack_from('>H',image,4)[0],'header CRC mismatch')
    expected=struct.unpack_from('<I',image,0x24)[0]
    require(0<expected<=4*1024*1024,'decoded payload size outside bound')
    compressed=expected+0x88!=len(image)
    if compressed:
        require(struct.unpack_from('<I',image,0x88)[0]==expected,'LZO length prefix mismatch')
        lib=ctypes.CDLL(LZO);fn=lib.lzo1x_decompress_safe
        fn.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong),ctypes.c_void_p]
        fn.restype=ctypes.c_int
        inp=ctypes.create_string_buffer(image[0x8c:]);out=ctypes.create_string_buffer(expected);n=ctypes.c_ulong(expected)
        status=fn(inp,len(image)-0x8c,out,ctypes.byref(n),None)
        require(status==0 and n.value==expected,f'LZO decode failed: {status}/{n.value}')
        payload=out.raw[:n.value]
    else:payload=image[0x88:]
    rows=[];regions=[];cursor=0
    for at in range(0x38,0x88,16):
        checksum=struct.unpack_from('>H',image,at)[0]
        require(image[at+2]==0,'nonzero TOC reserved field')
        rid=chr(image[at+3]);dest,offset,length=struct.unpack_from('<III',image,at+4)
        require(offset==cursor and 0<length<=expected-cursor,'TOC region gap/overlap/bounds')
        data=payload[offset:offset+length]
        require(crc16(data)==checksum,f'{rid} region CRC mismatch')
        rows.append(dict(id=rid,destination=hex(dest),offset=offset,size=length,crc16=hex(checksum),sha256=sha(data)))
        regions.append((rid,dest,data));cursor+=length
    require([rid for rid,_,_ in regions]==list('cgfbe') and cursor==expected,'region order/payload end mismatch')
    report=dict(size=len(image),sha256=sha(image),compressed=compressed,decoded_size=expected,
                header_crc_ok=True,file_size_ok=True,all_region_crcs_ok=True,regions=rows)
    return regions,report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('image',type=Path)
    args=parser.parse_args();_,report=decode(args.image.read_bytes());print(json.dumps(report,indent=2))
if __name__=='__main__':main()
