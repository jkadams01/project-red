"""Per-species legal move sets, parsed from the ROM's own learnset tables so that
generated trainer movesets stay inside each species' real Gen-9 learnset.

A move is legal for a species if it appears in ANY of:
  - the level-up learnset           (data.pokemon.moves.levelup)
  - the TM/HM compatibility bitfield (data.pokemon.moves.tmcompatibility; HMs live in the 128-TM list)
  - the move-tutor compatibility     (data.pokemon.moves.tutorcompatibility)
  - the egg-move table for its base form (data.pokemon.moves.egg, inherited up the evo line)

This is the source of truth for "what can this mon actually learn" in the UCDEP base; the curated
competitive pools in feature_trainers are filtered against it (a Bulbasaur can never roll Thunder Shock).
"""
import gamedata

COMPAT_BYTES = 16   # 128 TM/tutor slots -> 16-byte bitfield per species
EGG_SPECIES_OFFSET = 20000   # CFRU egg table: value>=offset marks a new species section


class Learnset:
    def __init__(self, rom):
        self.rom = rom
        t = rom.tables
        self.LU  = t["data.pokemon.moves.levelup"]["addr"]
        self.TMC = t["data.pokemon.moves.tmcompatibility"]["addr"]
        self.TUC = t["data.pokemon.moves.tutorcompatibility"]["addr"]
        self._tmlist  = [rom.u16(t["data.pokemon.moves.tms"]["addr"]  + k*2) for k in range(128)]
        self._tutlist = [rom.u16(t["data.pokemon.moves.tutors"]["addr"] + k*2) for k in range(128)]
        self._lu_cache = {}
        self._legal_cache = {}
        self._egg = None
        self._base = None

    # ---- level-up: per-species pointer -> [ (move u16, level u8) ... 00 00 FF ] ----
    def levelup(self, species):
        """Ordered (level, move_id) list from the species' level-up learnset (ascending level)."""
        c = self._lu_cache.get(species)
        if c is not None:
            return c
        out = []
        p = self.rom.ptr(self.LU + species*4)
        if p:
            o = p
            for _ in range(64):   # real learnsets are well under 64 entries
                mv = self.rom.u16(o); lv = self.rom.u8(o+2)
                if mv == 0 and lv == 0xFF:
                    break
                out.append((lv, mv)); o += 3
        self._lu_cache[species] = out
        return out

    def _bitfield(self, compat_addr, species, idlist):
        base = compat_addr + species*COMPAT_BYTES
        rom = self.rom; out = []
        for b in range(128):
            if rom.u8(base + (b >> 3)) & (1 << (b & 7)):
                out.append(idlist[b])
        return out

    def _egg_table(self):
        if self._egg is not None:
            return self._egg
        rom = self.rom; o = rom.tables["data.pokemon.moves.egg"]["addr"]
        m = {}; cur = None
        for _ in range(20000):
            v = rom.u16(o); o += 2
            if v == 0xFFFF:
                break
            if v >= EGG_SPECIES_OFFSET:
                cur = v - EGG_SPECIES_OFFSET; m.setdefault(cur, set())
            elif cur is not None:
                m[cur].add(v)
        self._egg = m
        return m

    def _base_form(self):
        """species -> lowest pre-evolution (egg moves are stored only on the base form)."""
        if self._base is not None:
            return self._base
        rom = self.rom
        valids = set(gamedata.valid_species(rom))
        pre = {}
        for i in valids:
            for (mth, arg, tgt, val) in gamedata.evolutions(rom, i):
                if gamedata.is_true_evo_method(mth) and tgt in valids:
                    pre.setdefault(tgt, i)
        base = {}
        for i in valids:
            cur = i; seen = set()
            while cur in pre and cur not in seen:
                seen.add(cur); cur = pre[cur]
            base[i] = cur
        self._base = base
        return base

    def legal(self, species):
        """Set of every move id the species can legally learn (level-up | TM/HM | tutor | egg)."""
        c = self._legal_cache.get(species)
        if c is not None:
            return c
        s = set(mv for _, mv in self.levelup(species))
        s |= set(self._bitfield(self.TMC, species, self._tmlist))
        s |= set(self._bitfield(self.TUC, species, self._tutlist))
        s |= self._egg_table().get(self._base_form().get(species, species), set())
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
        ordered = list(reversed(known)) + later
        seen = set(); out = []
        for mv in ordered:
            if mv and mv not in seen:
                seen.add(mv); out.append(mv)
        return out


if __name__ == "__main__":
    import romlib
    rom = romlib.Rom()
    L = Learnset(rom)
    MVN = rom.tables["data.pokemon.moves.names"]["addr"]
    def mvn(m): return rom.read_name(MVN + m*13, 13)
    def idx(name):
        for i in range(1, gamedata.N):
            if gamedata.norm(gamedata.spname(rom, i)) == gamedata.norm(name):
                return i
    for nm in ["Bulbasaur", "Venusaur", "Pikachu", "Garchomp"]:
        i = idx(nm); leg = L.legal(i)
        ts = gamedata.norm("Thunder Shock")
        has_ts = any(gamedata.norm(mvn(m)) == ts for m in leg)
        print("%-10s idx=%-4d legal_moves=%-3d  ThunderShock=%s  lvlup=%s"
              % (nm, i, len(leg), has_ts, [mvn(m) for m in L.fallback_moves(i, 30)][:6]))
