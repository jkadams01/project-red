"""Read-back: confirm NO trade-based evolution remains in the built ROM, and every species that had a
trade evolution in the base now evolves via a solo method (level-up or item) to the SAME target."""
import romlib, gamedata, feature_evofix as F

rom = romlib.Rom()
base = romlib.Rom(F.__dict__.get("BASE", r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba"))

def evos(r, i):
    out = []
    for o, m, arg, tgt in F._slots(r, i):
        if m == 0 and tgt == 0:
            continue
        out.append((m, arg, tgt))
    return out

valids = sorted(gamedata.valid_species(rom))

# 1) no method 5 or 6 anywhere in the built ROM
bad = []
for i in valids:
    for (m, arg, tgt) in evos(rom, i):
        if m in (F.TRADE, F.TRADE_ITEM):
            bad.append((gamedata.spname(rom, i), m, tgt))
assert not bad, "trade methods still present: %s" % bad[:10]
print("no method-5/6 (trade) evolutions remain in built ROM  OK")

# 2) no Link Cable (item 87) evolution remains
lc = [(gamedata.spname(rom, i), tgt) for i in valids for (m, arg, tgt) in evos(rom, i)
      if m == F.ITEM and arg == F.LINK_CABLE]
assert not lc, "Link Cable evolutions still present: %s" % lc[:10]
print("no Link Cable evolutions remain  OK")

# 3) every species that had a trade evo in the BASE now reaches the SAME target via a solo method
SOLO = {1, 2, 3, 4, 7, 8, 9, 10, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 31, 32,
        34, 35, 36, 37, 38, 39, 40, 41, 42}   # all non-trade true-evo methods present in this ROM
checked = 0
for i in valids:
    base_trades = [(m, arg, tgt) for (m, arg, tgt) in evos(base, i) if m in (F.TRADE, F.TRADE_ITEM)]
    for (m, arg, tgt) in base_trades:
        now = [(mm, aa) for (mm, aa, tt) in evos(rom, i) if tt == tgt and mm in SOLO]
        assert now, "%s -> %s has no solo evolution after fix!" % (gamedata.spname(rom, i), gamedata.spname(rom, tgt))
        checked += 1
print("all %d former trade evolutions now reach their target via a solo method  OK" % checked)

# 4) spot report
print("\nsample of converted evolutions in the built ROM:")
for nm in ["Kadabra", "Machoke", "Haunter", "Graveler", "Onix", "Scyther", "Porygon", "Feebas"]:
    i = next((k for k in valids if gamedata.spname(rom, k) == nm), None)
    if i is None: continue
    es = []
    for (m, arg, tgt) in evos(rom, i):
        if m == F.LEVEL: es.append("%s @Lv%d" % (gamedata.spname(rom, tgt), arg))
        elif m == F.ITEM: es.append("%s @use %s" % (gamedata.spname(rom, tgt), F._itemname(rom, arg)))
        else: es.append("%s (m%d)" % (gamedata.spname(rom, tgt), m))
    print("  %-10s -> %s" % (nm, ", ".join(es)))

print("\nALL VERIFY CHECKS PASSED")
