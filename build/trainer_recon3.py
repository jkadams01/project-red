import romlib, gamedata
rom = romlib.Rom()
TR = rom.tables["data.trainers.stats"]["addr"]
TCN = rom.tables["data.trainers.classes.names"]["addr"]
NT=743; STRIDE=40
def trclass(c): return rom.read_name(TCN + c*13, 13)
def spname(i): return gamedata.spname(rom,i)
ELS={0:8,1:16,2:8,3:16}
def trainer(i):
    o=TR+i*STRIDE
    return dict(idx=i,structType=rom.u8(o),cls=rom.u8(o+1),
        name=rom.read_name(o+4,12),double=rom.u8(o+0x18),
        count=rom.u8(o+0x20),ptr=rom.ptr(o+0x24))
def team_species(t):
    esz=ELS[t["structType"]]; out=[]
    for m in range(t["count"]):
        o=t["ptr"]+m*esz
        out.append((rom.u16(o+2), spname(rom.u16(o+4))))
    return out

# Search for Kanto boss names
BOSSNAMES=["BROCK","MISTY","SURGE","LT.SURGE","ERIKA","KOGA","SABRINA","BLAINE","GIOVANNI",
           "LANCE","LORELEI","BRUNO","AGATHA","BLUE","GARY","TERRY","RIVAL"]
print("=== trainers whose name matches a Kanto boss ===")
for i in range(NT):
    t=trainer(i)
    nm=t["name"].upper().replace(" ","")
    if any(b.replace(" ","") in nm for b in BOSSNAMES) and t["count"]>0:
        ts=team_species(t)
        print("  tr%3d cls=%-11s name=%-10s cnt=%d struct=%d  team=%s"%(
            i,trclass(t["cls"])[:11],t["name"],t["count"],t["structType"],
            [s[1] for s in ts]))

print("\n=== full boss block tr405-445 ===")
for i in range(405,446):
    t=trainer(i)
    if t["count"]==0: continue
    ts=team_species(t)
    lv=None
    if t["ptr"]:
        esz=ELS[t["structType"]]; lv=[rom.u16(t["ptr"]+m*esz+2) for m in range(t["count"])]
    print("  tr%3d cls=%-11s name=%-10s cnt=%d  %s lv=%s"%(
        i,trclass(t["cls"])[:11],t["name"],t["count"],[s[1] for s in ts],lv))
