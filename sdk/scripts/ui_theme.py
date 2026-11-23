#!/usr/bin/env python3
"""Recolour the GP-50 UI's code-set colours and set the on-screen version text. Offline.

Works on a decoded region-b file of ANY of this project's builds: the edit sites are found
by instruction pattern in stock V1.1.0 (so nothing depends on a hand-kept address list) and
the target build is only accepted if each site still holds either the stock instruction or
a colour load written by an earlier run of this script. Images are not touched.

Two colour roles (analysis/firmware/UI_CUSTOMIZATION.md):
  accent  the bright blue #217DF7 loaded at 46 code sites (text, borders, fills, icon tint)
  main    the dark blue #103963 / #101863 loaded at 13 code sites next to it
Colours are 24-bit hex; the firmware stores RGB565 with its two bytes swapped, and every
site is rewritten to `movi a1, <value>` (4 bytes, same size as what it replaces).

Copyright name: the name after the (c) sign in the About text (one copy per UI language) can
be replaced when the new name fits the NUL padding after each string (USB identity strings
are never touched).

Version text: 7 characters at 0x140f34. A start-up routine reads characters 2, 4 and 6
(the digits) to decide about settings migration, so the text must keep the form X1.1.0Y
with only the first and last characters free.

  ui_theme.py IN_B OUT_B --accent ff69b4 [--main 733152] [--version-text M1.1.0E] [--copyright-name NAME]
  ui_theme.py IN_B --show                      # list sites and their current colours
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent.parent
STOCK_B=ROOT/'work/v110/decoded_b.bin'
STOCK_SHA='f162db977ff009a20b8e1729a9d41451bf9ca9113060f37d8e7285b1c5c36575'
BASE=0x10000
GUI_CODE=(0x1a0a2,0x283a0)          # GUI/Dlg, GuiCommon, GuiMainTask (NDS32_APPLICATION_MAP.md)
VERSION_ADDRESS,VERSION_ROOM=0x140f34,8
STOCK_COLOURS=dict(accent=(0x23fe,),main=(0x11cc,0x10cc))
EXPECTED_SITES=dict(accent=46,main=13)


class ThemeError(ValueError):
    pass


def rgb565(colour):
    colour=colour.lstrip('#')
    if not re.fullmatch('[0-9a-fA-F]{6}',colour):raise ThemeError('colour must be six hex digits, e.g. ff69b4')
    r,g,b=(int(colour[i:i+2],16) for i in (0,2,4))
    return (r>>3)<<11|(g>>2)<<5|b>>3


def to_rgb(value565):
    r,g,b=value565>>11,value565>>5&63,value565&31
    return '#%02x%02x%02x'%(r<<3|r>>2,g<<2|g>>4,b<<3|b>>2)


def swapped(value565):
    return (value565&0xff)<<8|value565>>8


def movi_a1(loaded16):
    """`movi a1, imm` with the 16-bit value in the low bits; the consumers use 16 bits."""
    return bytes((0x44,0x10,loaded16>>8,loaded16&0xff))


def find_sites(stock):
    """{role: [(address, stock 4 bytes)]} from stock region b by instruction pattern:
    `movi a1,<colour>` (44 1f hh ll, sign-extended) or `ori a1,rb,<low 13 bits>` (58 1r xx ll)
    on a register preloaded with the top bits (0x..e000 / 0x..c000). Only inside GUI code."""
    lo,hi=GUI_CODE[0]-BASE,GUI_CODE[1]-BASE;sites={}
    for role,colours in STOCK_COLOURS.items():
        found=[]
        for colour in colours:
            loaded=swapped(colour);high,low=loaded>>8,loaded&0xff
            patterns=[re.escape(bytes((0x44,0x1f,high,low))),
                      b'\\x58[\\x13\\x14\\x15]'+b'['+re.escape(bytes((high&0x1f,)))+re.escape(bytes((high&0x1f|0x80,)))+b']'+re.escape(bytes((low,)))]
            for pattern in patterns:
                for m in re.finditer(pattern,stock[lo:hi]):
                    if (lo+m.start())%2==0:found.append((BASE+lo+m.start(),stock[lo+m.start():lo+m.start()+4]))
        found=sorted(set(found))
        if len(found)!=EXPECTED_SITES[role]:raise ThemeError(f'{role}: found {len(found)} sites in stock, expected {EXPECTED_SITES[role]}')
        sites[role]=found
    if {a for a,_ in sites['accent']}&{a for a,_ in sites['main']}:raise ThemeError('site roles overlap')
    return sites


def stock_sites():
    import hashlib
    stock=STOCK_B.read_bytes()
    if hashlib.sha256(stock).hexdigest()!=STOCK_SHA:raise ThemeError('stock region b changed')
    return find_sites(stock)


def current(data,sites):
    """Colour currently loaded at each site of a target build (stock or previously themed)."""
    out={}
    for role,rows in sites.items():
        values=[]
        for address,stock in rows:
            now=data[address-BASE:address-BASE+4]
            if now==stock:
                # Stock form (movi or ori on a preloaded register): the role's stock colour whose
                # low 13 loaded bits match this instruction.
                values.append(next(c for c in STOCK_COLOURS[role] if swapped(c)&0x1fff==(stock[2]<<8|stock[3])&0x1fff))
            elif now[0]==0x44 and now[1]==0x10:values.append(swapped(now[2]<<8|now[3]))
            else:raise ThemeError(f'{role} site {address:#x} holds {now.hex()}: neither stock nor a themed colour load')
        out[role]=values
    return out


STRINGS=(0xd3b84,0xd7a30)           # UI text tables (NDS32_APPLICATION_MAP.md)


def copyright_sites(data):
    """The About text's copyright line exists once per UI language: `(c)<name>\\n...`.
    Returns [(offset of the name, name bytes, bytes available for a longer name)]."""
    lo,hi=STRINGS[0]-BASE,STRINGS[1]-BASE;found=[]
    for m in re.finditer(rb'\xc2\xa9([A-Za-z0-9 ._-]{1,16})\n',data[lo:hi]):
        start=lo+m.start(1);end=data.index(b'\0',start)           # end of this string
        pad=0
        while data[end+1+pad]==0:pad+=1                           # NUL padding before the next string
        found.append((start,m.group(1),pad))
    if len(found)!=2:raise ThemeError(f'expected the copyright line in two language tables, found {len(found)}')
    return found


def apply(data,accent=None,main=None,version_text=None,copyright_name=None):
    """Return (new bytes, report). Unspecified roles and the version text are left as they are."""
    sites=stock_sites();current(data,sites);out=bytearray(data);report=dict(changed=[])
    for role,colour in (('accent',accent),('main',main)):
        if colour is None:continue
        value=rgb565(colour);new=movi_a1(swapped(value))
        for address,_ in sites[role]:
            o=address-BASE
            if bytes(out[o:o+4])!=new:report['changed'].append(dict(address=hex(address),role=role,old=bytes(out[o:o+4]).hex(),new=new.hex()));out[o:o+4]=new
        report[role]=dict(requested='#'+colour.lstrip('#').lower(),rgb565=f'{value:#06x}',shown_as=to_rgb(value),sites=len(sites[role]))
    if version_text is not None:
        if not re.fullmatch(r'[A-Za-z0-9]1\.1\.0[A-Za-z0-9]?',version_text):
            raise ThemeError('version text must look like X1.1.0Y: only the first and last characters are free')
        o=VERSION_ADDRESS-BASE;old=bytes(out[o:o+VERSION_ROOM])
        if not re.fullmatch(rb'[A-Za-z0-9]1\.1\.0[A-Za-z0-9]?\x00+',old):raise ThemeError('version text area is not as expected')
        new=version_text.encode()+bytes(VERSION_ROOM-len(version_text))
        if new!=old:report['changed'].append(dict(address=hex(VERSION_ADDRESS),role='version text',old=old.hex(),new=new.hex()));out[o:o+VERSION_ROOM]=new
        report['version_text']=version_text
    if copyright_name is not None:
        if not re.fullmatch(r'[A-Za-z0-9 ._-]{1,16}',copyright_name):raise ThemeError('copyright name: 1-16 plain ASCII characters')
        new_name=copyright_name.encode()
        for start,old_name,pad in copyright_sites(bytes(out)):
            growth=len(new_name)-len(old_name)
            if growth>pad:raise ThemeError(f'copyright name too long by {growth-pad} character(s) for the text at {start+BASE:#x}')
            end=out.index(b'\0',start);room=end+1+pad-start         # name .. last padding byte
            old=bytes(out[start:start+room]);new=new_name+old[len(old_name):end-start]
            new=new+bytes(room-len(new))
            if new!=old:report['changed'].append(dict(address=hex(start+BASE),role='copyright name',old=old.hex(),new=new.hex()));out[start:start+room]=new
        report['copyright_name']=copyright_name
    # Nothing outside the listed sites may differ.
    allowed=set()
    for row in report['changed']:allowed.update(range(int(row['address'],16)-BASE,int(row['address'],16)-BASE+len(row['new'])//2))
    if len(out)!=len(data) or any(out[i]!=data[i] for i in range(len(data)) if i not in allowed):raise ThemeError('internal error: unexpected change')
    return bytes(out),report


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path,nargs='?')
    p.add_argument('--accent');p.add_argument('--main');p.add_argument('--version-text');p.add_argument('--copyright-name');p.add_argument('--show',action='store_true')
    a=p.parse_args();data=a.input.read_bytes()
    try:
        sites=stock_sites()
        if a.show or a.output is None:
            now=current(data,sites);o=VERSION_ADDRESS-BASE
            print(json.dumps(dict(version_text=data[o:o+VERSION_ROOM].rstrip(b'\0').decode('latin-1'),copyright_names=[n.decode() for _,n,_ in copyright_sites(data)],
                **{role:dict(sites=len(v),colours=sorted({to_rgb(x) for x in v})) for role,v in now.items()}),indent=1));return 0
        if a.output.exists():p.error('output exists; choose a new file')
        out,report=apply(data,a.accent,a.main,a.version_text,a.copyright_name)
    except ThemeError as exc:
        p.error(str(exc))
    a.output.write_bytes(out);print(json.dumps({k:v for k,v in report.items() if k!='changed'}|dict(bytes_changed_sites=len(report['changed'])),indent=1))
    return 0
if __name__=='__main__':sys.exit(main())
