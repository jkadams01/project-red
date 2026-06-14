import romlib, gamedata, mapinfo, feature_wild as fw, json
rom=romlib.Rom()  # built output
entries=fw.walk_wild(rom)
loc={}
for e in entries:
    nm=mapinfo.map_name(rom,e["bank"],e["map"])
    if not fw.is_preleague(nm): continue
    L=loc.setdefault(nm,{"grass":[],"water":[],"lvl":[]})
    for cat,_ in fw.CATS:
        c=e["cats"][cat]
        if not c: continue
        for s in c:
            sp=gamedata.spname(rom,rom.u16(s["off"]+2))
            (L["water"] if cat in fw.WATER else L["grass"]).append((sp,s["lo"],s["hi"]))
            L["lvl"].append(s["lo"])

def uniq(lst):
    seen=[];
    for sp,lo,hi in lst:
        if sp not in [x[0] for x in seen]: seen.append((sp,lo,hi))
    return seen

order=sorted(loc, key=lambda n:min(loc[n]["lvl"]))
summary={}
for nm in order:
    g=uniq(loc[nm]["grass"]); w=uniq(loc[nm]["water"])
    summary[nm]={"grass":[x[0] for x in g],"water":[x[0] for x in w]}
    gl=", ".join("%s"%x[0] for x in g[:14])
    wl=", ".join("%s"%x[0] for x in w[:8])
    lo=min(loc[nm]["lvl"])
    print("\n%-17s (L%d+)" % (nm,lo))
    if gl: print("   GRASS:", gl)
    if wl: print("   WATER:", wl)
json.dump(summary, open("encounters_summary.json","w"), separators=(",",":"))
