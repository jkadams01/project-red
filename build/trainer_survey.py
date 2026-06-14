import romlib, gamedata
rom=romlib.Rom()
TR=rom.tables["data.trainers.stats"]["addr"]
MVN=rom.tables["data.pokemon.moves.names"]["addr"]
MVS=rom.tables["data.pokemon.moves.stats.battle"]["addr"]
TCN=rom.tables["data.trainers.classes.names"]["addr"]
NT=743; ELS={0:8,1:16,2:8,3:16}
def trclass(c): return rom.read_name(TCN+c*13,13)
def movename(i): return rom.read_name(MVN+i*13,13)
def trainer(i):
    o=TR+i*40
    return dict(i=i,st=rom.u8(o),cls=rom.u8(o+1),name=rom.read_name(o+4,12),
        dbl=rom.u8(o+0x18),cnt=rom.u8(o+0x20),ptr=rom.ptr(o+0x24))
def team(t):
    esz=ELS[t["st"]]; out=[]
    if not t["ptr"]: return out
    for m in range(t["cnt"]):
        o=t["ptr"]+m*esz
        out.append((rom.u16(o+2), rom.u16(o+4)))  # (level, species)
    return out

# move-name resolution test + move stats
def move_id(name):
    n=name.upper().replace(" ","").replace("-","")
    for i in range(992):
        if movename(i).upper().replace(" ","").replace("-","")==n: return i
    return None
def move_stats(mid):
    o=MVS+mid*12
    return dict(power=rom.u8(o+1),type=rom.u8(o+2),acc=rom.u8(o+3),cat=rom.u8(o+10))
print("=== move resolution test ===")
for nm in ["Flamethrower","Earthquake","Ice Beam","Thunderbolt","Swords Dance","Dragon Dance",
           "Close Combat","Shadow Ball","Surf","Sludge Bomb","Calm Mind","Toxic","Recover"]:
    mid=move_id(nm)
    print("  %-14s id=%s %s"%(nm,mid,move_stats(mid) if mid else "NOT FOUND"))

# trainer survey
real=0; counts={}; levels=[]; sts={}
for i in range(NT):
    t=trainer(i)
    tm=team(t)
    if not tm: continue
    sps=[s for l,s in tm]
    lvs=[l for l,s in tm]
    if any(s==0 or s>1440 for s in sps): continue
    if any(l<1 or l>100 for l in lvs): continue
    real+=1
    counts[t["cnt"]]=counts.get(t["cnt"],0)+1
    sts[t["st"]]=sts.get(t["st"],0)+1
    levels.append(max(lvs))
print("\n=== trainer survey ===")
print("real trainers (valid teams):",real)
print("party-count distribution:",dict(sorted(counts.items())))
print("structType distribution:",dict(sorted(sts.items())))
import statistics
levels.sort()
print("max-level distribution: min=%d p25=%d median=%d p75=%d max=%d"%(
    levels[0],levels[len(levels)//4],levels[len(levels)//2],levels[3*len(levels)//4],levels[-1]))
# how many would be 'route trainers' (non-boss) by level band
BOSS={348,349,350,410,411,412,413,414,415,416,417,418,419,420,438,439,440,735,736,737,738,739,740,741}
bands={"early<=15":0,"mid16-30":0,"late>30":0}
for i in range(NT):
    if i in BOSS: continue
    t=trainer(i); tm=team(t)
    if not tm: continue
    sps=[s for l,s in tm]; lvs=[l for l,s in tm]
    if any(s==0 or s>1440 for s in sps) or any(l<1 or l>100 for l in lvs): continue
    ml=max(lvs)
    bands["early<=15" if ml<=15 else "mid16-30" if ml<=30 else "late>30"]+=1
print("non-boss route trainers by max-level band:",bands)
