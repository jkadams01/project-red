"""Remove every IMPOSSIBLE (trade-based) evolution and replace it with a solo-achievable one.

In a single-player ROM hack you can't trade, so trade evolutions are dead ends. This UCDEP base
already pairs each trade evolution with a parallel item-use entry (method 7), so nothing is truly
stuck -- but the leftover trade-method slots are still "impossible" methods sitting in the table.
This module rewrites them:

  * METHOD 6  EVO_TRADE_ITEM  (trade while holding an item: Onix+Metal Coat -> Steelix, etc.)
      -> drop the trade slot; the parallel METHOD 7 "use that item" entry (same item) stays, so the
         mon evolves by USING the item directly (all of these items are sold at the Celadon evo shop).
  * METHOD 5  EVO_TRADE       (plain trade: Kadabra -> Alakazam, Machoke -> Machamp, ...)
      -> convert the slot to METHOD 4 EVO_LEVEL at level 37, and clear the now-redundant parallel
         METHOD 7 Link Cable entry, so the mon simply evolves by LEVELLING UP (no item needed).

Methods 5 and 6 are the ONLY trade-based (solo-impossible) methods in this ROM (verified by
recon_evos.py); friendship / level / stat / beauty / move-known / coin methods are all solo-doable
and untouched, as are the mega (254) and form (253) pseudo-evolutions.

The evolution GRAPH is unchanged (every src->tgt edge is preserved), so base-form/wild/learnset logic
that reads the table is unaffected. Run BEFORE feature_celadon_evoshop so the shop's item list reflects
the new reality (Link Cable is no longer an evolution item, so it drops out of the shop).
"""
import gamedata

TRADE      = 5    # EVO_TRADE        (impossible solo)
TRADE_ITEM = 6    # EVO_TRADE_ITEM   (impossible solo)
ITEM       = 7    # EVO_ITEM         (use item from bag -> the solo keeper)
LEVEL      = 4    # EVO_LEVEL
LINK_CABLE = 87   # the item this base uses to stand in for "trade"
LEVEL_FOR_TRADE = 37   # plain-trade evos now evolve by levelling up to this


def _slots(rom, species):
    addr = gamedata.addrs(rom)["evo"] + species * gamedata.EVO_W
    return [(addr + s*8, rom.u16(addr + s*8), rom.u16(addr + s*8 + 2), rom.u16(addr + s*8 + 4))
            for s in range(16)]

def _clear(rom, o):
    for k in range(0, 8, 2):
        rom.wu16(o + k, 0)

def _actions(rom):
    """Every slot that needs changing, as dicts (read-only; used by both plan() and apply())."""
    acts = []
    for i in sorted(gamedata.valid_species(rom)):
        nm = gamedata.spname(rom, i)
        if not nm or nm.startswith("?"):
            continue
        slots = _slots(rom, i)
        for o, m, arg, tgt in slots:
            tnm = gamedata.spname(rom, tgt)
            if m == TRADE_ITEM:
                has_item = any(mm == ITEM and aa == arg and tt == tgt for (_o, mm, aa, tt) in slots)
                acts.append(dict(o=o, kind="item", src=nm, tgt=tnm,
                                 item=_itemname(rom, arg), clear=has_item))
            elif m == TRADE:
                acts.append(dict(o=o, kind="level", src=nm, tgt=tnm, level=LEVEL_FOR_TRADE))
            elif m == ITEM and arg == LINK_CABLE:
                acts.append(dict(o=o, kind="lc", src=nm, tgt=tnm))
    return acts

def _itemname(rom, a):
    IST = rom.tables["data.items.stats"]["addr"]
    return rom.read_name(IST + a*44, 14).strip() if 0 < a < 900 else str(a)

def plan(rom):
    """Player-facing conversion list [(src, tgt, kind, detail)] for documentation. Read-only.
    kind 'item' -> detail is the item name; kind 'level' -> detail is the level."""
    return [(a["src"], a["tgt"], a["kind"], a.get("item") if a["kind"] == "item" else a["level"])
            for a in _actions(rom) if a["kind"] in ("item", "level")]

def apply(rom, verbose=True):
    acts = _actions(rom)
    convs = [(a["src"], a["tgt"], a["kind"], a.get("item") if a["kind"] == "item" else a["level"])
             for a in acts if a["kind"] in ("item", "level")]
    ni = nl = nc = 0
    for a in acts:
        if a["kind"] == "item":
            if a["clear"]:
                _clear(rom, a["o"])            # parallel use-item entry stays
            else:
                rom.wu16(a["o"], ITEM)         # fallback: convert trade-item -> use-item in place
            ni += 1
        elif a["kind"] == "level":
            rom.wu16(a["o"], LEVEL)            # method -> EVO_LEVEL
            rom.wu16(a["o"] + 2, LEVEL_FOR_TRADE)   # param -> level
            rom.wu16(a["o"] + 6, 0)
            nl += 1
        elif a["kind"] == "lc":
            _clear(rom, a["o"])                # remove redundant Link Cable path
            nc += 1
    if verbose:
        print("[evofix] trade-item -> use-item: %d | plain-trade -> Lv%d: %d | removed Link Cable dupes: %d"
              % (ni, LEVEL_FOR_TRADE, nl, nc))
    return dict(item=ni, level=nl, linkcable=nc, conversions=convs)


if __name__ == "__main__":
    import romlib
    base = r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba"
    r = romlib.Rom.__new__(romlib.Rom)
    r.path = base
    with open(base, "rb") as f:
        r.data = bytearray(f.read())
    r.tables = romlib.parse_toml_anchors(base[:-4] + ".toml")
    r._free = romlib.Rom.FREE_BASE
    info = apply(r)
    print("conversions:")
    for src, tgt, kind, detail in info["conversions"]:
        print("  %-12s -> %-12s : %s" % (src, tgt, "Lv%d" % detail if kind == "level" else "use %s" % detail))
