"""Themed wild-encounter designer: classify each base line into Kanto habitats, theme each
pre-League location, and assign species to slots with full coverage + level matching."""
import gamedata

HABS = ["GRASSLAND","FOREST","CAVE","MOUNTAIN","WATER","URBAN","POWER_PLANT",
        "GRAVEYARD","VOLCANO","SAFARI","RARE","ICE"]

def _ty(s):  # normalize ROM truncated type names
    s=s.lower()
    if s.startswith("electr"): return "electric"
    if s.startswith("psych"): return "psychic"
    if s.startswith("fight"): return "fighting"
    return s

# primary type -> ordered habitat affinities
TYPE_HAB = {
 "bug":      ["FOREST","SAFARI"],
 "grass":    ["FOREST","GRASSLAND"],
 "water":    ["WATER"],
 "rock":     ["CAVE","MOUNTAIN"],
 "ground":   ["CAVE","GRASSLAND"],
 "electric": ["POWER_PLANT","GRASSLAND"],   # rodents on routes; machines at the plant (not cities)
 "ghost":    ["GRAVEYARD"],
 "poison":   ["GRAVEYARD","CAVE","URBAN"],
 "fire":     ["VOLCANO"],
 "normal":   ["GRASSLAND","URBAN"],
 "flying":   ["GRASSLAND","MOUNTAIN"],
 "fighting": ["CAVE","SAFARI","URBAN"],
 "psychic":  ["URBAN","SAFARI"],
 "dark":     ["GRAVEYARD","URBAN","SAFARI"],
 "steel":    ["POWER_PLANT"],               # rely on secondary type for non-industrial steels
 "ice":      ["ICE"],                       # cold mons concentrate in Seafoam, not temperate caves
 "dragon":   ["RARE","CAVE"],
 "fairy":    ["GRASSLAND","URBAN"],
}

# Iconic / hand-tuned overrides (name -> habitats, prepended). Kanto-flavour placements.
OVERRIDE = {
 "Pikachu":["FOREST","POWER_PLANT"],"Pichu":["FOREST","POWER_PLANT"],
 "Gastly":["GRAVEYARD"],"Haunter":["GRAVEYARD"],"Cubone":["GRAVEYARD","CAVE"],
 "Eevee":["URBAN"],"Meowth":["URBAN"],"Rattata":["URBAN","GRASSLAND"],
 "Abra":["URBAN","SAFARI"],"Drowzee":["URBAN"],"Mr. Mime":["URBAN"],"Mime Jr.":["URBAN"],
 "Scyther":["SAFARI","FOREST"],"Pinsir":["SAFARI","FOREST"],"Heracross":["SAFARI","FOREST"],
 "Kangaskhan":["SAFARI"],"Tauros":["SAFARI","GRASSLAND"],"Miltank":["SAFARI","GRASSLAND"],
 "Happiny":["SAFARI"],"Chansey":["SAFARI"],"Nidoran?":["SAFARI","GRASSLAND"],
 "Dratini":["SAFARI","RARE"],"Magnemite":["POWER_PLANT","URBAN"],"Voltorb":["POWER_PLANT"],
 "Elekid":["POWER_PLANT"],"Magby":["VOLCANO"],"Magikarp":["WATER"],
 "Geodude":["CAVE"],"Onix":["CAVE"],"Machop":["CAVE","SAFARI"],"Zubat":["CAVE"],
 "Paras":["CAVE","FOREST"],"Diglett":["CAVE"],"Larvitar":["RARE","CAVE"],
 "Bagon":["RARE","CAVE"],"Beldum":["RARE","POWER_PLANT"],"Gible":["RARE","CAVE"],
 "Deino":["RARE","CAVE"],"Goomy":["RARE"],"Jangmo-o":["RARE","CAVE"],"Frigibax":["RARE","ICE"],
 "Axew":["RARE","CAVE"],"Snorlax":["GRASSLAND"],"Munchlax":["GRASSLAND"],
 "Vulpix":["VOLCANO"],"Growlithe":["VOLCANO","URBAN"],"Ponyta":["VOLCANO","GRASSLAND"],
 "Oddish":["FOREST","GRASSLAND"],"Bellsprout":["FOREST","GRASSLAND"],"Caterpie":["FOREST"],
 "Weedle":["FOREST"],"Pidgey":["GRASSLAND","FOREST"],"Spearow":["GRASSLAND","MOUNTAIN"],
 "Ekans":["GRASSLAND","SAFARI"],"Sandshrew":["CAVE","GRASSLAND"],"Mankey":["CAVE","SAFARI"],
 "Tangela":["SAFARI","FOREST"],"Lickitung":["SAFARI"],"Lapras":["WATER","ICE"],
 "Porygon":["POWER_PLANT","URBAN"],"Ditto":["URBAN","CAVE"],"Aerodactyl":["RARE","CAVE"],
 "Omanyte":["CAVE","WATER"],"Kabuto":["CAVE","WATER"],"Klefki":["URBAN"],
 "Skarmory":["MOUNTAIN","GRASSLAND"],"Carnivine":["SAFARI","FOREST"],
 "Pikachu":["FOREST","POWER_PLANT","GRASSLAND"],
}

def habitats(name, t1, t2, bst, is_water):
    if name in OVERRIDE:
        h = list(OVERRIDE[name])
    else:
        h = []
        for t in (t1,t2):
            if not t: continue
            for hab in TYPE_HAB.get(_ty(t),[]):
                if hab not in h: h.append(hab)
    # pseudo / very strong -> also RARE (late game)
    if bst >= 525 and "RARE" not in h: h.append("RARE")
    if is_water and "WATER" not in h: h.insert(0,"WATER")
    if not h: h=["GRASSLAND"]
    return h

# Location -> ordered habitat theme. Matched by substring on the location name.
def location_theme(name, level_lo):
    u=name.upper()
    if "VIRIDIAN FOREST" in u: return ["FOREST"]
    if "POWER PLANT" in u: return ["POWER_PLANT"]
    if "TOWER" in u: return ["GRAVEYARD"]
    if "MANSION" in u: return ["VOLCANO"]
    if "SAFARI" in u: return ["SAFARI","RARE","GRASSLAND","FOREST"]   # rare wild game incl. pseudos
    if "SEAFOAM" in u: return ["WATER","ICE","CAVE"]
    if "CINNABAR" in u: return ["VOLCANO","URBAN"]   # volcano island
    if "S.S. ANNE" in u or "S.S.ANNE" in u: return ["WATER","URBAN"]
    if "FUCHSIA" in u: return ["GRASSLAND","FOREST","URBAN"]          # Safari-gate nature flavour
    if "DIGLETT" in u: return ["CAVE"]
    if "VICTORY ROAD" in u: return ["RARE","CAVE","MOUNTAIN"]
    if "ROUTE 23" in u: return ["RARE","CAVE","GRASSLAND"]            # league approach: strong mons
    if "MT." in u or "MOON" in u or "TUNNEL" in u: return ["CAVE"]
    if any(t in u for t in ["TOWN","CITY","PLATEAU","PALLET"]) or "ISLAND" in u:
        return ["URBAN","GRASSLAND"]
    if "ROUTE" in u:
        return ["GRASSLAND","FOREST"]
    return ["GRASSLAND"]

def tier_of_bst(bst):
    # rough difficulty tier 0..5
    return min(5, max(0, (bst-180)//70))
def tier_of_level(lvl):
    return min(5, max(0, (lvl-2)//9))

def build_pool(rom):
    lines=gamedata.base_lines(rom); wid=gamedata.water_type_id(rom)
    pool=[]
    for L in lines:
        t1=gamedata.type_name(rom,L["t1"]).strip()
        t2=gamedata.type_name(rom,L["t2"]).strip()
        isw=(L["t1"]==wid or L["t2"]==wid)
        habs=habitats(L["name"],t1,t2,L["bst"],isw)
        pool.append(dict(idx=L["idx"],name=L["name"],bst=L["bst"],is_water=isw,
                         tier=tier_of_bst(L["bst"]),habs=habs))
    return pool
