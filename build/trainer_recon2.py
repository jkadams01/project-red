import romlib, gamedata
rom = romlib.Rom()
TR = rom.tables["data.trainers.stats"]["addr"]
TCN = rom.tables["data.trainers.classes.names"]["addr"]
MVN = rom.tables["data.pokemon.moves.names"]["addr"]
NT = 743; STRIDE=40
def trclass(c): return rom.read_name(TCN + c*13, 13)
def spname(i): return gamedata.spname(rom,i)
def movename(i): return rom.read_name(MVN + i*13, 13)

def trainer(i):
    o=TR+i*STRIDE
    return dict(idx=i,off=o,structType=rom.u8(o),cls=rom.u8(o+1),
        name=rom.read_name(o+4,12),double=rom.u8(o+0x18),
        count=rom.u8(o+0x20),ptr=rom.ptr(o+0x24))

ELS={0:8,1:16,2:8,3:16}
def dump_team(t):
    esz=ELS[t["structType"]]; out=[]
    for m in range(t["count"]):
        o=t["ptr"]+m*esz
        iv=rom.u16(o); lvl=rom.u16(o+2); sp=rom.u16(o+4)
        item=None; moves=None
        if t["structType"]==2: item=rom.u16(o+6)
        if t["structType"]==3:
            item=rom.u16(o+6); moves=[rom.u16(o+8+k*2) for k in range(4)]
        if t["structType"]==1:
            moves=[rom.u16(o+6+k*2) for k in range(4)]
        out.append((lvl,spname(sp),sp,item,[movename(x) for x in moves] if moves else None))
    return out

# Dump a structType-3 team to confirm layout
print("=== sample type-3 teams (confirm species/move layout) ===")
shown=0
for i in range(NT):
    t=trainer(i)
    if t["ptr"] and t["structType"]==3 and t["count"]>=3 and shown<3:
        print("tr%d %s '%s' double=%d cnt=%d:"%(i,trclass(t["cls"]),t["name"],t["double"],t["count"]))
        for lvl,nm,sp,item,mv in dump_team(t):
            print("    L%2d %-11s (#%d) item=%s moves=%s"%(lvl,nm,sp,item,mv))
        shown+=1

# Find all trainers with a non-empty name OR boss class
BOSS_CLASSES={23,24,30,81,83,84,87,89,90,2,47,55,56,85}  # leaders/e4/champ/rival/boss/admins
print("\n=== named / boss-class trainers ===")
for i in range(NT):
    t=trainer(i)
    nm=t["name"].strip()
    if (nm and not nm.startswith("?")) or t["cls"] in BOSS_CLASSES:
        if t["count"]==0: continue
        print("  tr%3d cls=%-12s name=%-10s struct=%d cnt=%d"%(
            i, trclass(t["cls"])[:12], t["name"], t["structType"], t["count"]))
