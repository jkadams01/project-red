"""Recon every evolution method in the built ROM: enumerate method ids with counts + example
(sourceMon -> targetMon, param), so we can pin down which methods are IMPOSSIBLE solo (trade-based)
and whether each affected mon has a parallel solo method already."""
import romlib, gamedata
from collections import defaultdict
rom = romlib.Rom()
IST = rom.tables["data.items.stats"]["addr"]
def itemname(a): return rom.read_name(IST + a*44, 14).strip() if 0 < a < 900 else ""
def sp(s): return gamedata.spname(rom, s)

valids = set(gamedata.valid_species(rom))
bymethod = defaultdict(list)     # method -> [(src, param, tgt)]
per_mon = defaultdict(list)      # src -> [(method, param, tgt)]
for i in valids:
    nm = sp(i)
    if not nm or nm.startswith("?"):
        continue
    for (m, arg, tgt, val) in gamedata.evolutions(rom, i):
        if m == 0 and tgt == 0:
            continue
        if tgt not in valids:
            continue
        bymethod[m].append((i, arg, tgt))
        per_mon[i].append((m, arg, tgt))

print("=== METHODS PRESENT (id: count) with examples ===")
for m in sorted(bymethod):
    rows = bymethod[m]
    ex = []
    for src, arg, tgt in rows[:4]:
        p = itemname(arg) or str(arg)
        ex.append("%s->%s[%s]" % (sp(src), sp(tgt), p))
    print("  m=%-3d n=%-3d  %s" % (m, len(rows), " ".join(ex)))

# Heuristic: trade methods = no level/param consistency. We'll examine candidate trade methods 5 & 6.
print("\n=== candidate TRADE methods (5=trade, 6=trade-item) full list ===")
for m in (5, 6):
    if m not in bymethod:
        print("  method %d: (none present)" % m); continue
    print("  --- method %d (%d entries) ---" % (m, len(bymethod[m])))
    for src, arg, tgt in bymethod[m]:
        # does this mon ALSO have a solo (non-trade) evolution to the SAME target?
        parallel = [(mm, aa) for (mm, aa, tt) in per_mon[src] if tt == tgt and mm not in (5, 6)]
        par = ("  ALSO via %s" % parallel) if parallel else "  (NO solo path!)"
        print("     %-12s -> %-12s param=%s(%s)%s" % (sp(src), sp(tgt), arg, itemname(arg) or "-", par))

# Also list any mon whose ONLY evolution path(s) are all trade-based (truly stuck solo)
print("\n=== mons whose EVERY evolution is trade-based (truly impossible solo) ===")
stuck = []
for src, evs in per_mon.items():
    methods = set(m for m, a, t in evs)
    if methods and methods <= {5, 6}:
        stuck.append(src)
for src in stuck:
    outs = ", ".join("%s(m%d/%s)" % (sp(t), m, itemname(a) or a) for m, a, t in per_mon[src])
    print("  %-12s -> %s" % (sp(src), outs))
print("\ntotal species with >=1 trade evolution entry:",
      len(set(s for m in (5, 6) for (s, a, t) in bymethod.get(m, []))))
