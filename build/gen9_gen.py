"""Build per-ROM-species REAL Gen-9 legal-move sets from Pokemon Showdown's learnset data and vendor
them (gen9_legal.py), so feature_trainers can filter trainer movesets against TRUE Gen-9 learnsets --
the ROM's own TM/tutor compatibility tables are not Gen-9-accurate (they let Abra "learn" Sand Tomb,
Dual Chop, Charge Beam, etc.).

A species' legal set = the moves in its LATEST-generation Showdown learnset (Gen 9 for SV mons; the most
recent gen otherwise = what it keeps when transferred into Gen 9), matched by name to this ROM's moves,
UNION the ROM's own level-up moves (accurate; immune to name-abbreviation mismatches). Names that can't
be matched are simply dropped -> a mon can never GAIN an illegal move, at worst it loses a rare one.

Run manually:  py gen9_gen.py            (reports matching diagnostics)
               py gen9_gen.py --write    (writes gen9_legal.py)
"""
import json, sys, romlib, gamedata, learnset

SD = "_sd_learnsets.json"

def norm(s): return "".join(c for c in s.lower() if c.isalnum())

# norm(ROM move name) -> Showdown move-id, for ROM names abbreviated past Showdown's 13-char spelling.
MOVE_ALIASES = {
  "hijumpkick": "highjumpkick", "smellingsalt": "smellingsalts", "dolleyes": "babydolleyes",
  "drainkiss": "drainingkiss", "dazzlegleam": "dazzlinggleam", "disarmcry": "disarmingvoice",
  "flowerguard": "flowershield", "petalstorm": "petalblizzard", "mysticfire": "mysticalfire",
  "clangscales": "clangingscales", "darklariat": "darkestlariat", "firstpress": "firstimpression",
  "floralheal": "floralhealing", "hihorsepower": "highhorsepower", "psychicfang": "psychicfangs",
  "sparklearia": "sparklingaria", "spectthief": "spectralthief", "tearylook": "tearfullook",
  "electerrain": "electricterrain", "grassterrain": "grassyterrain", "mistterrain": "mistyterrain",
  "psycterrain": "psychicterrain", "craftyguard": "craftyshield", "aromamist": "aromaticmist",
  "magnetflux": "magneticflux", "trickotreat": "trickortreat", "woodscurse": "forestscurse",
  "breakswipe": "breakingswipe", "expandforce": "expandingforce", "mistyexplode": "mistyexplosion",
  "risingvolt": "risingvoltage", "scorchsands": "scorchingsands", "freezeglare": "freezingglare",
  "jungleheal": "junglehealing", "corrodegas": "corrosivegas", "psyshieldram": "psyshieldbash",
  "thunderkick": "thunderouskick", "naturesmad": "naturesmadness", "reveldance": "revelationdance",
  "lunarbless": "lunarblessing", "mysticpower": "mysticalpower", "1000arrows": "thousandarrows",
  "1000waves": "thousandwaves", "prismlaser": "prismaticlaser", "sunsteelram": "sunsteelstrike",
  "giantblade": "behemothblade", "giantbash": "behemothbash", "dmaxcannon": "dynamaxcannon",
  "clangsoul": "clangoroussoul", "astralstorm": "astralbarrage", "surgestrikes": "surgingstrikes",
  "oneblow": "wickedblow", "bleakicewind": "bleakwindstorm", "wildboltwind": "wildboltstorm",
  "sandsearwind": "sandsearstorm", "springwind": "springtidestorm", "lightoruin": "lightofruin",
  "doubleiron": "doubleironbash", "coreenforce": "coreenforcer", "meteorrush": "meteorassault",
  "falseyield": "falsesurrender",
}
# norm(ROM species name) -> Showdown species-id, for abbreviated names. (Unown forms + Nidoran handled below.)
SPECIES_ALIASES = {
  "fletchindr": "fletchinder", "flabb": "flabebe", "crabminble": "crabominable",
  "blacphalon": "blacephalon", "corvsquire": "corvisquire", "corvknight": "corviknight",
  "baraskewda": "barraskewda", "centskorch": "centiskorch", "poltegeist": "polteageist",
  "stonjorner": "stonjourner", "baculegion": "basculegion", "meowscrada": "meowscarada",
  "squawkbily": "squawkabilly", "kilowatrel": "kilowattrel", "bramblgast": "brambleghast",
  "dudunsprce": "dudunsparce", "brutebonet": "brutebonnet", "flutermane": "fluttermane",
  "slithrwing": "slitherwing", "sandyshock": "sandyshocks", "ironjuglis": "ironjugulis",
  "roarinmoon": "roaringmoon", "ironvalint": "ironvaliant", "walkinwake": "walkingwake",
  "polchgeist": "poltchageist", "fezandipti": "fezandipiti", "gouginfire": "gougingfire",
  "ironbouldr": "ironboulder",
}
SPECIES_BY_INDEX = {29: "nidoranf", 32: "nidoranm"}   # both ROM names normalise to "nidoran"

def showdown_legal(sd):
    """species-id -> set of move-ids learnable in the species' LATEST generation; + the full move universe."""
    legal = {}; universe = set()
    for sp, data in sd.items():
        ls = data.get("learnset", {})
        universe |= set(ls.keys())
        if not ls:
            continue
        maxgen = 0
        for srcs in ls.values():
            for s in srcs:
                if s and s[0].isdigit(): maxgen = max(maxgen, int(s[0]))
        legal[sp] = set(mv for mv, srcs in ls.items()
                        if any(s and s[0].isdigit() and int(s[0]) == maxgen for s in srcs))
    return legal, universe

def main():
    write = "--write" in sys.argv
    sd = json.load(open(SD, encoding="utf-8"))
    sd_legal, sd_universe = showdown_legal(sd)
    sd_species = set(sd.keys())

    rom = romlib.Rom()  # output ROM (move/species names + level-up ids are stable)
    L = learnset.Learnset(rom)
    MVN = rom.tables["data.pokemon.moves.names"]["addr"]

    # ---- match ROM moves -> showdown move-ids ----
    rommove = {}; unmatched_moves = []
    for mid in range(1, 920):
        nm = rom.read_name(MVN + mid*13, 13).strip()
        if not nm or nm.startswith("?"):
            continue
        n = norm(nm)
        sid = MOVE_ALIASES.get(n) or (n if n in sd_universe else None)
        if sid:
            rommove[mid] = sid
        else:
            unmatched_moves.append((mid, nm))

    # ---- match ROM species -> showdown species-ids ----
    romsp = {}; unmatched_sp = []
    for i in gamedata.valid_species(rom):
        nm = gamedata.spname(rom, i)
        if not nm or nm.startswith("?"):
            continue
        n = norm(nm)
        sid = (SPECIES_BY_INDEX.get(i) or SPECIES_ALIASES.get(n)
               or ("unown" if n.startswith("unown") else None) or (n if n in sd_species else None))
        if sid and sid in sd_species:
            romsp[i] = sid
        else:
            unmatched_sp.append((i, nm))

    # validate alias targets actually exist in the Showdown data (catch typos)
    bad = [v for v in MOVE_ALIASES.values() if v not in sd_universe] + \
          [v for v in list(SPECIES_ALIASES.values()) + list(SPECIES_BY_INDEX.values()) if v not in sd_species]
    if bad:
        print("!! ALIAS TARGETS NOT FOUND IN SHOWDOWN DATA:", bad)

    # ---- build per-species legal ROM-move-id sets ----
    LEGAL = {}
    for i, sid in romsp.items():
        sl = sd_legal.get(sid, set())
        ids = set(mid for mid, smv in rommove.items() if smv in sl)
        ids |= set(m for _, m in L.levelup(i))      # union ROM level-up (accurate)
        ids.discard(0)
        if ids:
            LEGAL[i] = sorted(ids)

    # ---- diagnostics ----
    print("ROM moves matched: %d / unmatched: %d" % (len(rommove), len(unmatched_moves)))
    print("unmatched ROM moves:", [nm for _, nm in unmatched_moves])
    print("ROM species matched: %d / unmatched: %d" % (len(romsp), len(unmatched_sp)))
    print("unmatched ROM species (first 40):", [nm for _, nm in unmatched_sp][:40])
    # spot check Abra
    ab = next((i for i in romsp if gamedata.spname(rom, i) == "Abra"), None)
    if ab:
        def mvn(m): return rom.read_name(MVN + m*13, 13).strip()
        print("\nAbra -> showdown '%s', max-gen legal count=%d" % (romsp[ab], len(LEGAL.get(ab, []))))
        print("Abra legal moves:", sorted(mvn(m) for m in LEGAL.get(ab, [])))
        for q in ["Sand Tomb", "Dual Chop", "Charge Beam"]:
            qid = next((m for m in range(920) if norm(mvn(m)) == norm(q)), None)
            print("   %-12s in Abra legal? %s" % (q, qid in LEGAL.get(ab, [])))

    if write:
        with open("gen9_legal.py", "w", encoding="utf-8") as f:
            f.write("# AUTO-GENERATED by gen9_gen.py from Pokemon Showdown Gen-9 learnsets. Do not edit by hand.\n")
            f.write("# species_index -> sorted list of REAL Gen-9-legal move ids (latest-gen learnset + ROM level-up).\n")
            f.write("LEGAL = {\n")
            for i in sorted(LEGAL):
                f.write("  %d: %s,\n" % (i, LEGAL[i]))
            f.write("}\n")
        print("\nwrote gen9_legal.py (%d species)" % len(LEGAL))

if __name__ == "__main__":
    main()
