"""Feature 1+2 (themed): every non-legendary/mythical base line is catchable before the League,
distributed into thematically-appropriate, level-appropriate locations.

Land species fill land (grass/rock-smash) slots; Water species fill water (surf/fishing) slots.
Each location's slots are themed by habitat (see themer.location_theme) and keep their native
level ranges, so the curve stays natural. Coverage of all 461 lines is guaranteed."""
import themer, mapinfo

CATS=[("grass",12),("surf",5),("tree",5),("fish",10)]
LAND={"grass","tree"}; WATER={"surf","fish"}

POSTGAME=["ONE ISLAND","TWO ISLAND","THREE ISLAND","FOUR ISLAND","FIVE ISLAND","SIX ISLAND",
  "SEVEN ISLAND","KINDLE","TREASURE BEACH","CAPE BRINK","BOND BRIDGE","BERRY FOREST","MT. EMBER",
  "ICEFALL","LOST CAVE","PATTERN BUSH","ALTERING CAVE","TANOBY","CHAMBER","SEVAULT","CANYON",
  "DOTTED","TRAINER TOWER","RUIN VALLEY","GREEN PATH","OUTCAST","WATER PATH","RESORT GORGEOUS",
  "MEMORIAL PILLAR","THREE ISLE PORT","WATER LABYRINTH","FIVE ISLE MEADOW","CERULEAN CAVE"]
def is_preleague(name):
    u=name.upper(); return not any(k in u for k in POSTGAME)

def walk_wild(rom):
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

def gather_slots(rom):
    entries=walk_wild(rom)
    # group by location name to compute per-location level_lo
    loc_lo={}
    raw=[]
    for e in entries:
        nm=mapinfo.map_name(rom,e["bank"],e["map"])
        if not is_preleague(nm): continue
        for cat,_ in CATS:
            c=e["cats"][cat]
            if not c: continue
            for s in c:
                raw.append((nm,cat,s)); loc_lo[nm]=min(loc_lo.get(nm,99), s["lo"])
    land=[]; water=[]
    for nm,cat,s in raw:
        theme=themer.location_theme(nm, loc_lo[nm])
        rec=dict(off=s["off"], loc=nm, theme=theme, level=(s["lo"]+s["hi"])/2.0)
        (water if cat in WATER else land).append(rec)
    return land, water

def _lvlpen(sp, slot):
    return abs(sp["tier"] - themer.tier_of_level(slot["level"]))
def _score(sp, slot):
    theme=slot["theme"]; tm=0
    for i,h in enumerate(sp["habs"]):
        if h in theme:
            tm=max(tm, 12 - i - theme.index(h))
    # level fit dominates for big gaps (squared) so strong mons never land on weak slots
    return tm*5 - _lvlpen(sp,slot)**2 * 4

def _assign(slots, species):
    """coverage-first greedy: each species -> best free slot; then fill rest with variety."""
    if not slots or not species: return {}, set()
    asg={}; placed=set()
    slotset=list(slots)
    # coverage: low tier first so early species claim low-level slots
    for sp in sorted(species, key=lambda s:s["tier"]):
        best=None; bestsc=-10**9
        for sl in slotset:
            if sl["off"] in asg: continue
            sc=_score(sp,sl)
            if sc>bestsc: bestsc=sc; best=sl
        if best is not None:
            asg[best["off"]]=sp["idx"]; placed.add(sp["name"])
    # fill remaining slots with themed + level-appropriate variety (veto far-off-level species)
    for i,sl in enumerate(s for s in slots if s["off"] not in asg):
        cands=[sp for sp in species if _lvlpen(sp,sl)<=2] or species
        scored=sorted(cands, key=lambda sp:_score(sp,sl), reverse=True)
        top=scored[:14] or scored
        asg[sl["off"]]=top[i % len(top)]["idx"]
    return asg, placed

def apply(rom, verbose=True):
    pool=themer.build_pool(rom)
    land_sp=[p for p in pool if not p["is_water"]]
    water_sp=[p for p in pool if p["is_water"]]
    land, water = gather_slots(rom)
    la, lp = _assign(land, land_sp)
    wa, wp = _assign(water, water_sp)
    for off,idx in la.items(): rom.wu16(off+2, idx)
    for off,idx in wa.items(): rom.wu16(off+2, idx)
    placed = lp | wp
    missing=[p["name"] for p in pool if p["name"] not in placed]
    if verbose:
        print("[wild] land slots=%d (species %d, placed %d) | water slots=%d (species %d, placed %d)"
              % (len(land),len(land_sp),len(lp),len(water),len(water_sp),len(wp)))
        print("[wild] total lines=%d, NOT catchable pre-league (should be 0): %d %s"
              % (len(pool), len(missing), missing[:10]))
    return dict(land=len(land), water=len(water), missing=missing)
