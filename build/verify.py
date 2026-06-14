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
import feature_wild
entries=feature_wild.walk_wild(rom)
def label(e): return feature_wild.section_name(rom, feature_wild.region_section(rom,e["bank"],e["map"]))
present=set()
samples={}
for e in entries:
    nm=label(e)
    if not feature_wild.is_preleague(nm): continue
    for cat,_ in feature_wild.CATS:
        c=e["cats"][cat]
        if not c: continue
        for s in c["slots"]:
            sp=rom.u16(s["off"]+2); present.add(sp)
    if nm not in samples:
        g=e["cats"]["grass"]
        if g: samples[nm]=[(gamedata.spname(rom,rom.u16(s["off"]+2)),s["lo"],s["hi"]) for s in g["slots"][:6]]

lines=gamedata.base_lines(rom)
missing=[L["name"] for L in lines if L["idx"] not in present]
print("\n=== wild ===")
print("base lines:",len(lines)," present in pre-league:",sum(1 for L in lines if L["idx"] in present)," missing:",len(missing))
print("missing sample:",missing[:8])
for mp in ["ROUTE 1","ROUTE 2","VIRIDIAN FOREST","ROUTE 10","VICTORY ROAD"]:
    for nm,sl in samples.items():
        if nm.upper().startswith(mp):
            print("  %-16s %s"%(nm,[(n,'L%d-%d'%(lo,hi)) for n,lo,hi in sl]));break
