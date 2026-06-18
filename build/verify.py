import romlib, gamedata, feature_bosses
rom = romlib.Rom()   # loads build/project-red.gba (the built output)

print("ROM size:", len(rom.data), "(expect 32718514)")

# ---- Verify bosses ----
TR=rom.tables["data.trainers.stats"]["addr"]; ELS={0:8,1:16,2:8,3:16}
TCN=rom.tables["data.trainers.classes.names"]["addr"]
def trclass(c): return rom.read_name(TCN+c*13,13)
def show_boss(tid,label):
    o=TR+tid*40; st=rom.u8(o); cnt=rom.u8(o+0x20); ptr=rom.ptr(o+0x24); esz=ELS[st]
    mons=[]
    for m in range(cnt):
        mo=ptr+m*esz
        iv=rom.u16(mo); lv=rom.u16(mo+2); sp=rom.u16(mo+4); it=rom.u16(mo+6)
        mons.append("%s L%d%s"%(gamedata.spname(rom,sp),lv,("/itm%d"%it if it else "")))
    ace_sp=rom.u16(ptr+(cnt-1)*esz+4)
    print("  %-10s tr%d %s struct=%d cnt=%d iv=%d ace=%s(#%d,%s)"%(
        label,tid,trclass(rom.u8(o+1)).strip(),st,cnt,rom.u16(ptr),
        gamedata.spname(rom,ace_sp),ace_sp,"GEN1-OK" if ace_sp<=151 else "NOT-GEN1!"))
    print("      "+", ".join(mons))

print("\n=== bosses ===")
for tid,lab in [(414,"Brock"),(415,"Misty"),(416,"Surge"),(417,"Erika"),(418,"Koga"),
                (419,"Blaine"),(420,"Sabrina"),(350,"GiovanniG"),(348,"GiovHide"),
                (410,"Lorelei"),(411,"Bruno"),(412,"Agatha"),(413,"Lance"),
                (438,"Champ-Bls"),(739,"Champ-R")]:
    show_boss(tid,lab)

# ---- Verify wild coverage + level sanity ----
import feature_wild, mapinfo
entries=feature_wild.walk_wild(rom)
def label(e): return mapinfo.map_name(rom, e["bank"], e["map"])
present=set()
samples={}
for e in entries:
    nm=label(e)
    if not feature_wild.is_preleague(nm): continue
    for cat,_ in feature_wild.CATS:
        c=e["cats"][cat]
        if not c: continue
        for s in c:
            sp=rom.u16(s["off"]+2); present.add(sp)
    if nm not in samples:
        g=e["cats"]["grass"]
        if g: samples[nm]=[(gamedata.spname(rom,rom.u16(s["off"]+2)),s["lo"],s["hi"]) for s in g[:6]]

lines=gamedata.base_lines(rom)
missing=[L["name"] for L in lines if L["idx"] not in present]
print("\n=== wild ===")
print("base lines:",len(lines)," present in pre-league:",sum(1 for L in lines if L["idx"] in present)," missing:",len(missing))
print("missing sample:",missing[:8])
for mp in ["ROUTE 1","ROUTE 2","VIRIDIAN FOREST","ROUTE 10","VICTORY ROAD"]:
    for nm,sl in samples.items():
        if nm.upper().startswith(mp):
            print("  %-16s %s"%(nm,[(n,'L%d-%d'%(lo,hi)) for n,lo,hi in sl]));break

# ---- Verify Mega Evolution feature ----
print("\n=== mega evolution ===")
IST=rom.tables["data.items.stats"]["addr"]
def _itn(i): return rom.read_name(IST+i*44,14)
mega_bad=[]
for d in feature_bosses.boss_defs()+feature_bosses.champion_defs():
    if not d.get("mega"): continue
    tid=d["ids"][0]; o=TR+tid*40; st=rom.u8(o); cnt=rom.u8(o+0x20); ptr=rom.ptr(o+0x24); esz=ELS[st]
    has_ring = 353 in [rom.u16(o+0x10+k*2) for k in range(4)]              # trainer-side mega enable
    stones   = [rom.u16(ptr+k*esz+6) for k in range(cnt) if 533<=rom.u16(ptr+k*esz+6)<=579]
    if not (has_ring and len(stones)==1): mega_bad.append((d["name"],has_ring,stones))
print("bosses with Mega Ring(items) + exactly one held stone:",
      sum(1 for d in feature_bosses.boss_defs()+feature_bosses.champion_defs() if d.get("mega"))-len(mega_bad),
      " problems:", mega_bad or "none")
pc=rom.ptr(0xEB6A8); ring_in_pc=any(rom.u16(pc+k*4)==353 for k in range(4))
print("player Mega Ring in new-game PC:", ring_in_pc)
import feature_megastones as _fm
scattered=0
for b in range(43):
    for m in range(_fm.bank_mapcount(rom,b)):
        import mapinfo as _mi
        h=_mi.header(rom,b,m)
        if not h: continue
        ev=rom.ptr(h+4)
        if not ev: continue
        oc=rom.u8(ev); op=rom.ptr(ev+4)
        if not op: continue
        for i in range(oc):
            ob=op+i*0x18
            if rom.u8(ob+1)!=0x5C: continue
            sc=rom.ptr(ob+0x10)
            if sc and rom.u8(sc)==0x1A and rom.u16(sc+1)==0x8000 and 533<=rom.u16(sc+3)<=579: scattered+=1
print("scattered Mega Stone item-balls:", scattered)
assert not mega_bad and ring_in_pc, "MEGA FEATURE VERIFICATION FAILED"
print("mega feature: OK")
