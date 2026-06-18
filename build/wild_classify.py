import romlib, wild, maps
rom = wild.rom
entries = wild.walk()

# Sevii-island region name keywords (post-mainland). Islands 4-7 + Tanoby are post-league;
# islands 1-3 are reachable mid-game. We'll mark all Sevii as "SEVII" and Kanto as "KANTO".
SEVII_KEYS = ["ISLAND","KINDLE","TREASURE BEACH","CAPE BRINK","BOND BRIDGE","BERRY FOREST",
              "MT. EMBER","MT EMBER","ICEFALL","LOST CAVE","PATTERN BUSH","ALTERING CAVE",
              "TANOBY","CHAMBER","SEVAULT","CANYON","DOTTED","TRAINER TOWER","RUIN VALLEY",
              "GREEN PATH","OUTCAST","WATER PATH","RESORT GORGEOUS","MEMORIAL PILLAR","PORT"]

def classify(label):
    up = label.upper()
    for k in SEVII_KEYS:
        if k in up:
            return "SEVII"
    return "KANTO"

rows = []
for e in entries:
    lab = maps.map_label(e["bank"], e["map"])
    cls = classify(lab)
    nslots = sum(len(e["cats"][n]["slots"]) for n,_ in wild.CATS if e["cats"][n])
    rows.append((cls, e["bank"], e["map"], lab, nslots))

# print grouped
from collections import defaultdict
byc = defaultdict(lambda:[0,0])
for cls,b,m,lab,ns in rows:
    byc[cls][0]+=1; byc[cls][1]+=ns
print("=== KANTO entries ===")
for cls,b,m,lab,ns in rows:
    if cls=="KANTO": print("  %d.%-3d %-28s slots=%d"%(b,m,lab[:28],ns))
print("=== SEVII entries ===")
for cls,b,m,lab,ns in rows:
    if cls=="SEVII": print("  %d.%-3d %-28s slots=%d"%(b,m,lab[:28],ns))
print("=== summary ===")
for cls,(cnt,ns) in byc.items():
    print("  %s: %d entries, %d slots" % (cls, cnt, ns))
