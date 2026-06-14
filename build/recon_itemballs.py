import romlib, mapinfo
rom=romlib.Rom()
IST=rom.tables["data.items.stats"]["addr"]
def itname(i): return rom.read_name(IST+i*44,14)

def itemballs(b,m):
    h=mapinfo.header(rom,b,m)
    if h is None: return []
    ev=rom.ptr(h+4)
    if not ev: return []
    oc=rom.u8(ev); op=rom.ptr(ev+4); out=[]
    if not op: return []
    for i in range(oc):
        o=op+i*0x18
        if rom.u8(o+1)!=0x5C: continue          # item-ball gfx
        sc=rom.ptr(o+0x10); flag=rom.u16(o+0x14)
        item=None
        if sc and rom.u8(sc)==0x1A and rom.u16(sc+1)==0x8000:   # setorcopyvar VAR_0x8000, item
            item=rom.u16(sc+3)
        out.append(dict(obj=o,x=rom.u16(o+4),y=rom.u16(o+6),script=sc,flag=flag,item=item))
    return out

def bank_mapcount(b):
    BA=mapinfo.banks_addr(rom)
    p0=rom.ptr(BA+b*4); p1=rom.ptr(BA+(b+1)*4)
    if p0 is None: return 0
    if p1 is None or p1<=p0 or (p1-p0)//4>120: return 60   # last/odd bank: cap
    return (p1-p0)//4

NBANKS=43
rows=[]
for b in range(NBANKS):
    for m in range(bank_mapcount(b)):
        if mapinfo.header(rom,b,m) is None: continue
        for ib in itemballs(b,m):
            rows.append((b,m,mapinfo.map_name(rom,b,m),ib))
print("total item balls found:", len(rows))
# group by map
from collections import defaultdict
bymap=defaultdict(list)
for b,m,nm,ib in rows: bymap[(b,m,nm)].append(ib)
for (b,m,nm),lst in sorted(bymap.items(), key=lambda kv:kv[0][2]):
    items=", ".join("%s"%(itname(ib["item"]) if ib["item"] is not None else "?script") for ib in lst)
    print("  %d.%-3d %-22s x%d: %s"%(b,m,nm[:22],len(lst),items))
