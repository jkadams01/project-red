"""Read back the built ROM and assert every custom-moveset trainer mon only knows moves inside its
species' real learnset. Also confirms the first rival fight stays level-up-only (structType 2)."""
import romlib, gamedata, learnset
from feature_bosses import FIRST_RIVAL_IDS

rom = romlib.Rom()                      # default = built project-red.gba
L = learnset.Learnset(rom)
MVN = rom.tables["data.pokemon.moves.names"]["addr"]
def mvn(m): return rom.read_name(MVN + m*13, 13)
def spn(s): return gamedata.spname(rom, s)

TR = rom.tables["data.trainers.stats"]["addr"]
TR_STRIDE = 40
ELS = {0: 8, 1: 16, 2: 8, 3: 16}

illegal = []        # (tid, species_name, move_name)
checked_mons = 0
type3 = 0
for tid in range(1, 743):
    o = TR + tid*TR_STRIDE
    st = rom.u8(o); cnt = rom.u8(o+0x20); ptr = rom.ptr(o+0x24)
    if not ptr or cnt == 0 or cnt > 6:
        continue
    esz = ELS.get(st, 8)
    has_moves = st in (1, 3)            # structType 1/3 carry explicit moves
    if has_moves:
        type3 += 1
    for m in range(cnt):
        mo = ptr + m*esz
        sp = rom.u16(mo+4)
        if sp == 0 or sp > 1440:
            continue
        if not has_moves:
            continue
        moff = mo + (8 if st == 3 else 4)   # struct3: iv,lv,sp,item then 4 moves; struct1: iv,lv,sp then 4 moves
        legal = L.legal(sp)
        for k in range(4):
            mid = rom.u16(moff + k*2)
            if mid == 0:
                continue
            checked_mons += 1
            if mid not in legal:
                illegal.append((tid, spn(sp), mvn(mid)))

print("trainers with explicit movesets (structType 1/3):", type3)
print("move-slots checked:", checked_mons)
print("ILLEGAL moves found:", len(illegal))
for row in illegal[:60]:
    print("   tr%-4d %-12s -> %s" % row)
if len(illegal) > 60:
    print("   ... and %d more" % (len(illegal)-60))

print("\n--- first rival fight (Oak's Lab) ---")
for tid in sorted(FIRST_RIVAL_IDS):
    o = TR + tid*TR_STRIDE
    st = rom.u8(o); cnt = rom.u8(o+0x20); ptr = rom.ptr(o+0x24)
    mons = []
    if ptr:
        esz = ELS.get(st, 8)
        for m in range(cnt):
            mo = ptr + m*esz
            mons.append("%s L%d" % (spn(rom.u16(mo+4)), rom.u16(mo+2)))
    print("  tr%d structType=%d (%s) cnt=%d team=%s"
          % (tid, st, "level-up moves" if st in (0, 2) else "CUSTOM MOVES", cnt, mons))

print("\nRESULT:", "PASS - all trainer mons legal" if not illegal else "FAIL - %d illegal moves" % len(illegal))
