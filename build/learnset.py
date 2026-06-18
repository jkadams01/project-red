"""Per-species REAL Gen-9 legal move sets, used to keep generated trainer movesets inside each
species' true Gen-9 learnset.

The data comes from `gen9_legal.py` (vendored), which `gen9_gen.py` builds from Pokemon Showdown's
learnset dataset: for each species, the moves in its LATEST-generation learnset (Gen 9 for Scarlet/
Violet mons; the most recent gen otherwise = what it keeps transferred into Gen 9), matched by name to
this ROM's moves, unioned with the ROM's own (accurate) level-up moves.

We do NOT use the ROM's own TM/tutor compatibility tables -- in this CFRU/UCDEP base they are broad,
older-gen-style flags, NOT Gen-9 learnsets (they let Abra "learn" Sand Tomb, Dual Chop, Charge Beam).
"""
import gamedata

try:
    import gen9_legal
    GEN9 = gen9_legal.LEGAL
except Exception:
    GEN9 = {}


class Learnset:
    def __init__(self, rom):
        self.rom = rom
        self.LU = rom.tables["data.pokemon.moves.levelup"]["addr"]
        self._lu_cache = {}
        self._legal_cache = {}

    # ---- level-up: per-species pointer -> [ (move u16, level u8) ... 00 00 FF ] ----
    def levelup(self, species):
        """Ordered (level, move_id) list from the species' level-up learnset (ascending level)."""
        c = self._lu_cache.get(species)
        if c is not None:
            return c
        out = []
        p = self.rom.ptr(self.LU + species * 4)
        if p:
            o = p
            for _ in range(64):
                mv = self.rom.u16(o); lv = self.rom.u8(o + 2)
                if mv == 0 and lv == 0xFF:
                    break
                out.append((lv, mv)); o += 3
        self._lu_cache[species] = out
        return out

    def legal(self, species):
        """Set of every move id the species can legally have in Gen 9 (from gen9_legal). Falls back to
        the ROM's level-up moves only if the species has no Gen-9 data."""
        c = self._legal_cache.get(species)
        if c is not None:
            return c
        if species in GEN9:
            s = set(GEN9[species])
        else:
            s = set(m for _, m in self.levelup(species))
        s.discard(0)
        self._legal_cache[species] = s
        return s

    def fallback_moves(self, species, level):
        """Legal move ids to pad a moveset with: the mon's level-up moves it would know by `level`
        (most-recent first), then any remaining level-up move. Always legal, always non-empty if the
        mon has any level-up learnset."""
        lu = self.levelup(species)
        known = [mv for lv, mv in lu if lv <= level]
        later = [mv for lv, mv in lu if lv > level]
        seen = set(); out = []
        for mv in list(reversed(known)) + later:
            if mv and mv not in seen:
                seen.add(mv); out.append(mv)
        return out


if __name__ == "__main__":
    import romlib
    rom = romlib.Rom()
    L = Learnset(rom)
    MVN = rom.tables["data.pokemon.moves.names"]["addr"]
    def mvn(m): return rom.read_name(MVN + m * 13, 13).strip()
    def idx(name):
        for i in range(1, gamedata.N):
            if gamedata.norm(gamedata.spname(rom, i)) == gamedata.norm(name):
                return i
    print("Gen-9 data loaded for %d species" % len(GEN9))
    for nm in ["Abra", "Bulbasaur", "Garchomp", "Corviknight"]:
        i = idx(nm)
        if i is None:
            continue
        leg = L.legal(i)
        bad = [q for q in ["Sand Tomb", "Dual Chop", "Charge Beam"]
               if any(gamedata.norm(mvn(m)) == gamedata.norm(q) for m in leg)]
        print("%-12s idx=%-4d legal=%-3d  illegal-present=%s" % (nm, i, len(leg), bad or "none"))
