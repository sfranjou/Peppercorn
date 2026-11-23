"""Small NDS encoders for independent hook checks; not a general assembler.

Instruction bytes are big-endian even in NDS32:LE. Data words remain LE.
Cross-check every prospective instruction with installed Ghidra assembly and
decode/p-code; do not use these helpers as a complete target implementation.
"""


def jump(site,target,link=False):
    if not isinstance(site,int) or not isinstance(target,int) or (site|target)&1:
        raise ValueError("jump addresses must be even integers")
    delta = (target-site)//2
    if not -(1<<23) <= delta < (1<<23):
        raise ValueError("jump displacement exceeds signed24 halfwords")
    return ((0x49000000 if link else 0x48000000)|(delta&0xffffff)).to_bytes(4,"big")


def gp_add(register,offset):
    if not isinstance(register,int) or not 0 <= register < 32:
        raise ValueError("invalid register index")
    if not isinstance(offset,int) or not -(1<<18) <= offset < (1<<18):
        raise ValueError("GP offset exceeds signed19 bytes")
    return (0x3e080000 | register<<20 | (offset&0x7ffff)).to_bytes(4,"big")
