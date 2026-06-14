import romlib, gamedata
rom = romlib.Rom()
TR = rom.tables["data.trainers.stats"]["addr"]
TCN = rom.tables["data.trainers.classes.names"]["addr"]
NT = 743
def trclass_name(c): return rom.read_name(TCN + c*13, 13)

# assume stride 40; verify field sanity
STRIDE=40
def trainer(i):
    o=TR+i*STRIDE
    return dict(off=o,
        structType=rom.u8(o+0),
        cls=rom.u8(o+1),
        sprite=rom.u8(o+3),
        name=rom.read_name(o+4,12),
        double=rom.u8(o+0x18),
        count=rom.u8(o+0x20),
        ptr=rom.ptr(o+0x24))

# sanity print first trainers
print("=== first 6 trainers (stride 40) ===")
for i in range(6):
    t=trainer(i)
    print("  %3d struct=%d cls=%-12s name=%-10s cnt=%d ptr=%s" % (
        i, t["structType"], trclass_name(t["cls"])[:12], t["name"], t["count"],
        ("0x%X"%t["ptr"]) if t["ptr"] else None))

# infer tpt element size by structType: collect (structType,count,ptr) and look at contiguous blocks
recs=[]
for i in range(NT):
    t=trainer(i)
    if t["ptr"] and 0<t["count"]<=6 and t["structType"]<=4:
        recs.append((t["ptr"],t["count"],t["structType"],i))
recs.sort()
print("\n=== infer element size from contiguous pointer gaps ===")
from collections import defaultdict
sizes=defaultdict(lambda:defaultdict(int))
for k in range(len(recs)-1):
    p,c,st,i = recs[k]
    p2 = recs[k+1][0]
    gap = p2-p
    if c>0 and gap>0 and gap%c==0 and gap//c<=60:
        sizes[st][gap//c]+=1
for st in sorted(sizes):
    print("  structType %d -> element-size histogram: %s" % (st, dict(sizes[st])))

# Dump raw bytes of a few teams to inspect layout
print("\n=== raw team dumps ===")
shown=0
for i in range(NT):
    t=trainer(i)
    if t["ptr"] and t["count"]>=2 and shown<4:
        # guess element size from histogram majority for its structType
        hist=sizes.get(t["structType"],{})
        esz=max(hist,key=hist.get) if hist else 16
        print("trainer %d (%s '%s') struct=%d cnt=%d elsize≈%d" % (
            i, trclass_name(t["cls"]), t["name"], t["structType"], t["count"], esz))
        for m in range(t["count"]):
            o=t["ptr"]+m*esz
            raw=bytes(rom.data[o:o+esz])
            sp = rom.u16(o+ (esz-2) if False else 0)  # placeholder
            print("   mon%d: %s" % (m, raw.hex()))
        shown+=1
