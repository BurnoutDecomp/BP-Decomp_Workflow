"""Dump DefineFunction2 (DF2) records in a GUIAPT bundle to confirm the arg-table
layout (JeBobs native-8 emitter vs the XB1-authoritative name@+8 stride16).

DF2 header (48B, 8-aligned): name u64@+0, numArgs u32@+8, registers u16@+0xC,
preload u16@+0xE, argtable u64@+0x10, bodyLen u32@+0x18, pad@+0x1C,
sig1 u64@+0x20 (0x...98765432), sig2 u64@+0x28 (0x...12345678), bytecode@+0x30.
We locate records by scanning for the sig1 dword 0x98765432."""
import struct, sys

def rd32(b,o): return struct.unpack_from('<I',b,o)[0]
def rd64(b,o): return struct.unpack_from('<Q',b,o)[0]

path = sys.argv[1]
data = bytearray(open(path,'rb').read())
assert data[:4]==b'bnd2'
n_ent=rd32(data,0x10); ent_off=rd32(data,0x14); d0=rd32(data,0x18)
entries=[]
for e in range(n_ent):
    b=ent_off+0x40*e
    entries.append(dict(base=b, unc=rd32(data,b+0x10), off=rd32(data,b+0x28), typeid=rd32(data,b+0x38)))
apt_e=next(e for e in entries if e['typeid']==0x1E)
res_base=d0+apt_e['off']; res_size=apt_e['unc']&0x0FFFFFFF
h_apt=rd64(data,res_base+0x10); apt_base=res_base+h_apt; apt_size=res_size-h_apt

# scan the apt resource for the DF2 sig1 dword 0x98765432
sig=struct.pack('<I',0x98765432)
pos=apt_base-1; found=0
while found<100000:
    pos=data.find(sig,pos+1,res_base+res_size)
    if pos<0: break
    # sig1 sits at header+0x20 -> header = pos-0x20
    hdr=pos-0x20
    if hdr<apt_base: continue
    # sanity: sig2 at hdr+0x28 should be 0x12345678
    if rd32(data,hdr+0x28)!=0x12345678: continue
    found+=1
    name_off=rd64(data,hdr+0x00)
    nargs=rd32(data,hdr+0x08)
    nregs=rd32(data,hdr+0x0C)&0xFFFF
    argtab=rd64(data,hdr+0x10)   # chunk-relative
    blen=rd32(data,hdr+0x18)
    if nargs==0: continue
    print('DF2 @chunk+%#x  name_off=%#x nargs=%d nregs=%d argtab=%#x blen=%d'%(
        hdr-apt_base, name_off, nargs, nregs, argtab, blen))
    if 0<nargs<=32 and argtab and argtab<apt_size:
        atb=apt_base+argtab
        for i in range(nargs):
            rec=atb+16*i
            raw=bytes(data[rec:rec+16])
            reg=rd32(data,rec)
            at4=rd32(data,rec+4); at8=rd64(data,rec+8)
            # try reading a name string at +4 and +8 (as chunk-relative offsets)
            def strat(off):
                if 0<off<apt_size:
                    p=apt_base+off; s=bytes(data[p:p+16]); s=s.split(b'\0')[0]
                    return s.decode('latin1','replace')
                return None
            print('   arg[%d] raw=%s reg=%d  +4=%#x(%r)  +8=%#x(%r)'%(
                i, raw.hex(), reg, at4, strat(at4), at8, strat(at8)))
