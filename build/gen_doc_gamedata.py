"""Generate docs/GAME_DATA.md from the BUILT ROM: wild encounters (species/levels/odds) per location,
plus every boss and every regular trainer with full teams + movesets. Run after `py build.py`."""
import os, romlib, gamedata, mapinfo, learnset
import feature_bosses as fb
import feature_wild as fw
import feature_evofix

BASE_ROM = r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba"

rom = romlib.Rom()
MVN = rom.tables["data.pokemon.moves.names"]["addr"]
IST = rom.tables["data.items.stats"]["addr"]
TR  = rom.tables["data.trainers.stats"]["addr"]
CLS = rom.tables["data.trainers.classes.names"]["addr"]
L = learnset.Learnset(rom)
TR_STRIDE = 40
ELS = {0: 8, 1: 16, 2: 8, 3: 16}

def mvname(m): return rom.read_name(MVN + m*13, 13).strip() if m else ""
def itemname(i): return rom.read_name(IST + i*44, 14).strip() if i else ""
def clsname(c): return rom.read_name(CLS + c*13, 13).strip()
def spname(s): return gamedata.spname(rom, s)

# ---- WILD ENCOUNTERS -------------------------------------------------------
# Standard FRLG per-slot encounter rates.
GRASS = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]   # 12 slots
SURF  = [60, 30, 5, 4, 1]                              # 5 slots
ROCK  = [60, 30, 5, 4, 1]                              # 5 slots (rock smash)
FISH_RODS = [("Old Rod", 0, [70, 30]), ("Good Rod", 2, [60, 20, 20]),
             ("Super Rod", 5, [40, 40, 15, 4, 1])]     # 10 fishing slots split across 3 rods

def aggregate(slots, rates):
    """Combine identical species across a category's slots -> [(name, lo, hi, pct)] sorted by pct desc."""
    d = {}
    for s, rate in zip(slots, rates):
        sp = rom.u16(s["off"] + 2)
        if sp == 0:
            continue
        e = d.get(sp)
        if e:
            e[0] = min(e[0], s["lo"]); e[1] = max(e[1], s["hi"]); e[2] += rate
        else:
            d[sp] = [s["lo"], s["hi"], rate]
    return sorted(([spname(k), v[0], v[1], v[2]] for k, v in d.items()), key=lambda r: -r[3])

def lvltext(lo, hi):
    return "L%d" % lo if lo == hi else "L%d-%d" % (lo, hi)

def enc_table(rows):
    out = ["| Pokemon | Levels | Odds |", "|---|---|---|"]
    for nm, lo, hi, pct in rows:
        out.append("| %s | %s | %d%% |" % (nm, lvltext(lo, hi), pct))
    return "\n".join(out)

def wild_section():
    entries = fw.walk_wild(rom)
    # order by lowest level present, like dump_encounters
    def minlvl(e):
        m = 99
        for c in e["cats"].values():
            if c:
                m = min(m, min(s["lo"] for s in c))
        return m
    entries.sort(key=minlvl)
    seen = {}
    out = ["# Wild Encounters\n",
           "Every location where wild Pokemon can be caught, with level ranges and per-encounter odds.",
           "Odds are the standard FireRed slot rates (Grass 20/20/10.../1, Surf & Rock Smash 60/30/5/4/1,",
           "Fishing split across Old/Good/Super Rod). Within a method, a species appearing in several",
           "slots has its odds summed.\n"]
    for e in entries:
        nm = mapinfo.map_name(rom, e["bank"], e["map"]) or "MAP %d-%d" % (e["bank"], e["map"])
        seen[nm] = seen.get(nm, 0) + 1
        title = nm if seen[nm] == 1 else "%s (area %d)" % (nm, seen[nm])
        blocks = []
        for cat, rates, label in [("grass", GRASS, "Walking (grass/cave)"),
                                  ("surf", SURF, "Surfing"),
                                  ("tree", ROCK, "Rock Smash")]:
            c = e["cats"].get(cat)
            if c:
                rows = aggregate(c, rates)
                if rows:
                    blocks.append("**%s**\n\n%s" % (label, enc_table(rows)))
        fc = e["cats"].get("fish")
        if fc:
            fblocks = []
            for rodname, start, rrates in FISH_RODS:
                rods = fc[start:start + len(rrates)]
                rows = aggregate(rods, rrates)
                if rows:
                    fblocks.append("*%s*\n\n%s" % (rodname, enc_table(rows)))
            if fblocks:
                blocks.append("**Fishing**\n\n" + "\n\n".join(fblocks))
        if blocks:
            out.append("\n## %s\n" % title)
            out.append("\n\n".join(blocks))
    return "\n".join(out)

# ---- EVOLUTION CHANGES -----------------------------------------------------
def evo_changes_section():
    """List trade evolutions that were converted to solo (level-up / item) evolutions.
    Derived by reading the pristine base's evolution table via feature_evofix.plan()."""
    base = romlib.Rom(BASE_ROM)
    convs = feature_evofix.plan(base)
    lv = sorted(set((s, t) for s, t, k, d in convs if k == "level"))
    it = sorted(set((s, t, d) for s, t, k, d in convs if k == "item"))
    out = ["# Evolution Changes\n",
           "Trade-based evolutions can't be done in single-player, so every one has been replaced with a",
           "solo-achievable evolution. Nothing else about the evolution lines changed (same final forms).\n",
           "**Former trade evolutions — now evolve by levelling up (Lv%d):**\n" % feature_evofix.LEVEL_FOR_TRADE,
           "| Pokemon | Evolves into | Now |", "|---|---|---|"]
    for s, t in lv:
        out.append("| %s | %s | Level %d |" % (s, t, feature_evofix.LEVEL_FOR_TRADE))
    out += ["\n**Former trade-with-item evolutions — now evolve by USING that item** "
            "(all sold at the Celadon evolution-item shop):\n",
            "| Pokemon | Evolves into | Use item |", "|---|---|---|"]
    for s, t, item in it:
        out.append("| %s | %s | %s |" % (s, t, item))
    return "\n".join(out)

# ---- TRAINERS --------------------------------------------------------------
def read_team(o):
    st = rom.u8(o); cnt = rom.u8(o + 0x20); ptr = rom.ptr(o + 0x24)
    if not ptr or cnt == 0 or cnt > 6:
        return st, []
    esz = ELS.get(st, 8); team = []
    for k in range(cnt):
        mo = ptr + k * esz
        lvl = rom.u16(mo + 2); species = rom.u16(mo + 4)
        if species == 0 or species > 1440:
            continue
        item = 0; moves = []
        if st in (2, 3):
            item = rom.u16(mo + 6)
        if st == 3:
            moves = [rom.u16(mo + 8 + j*2) for j in range(4)]
        elif st == 1:
            moves = [rom.u16(mo + 6 + j*2) for j in range(4)]
        else:                                  # st 0/2: game auto-generates level-up moves
            moves = L.fallback_moves(species, lvl)[:4]
        team.append(dict(lvl=lvl, sp=species, item=item,
                         moves=[mvname(m) for m in moves if m]))
    return st, team

def fmt_trainer(tid):
    o = TR + tid * TR_STRIDE
    st, team = read_team(o)
    if not team:
        return None
    cls = clsname(rom.u8(o + 1)); name = rom.read_name(o + 4, 12).strip()
    head = ("%s %s" % (cls, name)).strip() or "Trainer #%d" % tid
    lines = ["### %s  *(trainer #%d)*" % (head, tid)]
    for m in team:
        held = "  @%s" % itemname(m["item"]) if m["item"] else ""
        mv = ", ".join(m["moves"]) if m["moves"] else "(level-up moveset)"
        lines.append("- **%s** Lv%d%s — %s" % (spname(m["sp"]), m["lvl"], held, mv))
    return "\n".join(lines)

def boss_catalogue():
    """Ordered (tid, category) for gyms/rocket/E4/champion/rivals from feature_bosses defs."""
    cats = []
    bd = fb.boss_defs()
    spans = [(0, 8, "Gym Leaders"), (8, 10, "Team Rocket (Giovanni)"),
             (10, 14, "Elite Four"), (14, 18, "Elite Four (Rematch)")]
    for lo, hi, label in spans:
        for d in bd[lo:hi]:
            for tid in d["ids"]:
                cats.append((tid, label))
    champ = fb.champion_defs()
    for i, d in enumerate(champ):
        for tid in d["ids"]:
            cats.append((tid, "Champion" if i < 3 else "Champion (Rematch)"))
    for d in fb.rival_defs():
        for tid in d["ids"]:
            cats.append((tid, "Rival"))
    return cats

def boss_section():
    out = ["# Boss Battles\n",
           "Gym leaders, Team Rocket, the Elite Four (and their rematches), the Champion (and rematch),",
           "and every rival fight. Rival fights have three variants — the rival's team depends on which",
           "starter YOU chose (he takes the one with the type advantage).\n"]
    cats = boss_catalogue()
    boss_ids = set(t for t, _ in cats)
    cur = None
    for tid, label in cats:
        if label != cur:
            out.append("\n## %s\n" % label); cur = label
        block = fmt_trainer(tid)
        if block:
            out.append(block + "\n")
    return "\n".join(out), boss_ids

def regular_section(boss_ids):
    out = ["# Regular Trainers\n",
           "Every other fightable trainer in the game (not a boss/rival), with full teams and movesets.\n"]
    n = 0
    for tid in range(1, 743):
        if tid in boss_ids:
            continue
        block = fmt_trainer(tid)
        if block:
            out.append(block + "\n"); n += 1
    out.insert(1, "Total: %d trainers.\n" % n)
    return "\n".join(out)

# ---- ASSEMBLE --------------------------------------------------------------
def main():
    wild = wild_section()
    evo = evo_changes_section()
    bosses, boss_ids = boss_section()
    regular = regular_section(boss_ids)
    doc = ("# Project Red — Game Data\n\n"
           "Auto-generated from the built ROM (`build/project-red.gba`) by `build/gen_doc_gamedata.py`.\n"
           "Regenerate after any rebuild. Sections: [Wild Encounters](#wild-encounters), "
           "[Evolution Changes](#evolution-changes), [Boss Battles](#boss-battles), "
           "[Regular Trainers](#regular-trainers).\n\n---\n\n"
           + wild + "\n\n---\n\n" + evo + "\n\n---\n\n" + bosses + "\n\n---\n\n" + regular + "\n")
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "GAME_DATA.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", path, "(%d bytes, %d lines)" % (len(doc), doc.count("\n")))

if __name__ == "__main__":
    main()
