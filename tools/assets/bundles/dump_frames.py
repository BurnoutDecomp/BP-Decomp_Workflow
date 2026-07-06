"""Dump B5MENUITEM frame tables: per movie, per frame, list command tags and
(for tag-1 action commands) the stream pointer. Reuses apt8_fix_frametables parsing."""
import struct, sys

def rd32(b,o): return struct.unpack_from('<I',b,o)[0]
def rd64(b,o): return struct.unpack_from('<Q',b,o)[0]

path = sys.argv[1]
data = bytearray(open(path,'rb').read())
assert data[:4]==b'bnd2'
n_ent=rd32(data,0x10); ent_off=rd32(data,0x14)
data_off=[rd32(data,0x18),rd32(data,0x1C),rd32(data,0x20)]
entries=[]
for e in range(n_ent):
    b=ent_off+0x40*e
    entries.append(dict(base=b,
        unc=[rd32(data,b+0x10+4*k) for k in range(3)],
        off=[rd32(data,b+0x28+4*k) for k in range(3)],
        typeid=rd32(data,b+0x38)))
apt_e=next(e for e in entries if e['typeid']==0x1E)
res_base=data_off[0]+apt_e['off'][0]
res_size=apt_e['unc'][0]&0x0FFFFFFF
h_apt=rd64(data,res_base+0x10)
apt_base=res_base+h_apt
apt_size=res_size-h_apt
def au64(o): return rd64(data,apt_base+o)
def au32(o): return rd32(data,apt_base+o)

# find type-9 root
root=None; pos=apt_base-1; sig4=struct.pack('<I',0x09876543)
while True:
    pos=data.find(sig4,pos+1,res_base+res_size)
    if pos<0: break
    if pos-8>=apt_base and rd64(data,pos-8)==9:
        root=pos-8-apt_base; break
movies=[('root',root)]
cc=au64(root+0x38); ct=au64(root+0x40)
if 0<cc<=1024 and ct and ct<apt_size:
    for i in range(cc):
        v=au64(ct+8*i)
        if not v or v>=apt_size: continue
        if au64(v) in (5,9) and au32(v+8)==0x09876543:
            movies.append(('char[%d]'%i,v))

def cmd_tag_info(cmd):
    if not cmd or cmd>=apt_size: return 'NULL'
    tag=au32(cmd)
    absaligned=(apt_base+cmd)%8==0
    s=''
    if tag==1:  # action: stream at cmd+8 (fixed)
        stream=au64(cmd+8)
        sane = stream>=0x10000 and (stream>>47)==0 and (stream&0xFFFFFFFF)!=0
        s=' stream=%#x %s' % (stream, 'SANE' if sane else 'BAD')
    return 't%d%s%s'%(tag, '' if absaligned else '!misalign', s)

for name,ch in movies:
    fc=au64(ch+0x20); fro=au64(ch+0x28)
    if not (0<fc<=4096 and fro and fro<apt_size): continue
    aligned=(apt_base+fro)%8==0
    print('=== %s @+%#x  frames=%d fro=%#x %s ==='%(name,ch,fc,fro,'ALIGNED' if aligned else 'MISALIGN'))
    for f in range(fc):
        rec=fro+16*f
        cnt=au32(rec); cmds=au64(rec+8)
        tags=[]
        if 0<cnt<=512 and cmds and cmds<apt_size:
            for ci in range(cnt):
                cmd=au64(cmds+8*ci)
                tags.append(cmd_tag_info(cmd))
        # only print frames that have an ACTION (tag1) or are near 0-20
        joined=' '.join(tags)
        if 't1' in joined or f<=20:
            print('  f%-3d cnt=%d  %s'%(f,cnt,joined))
