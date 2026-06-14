"""Build the location inventory + species pool for the themed-encounter design workflow."""
import romlib, mapinfo, gamedata, json

# Post-game / not-yet-reachable locations to EXCLUDE from the pre-League pool.
POSTGAME_KEYS = ["ONE ISLAND","TWO ISLAND","THREE ISLAND","FOUR ISLAND","FIVE ISLAND","SIX ISLAND",
  "SEVEN ISLAND","KINDLE","TREASURE BEACH","CAPE BRINK","BOND BRIDGE","BERRY FOREST","MT. EMBER",
  "ICEFALL","LOST CAVE","PATTERN BUSH","ALTERING CAVE","TANOBY","CHAMBER","SEVAULT","CANYON",
  "DOTTED","TRAINER TOWER","RUIN VALLEY","GREEN PATH","OUTCAST","WATER PATH","RESORT GORGEOUS",
  "MEMORIAL PILLAR","THREE ISLE PORT","WATER LABYRINTH","FIVE ISLE MEADOW","CERULEAN CAVE"]
def is_preleague(name):
    up=name.upper(); return not any(k in up for k in POSTGAME_KEYS)

def categorize(name):
    u=name.upper()
    if "FOREST" in u and "BERRY" not in u: return "FOREST"
    if "POWER PLANT" in u: return "POWER_PLANT"
    if "TOWER" in u: return "GRAVEYARD"
    if "MANSION" in u: return "VOLCANO"
    if "SAFARI" in u: return "SAFARI"
    if "S.S. ANNE" in u or "S.S.ANNE" in u: return "SHIP"
    if "SEAFOAM" in u: return "SEA_CAVE"
    if "MT." in u or "MOON" in u: return "CAVE"
    if "TUNNEL" in u or "DIGLETT" in u: return "CAVE"
    if "VICTORY ROAD" in u: return "CAVE_LATE"
    if "ROUTE" in u: return "ROUTE"
    if any(t in u for t in ["TOWN","CITY","PLATEAU","ISLAND","PALLET"]): return "URBAN"
    return "OTHER"

CATS=[("grass",12),("surf",5),("tree",5),("fish",10)]
def walk(rom):
    WILD=rom.tables["data.pokemon.wild"]["addr"]; a=WILD; out=[]
    while not (rom.u8(a)==0xFF and rom.u8(a+1)==0xFF):
        e=dict(addr=a,bank=rom.u8(a),map=rom.u8(a+1),cats={}); p=a+4
        for nm,ns in CATS:
            ptr=rom.ptr(p); p+=4
            if ptr is None: e["cats"][nm]=None; continue
            lp=rom.ptr(ptr+4); slots=[]
            if lp is not None:
                for s in range(ns): slots.append(dict(off=lp+s*4,lo=rom.u8(lp+s*4),hi=rom.u8(lp+s*4+1)))
            e["cats"][nm]=slots
        out.append(e); a+=20
    return out

# Towns to receive added grass (name, bank, map, level lo/hi by story position)
TOWN_GRASS = [
  ("PALLET TOWN",3,0,2,4),("VIRIDIAN CITY",3,1,3,5),("PEWTER CITY",3,2,4,7),
  ("CERULEAN CITY",3,3,10,14),("VERMILION CITY",3,5,14,18),("LAVENDER TOWN",3,4,16,20),
  ("CELADON CITY",3,6,18,24),("SAFFRON CITY",3,10,24,30),("FUCHSIA CITY",3,7,24,30),
  ("CINNABAR ISLAND",3,8,32,40),
]

def build(rom):
    entries=walk(rom)
    # merge wild entries by section name (so e.g. all Mt Moon floors are one logical location)
    locs={}
    for e in entries:
        nm=mapinfo.map_name(rom,e["bank"],e["map"])
        if not is_preleague(nm): continue
        gslots=e["cats"]["grass"] or []
        wslots=(e["cats"]["surf"] or [])+(e["cats"]["fish"] or [])+(e["cats"]["tree"] or [])
        L=locs.setdefault(nm,dict(name=nm,category=categorize(nm),grass=0,water=0,levels=[]))
        L["grass"]+=len(gslots); L["water"]+=len(wslots)
        for s in gslots+wslots: L["levels"].append((s["lo"],s["hi"]))
    # add town grass locations (grass we will create)
    for nm,b,m,lo,hi in TOWN_GRASS:
        L=locs.setdefault(nm,dict(name=nm,category="URBAN",grass=0,water=0,levels=[]))
        L["grass"]+=12; L["levels"].append((lo,hi))
        L["town_grass_levels"]=(lo,hi)
    # finalize level ranges
    locout=[]
    for nm,L in locs.items():
        if L["levels"]:
            lo=min(a for a,b in L["levels"]); hi=max(b for a,b in L["levels"])
        else: lo=hi=5
        locout.append(dict(name=nm,category=L["category"],grass_slots=L["grass"],
                           water_slots=L["water"],level_lo=lo,level_hi=hi))
    locout.sort(key=lambda d:(d["level_lo"],d["name"]))

    # species pool (461 non-legendary base lines) with types, bst
    lines=gamedata.base_lines(rom)
    water_id=gamedata.water_type_id(rom)
    pool=[]
    for L in lines:
        t1=gamedata.type_name(rom,L["t1"]).strip().title()
        t2=gamedata.type_name(rom,L["t2"]).strip().title()
        pool.append(dict(name=L["name"],type1=t1,type2=(t2 if t2!=t1 else ""),
                         bst=L["bst"],is_water=(L["t1"]==water_id or L["t2"]==water_id)))
    pool.sort(key=lambda d:d["bst"])
    return locout, pool

if __name__=="__main__":
    rom=romlib.Rom()
    locs,pool=build(rom)
    json.dump(locs,open("inv_locations.json","w"),indent=0)
    json.dump(pool,open("inv_pool.json","w"),indent=0)
    print("locations (%d):"%len(locs))
    for d in locs:
        print("  %-18s %-11s grass=%-3d water=%-3d L%d-%d"%(
            d["name"],d["category"],d["grass_slots"],d["water_slots"],d["level_lo"],d["level_hi"]))
    print("pool species:",len(pool),"types sample:",[(p["name"],p["type1"],p["type2"]) for p in pool[:5]])
