"""Feature: competitive trainer teams.
1. Every trainer gets a competitive custom moveset (STAB matched to its better attacking stat,
   strong coverage, and a setup/status move for bosses/aces) scaled to the mon's level, plus
   a smarter battle-AI flag.
2. Non-boss "route" trainers gain 1-3 extra Pokemon, themed to the team's types and level-scaled
   (early trainers skew to +1, later trainers to +3), capped at 6.

All processed trainers are rewritten as structType 3 (held item + 4 custom moves) in fresh free space.
Every generated move is filtered through learnset.Learnset so a mon never gets a move outside its real
Gen-9 learnset (e.g. the rival's Bulbasaur can no longer roll Thunder Shock as coverage).
"""
import gamedata, learnset
from feature_bosses import FIRST_RIVAL_IDS

TR_STRIDE=40; ELS={0:8,1:16,2:8,3:16}
BOSS_IDS={348,349,350,410,411,412,413,414,415,416,417,418,419,420,
          438,439,440,735,736,737,738,739,740,741}
RIVAL_CLASSES={81,89}   # recurring rival fights: competitive movesets, but NOT extra mons

# ---------- move tables (curated good moves by type; stats read from ROM) ----------
TYPE_MOVES = {
 "Normal":  ["Tackle","Body Slam","Return","Double-Edge","Hyper Voice","Extreme Speed","Façade","Boomburst","Slash"],
 "Fire":    ["Ember","Fire Fang","Flame Wheel","Flamethrower","Fire Punch","Fire Blast","Flare Blitz","Lava Plume","Heat Wave"],
 "Water":   ["Water Gun","Bubble Beam","Aqua Tail","Surf","Waterfall","Hydro Pump","Liquidation","Scald","Muddy Water"],
 "Electric":["Thunder Shock","Spark","Thunderbolt","Thunder Punch","Thunder","Wild Charge","Volt Switch","Discharge"],
 "Grass":   ["Vine Whip","Mega Drain","Razor Leaf","Giga Drain","Energy Ball","Leaf Blade","Seed Bomb","Power Whip","Petal Blizzard","Leaf Storm"],
 "Ice":     ["Ice Shard","Icy Wind","Ice Punch","Ice Beam","Aurora Beam","Blizzard","Icicle Crash","Avalanche"],
 "Fighting":["Karate Chop","Brick Break","Drain Punch","Close Combat","Aura Sphere","Cross Chop","Superpower","Sky Uppercut","Mach Punch"],
 "Poison":  ["Acid","Poison Jab","Sludge","Sludge Bomb","Gunk Shot","Poison Fang","Sludge Wave","Cross Poison"],
 "Ground":  ["Mud-Slap","Bulldoze","Dig","Earthquake","Earth Power","Mud Bomb","High Horsepower","Bone Rush"],
 "Flying":  ["Wing Attack","Aerial Ace","Air Slash","Drill Peck","Brave Bird","Air Cutter","Hurricane","Dual Wingbeat"],
 "Psychic": ["Confusion","Psybeam","Psyshock","Psychic","Zen Headbutt","Future Sight","Extrasensory","Psystrike"],
 "Bug":     ["Bug Bite","Struggle Bug","X-Scissor","Bug Buzz","Megahorn","Leech Life","Pin Missile","U-turn"],
 "Rock":    ["Rock Throw","Rock Tomb","Rock Slide","Stone Edge","Power Gem","Ancient Power","Rock Blast","Head Smash"],
 "Ghost":   ["Lick","Astonish","Shadow Punch","Shadow Ball","Shadow Claw","Hex","Phantom Force","Shadow Sneak"],
 "Dragon":  ["Twister","Dragon Breath","Dragon Claw","Dragon Pulse","Dragon Rush","Outrage","Draco Meteor","Dual Chop"],
 "Dark":    ["Bite","Feint Attack","Crunch","Dark Pulse","Knock Off","Night Slash","Foul Play","Sucker Punch"],
 "Steel":   ["Metal Claw","Bullet Punch","Iron Head","Flash Cannon","Iron Tail","Meteor Mash","Steel Wing","Gyro Ball"],
 "Fairy":   ["Fairy Wind","Draining Kiss","Dazzling Gleam","Play Rough","Moonblast","Disarming Voice","Spirit Break"],
}
# coverage is drawn from these types' move pools (level-scaled), best-first
COVERAGE_TYPES = ["Ground","Ice","Electric","Rock","Fire","Fairy","Dark","Fighting","Water","Flying","Steel","Grass"]
# ROM truncates some type names; map them back to TYPE_MOVES keys
TYPE_ALIAS = {"psychc":"Psychic","electr":"Electric","fight":"Fighting"}
def _canon_type(name):
    n=name.strip()
    return TYPE_ALIAS.get(n.lower(), n.title())
BOOST_PHYS = ["Swords Dance","Dragon Dance","Bulk Up"]
BOOST_SPEC = ["Calm Mind","Nasty Plot"]
STATUS     = ["Toxic","Thunder Wave","Will-O-Wisp","Recover","Roost"]

def _norm(s): return "".join(c for c in s.upper() if c.isalnum())

class Moves:
    def __init__(self, rom):
        self.rom=rom
        self.MVN=rom.tables["data.pokemon.moves.names"]["addr"]
        self.MVS=rom.tables["data.pokemon.moves.stats.battle"]["addr"]
        self.byname={}
        for i in range(992):
            n=_norm(rom.read_name(self.MVN+i*13,13))
            if n and n not in self.byname: self.byname[n]=i
        self._stat={}
    def id(self,name):
        return self.byname.get(_norm(name))
    def stat(self,mid):
        if mid not in self._stat:
            o=self.MVS+mid*12
            self._stat[mid]=dict(power=self.rom.u8(o+1),type=self.rom.u8(o+2),
                                 acc=self.rom.u8(o+3),cat=self.rom.u8(o+10))
        return self._stat[mid]
    def resolve_pool(self, names):
        out=[]
        for nm in names:
            mid=self.id(nm)
            if mid is None: continue
            st=self.stat(mid)
            out.append((mid,st["power"],st["cat"],st["type"]))
        return out

def _cap(level):
    if level<=10: return 55
    if level<=18: return 70
    if level<=28: return 85
    if level<=40: return 100
    if level<=55: return 120
    return 999

def build_moveset(M, rom, species, level, boss=False, L=None):
    st=gamedata.stats(rom,species)
    t1=_canon_type(gamedata.type_name(rom,st["t1"]))
    t2=_canon_type(gamedata.type_name(rom,st["t2"]))
    types=[t for t in dict.fromkeys([t1,t2]) if t in TYPE_MOVES] or ["Normal"]
    montypes={t1,t2}
    pref = 0 if st["atk"] >= st["spa"] else 1   # 0 phys, 1 spec
    cap=_cap(level)
    legal = L.legal(species) if L is not None else None   # restrict every pick to the real learnset
    def ok(mid): return legal is None or mid in legal
    moves=[]
    def best_from(pool_names, want_cat=None):
        cands=[c for c in M.resolve_pool(pool_names) if 0<c[1]<=cap and c[0] not in moves and ok(c[0])]
        if want_cat is not None:
            cands=[c for c in cands if c[2]==want_cat] or cands
        cands.sort(key=lambda c:c[1], reverse=True)
        return cands[0][0] if cands else None
    # 1) STAB for each of the mon's types (prefer its better attacking category)
    for t in types:
        m=best_from(TYPE_MOVES[t], pref) or best_from(TYPE_MOVES[t], None)
        if m is not None: moves.append(m)
    # 2) coverage from other types, level-scaled; rotate order per-species so teammates differ
    rot=species % len(COVERAGE_TYPES)
    cov_order=COVERAGE_TYPES[rot:]+COVERAGE_TYPES[:rot]
    for ct in cov_order:
        if len(moves)>=4: break
        if ct in montypes: continue
        m=best_from(TYPE_MOVES[ct], pref) or best_from(TYPE_MOVES[ct], None)
        if m is not None: moves.append(m)
    # 3) boss/ace flavour: swap the 4th slot for a setup/status move (keeps >=3 damaging)
    if boss and level>=30 and len(moves)>=3:
        for nm in (BOOST_PHYS if pref==0 else BOOST_SPEC)+STATUS:
            mid=M.id(nm)
            if mid is not None and mid not in moves and ok(mid):
                moves=moves[:3]+[mid]; break
    # 4) fill to 4 distinct, level-appropriate moves
    if len(moves)<4:
        pool=[n for t in types for n in TYPE_MOVES[t]]+[n for ct in COVERAGE_TYPES for n in TYPE_MOVES[ct]]
        for nm in pool:
            if len(moves)>=4: break
            mid=M.id(nm)
            if mid is not None and mid not in moves and ok(mid) and 0<M.stat(mid)["power"]<=cap:
                moves.append(mid)
    # 5) last resort: pad from the mon's OWN level-up learnset (always legal)
    if len(moves)<4 and L is not None:
        for mid in L.fallback_moves(species, level):
            if len(moves)>=4: break
            if mid not in moves: moves.append(mid)
    # 6) movepool-starved mon (e.g. low-level Abra): fill remaining slots with other legal moves so we
    #    get 4 DISTINCT legal moves instead of repeating one. Stay level-appropriate: damaging moves
    #    within the power cap first, then status moves, then (only if truly stuck) anything legal.
    if len(moves)<4 and legal is not None:
        by_power=sorted(legal, key=lambda x:M.stat(x)["power"], reverse=True)
        def fill_from(pred):
            for mid in by_power:
                if len(moves)>=4: break
                if mid not in moves and pred(M.stat(mid)["power"]): moves.append(mid)
        fill_from(lambda p: 0<p<=cap)   # damaging, level-appropriate
        fill_from(lambda p: p==0)       # status (Calm Mind, Light Screen, Thunder Wave, ...)
        fill_from(lambda p: True)       # absolute last resort: any legal move
    if not moves:   # mon with no usable learnset at all (shouldn't happen) -> a guaranteed-legal Tackle
        mid=M.id("Tackle"); moves.append(mid if mid is not None else 1)
    while len(moves)<4: moves.append(moves[0])
    return moves[:4]

# ---------- species pool for route additions ----------
def build_add_pool(rom):
    valids=gamedata.valid_species(rom)
    lowest={}
    for i in valids:
        n=_norm(gamedata.spname(rom,i))
        if n and n not in lowest: lowest[n]=i
    by_type={}
    for i in valids:
        nm=gamedata.spname(rom,i)
        if lowest[_norm(nm)]!=i: continue        # skip alt forms / dupes
        if gamedata.is_legendary(nm): continue
        if nm.startswith("Unown "): continue
        st=gamedata.stats(rom,i)
        rec=(i,st["bst"])
        for t in set([st["t1"],st["t2"]]):
            by_type.setdefault(t,[]).append(rec)
    for t in by_type: by_type[t].sort(key=lambda r:r[1])
    return by_type

def _target_bst(level):
    return max(240, min(560, 240+level*6))

def pick_add(by_type, type_id, level, salt):
    target=_target_bst(level)
    cands=by_type.get(type_id,[])
    if not cands:
        # any type
        allc=[r for v in by_type.values() for r in v]
        cands=allc
    window=[r for r in cands if abs(r[1]-target)<=70]
    if not window: window=[r for r in cands if abs(r[1]-target)<=140] or cands
    return window[salt % len(window)][0]

def _addcount(level, salt):
    # early skew +1, mid +2, late +3, with mild variety
    if level<=15: base=1
    elif level<=30: base=2
    else: base=3
    j=(salt*7+level)%10
    if base==1 and j>=8: base=2
    elif base==2 and j<2: base=1
    elif base==2 and j>=8: base=3
    elif base==3 and j<2: base=2
    return base

# ---------- apply ----------
import struct
def apply(rom, verbose=True):
    M=Moves(rom)
    L=learnset.Learnset(rom)
    by_type=build_add_pool(rom)
    TR=rom.tables["data.trainers.stats"]["addr"]
    def read_team(o):
        st=rom.u8(o); cnt=rom.u8(o+0x20); ptr=rom.ptr(o+0x24); esz=ELS.get(st,8)
        team=[]
        if ptr:
            for m in range(cnt):
                mo=ptr+m*esz
                iv=rom.u16(mo); lv=rom.u16(mo+2); sp=rom.u16(mo+4)
                item = rom.u16(mo+6) if st in (2,3) else 0
                team.append([iv,lv,sp,item])
        return st,cnt,team
    nproc=0; nadded=0; nmoves=0
    for tid in range(1,743):
        # The first rival fight (Oak's Lab, right after the starter pick) is left untouched so it keeps
        # feature_bosses' auto-generated level-up-only moveset: an easy, fully-legal opener.
        if tid in FIRST_RIVAL_IDS: continue
        o=TR+tid*TR_STRIDE
        st,cnt,team=read_team(o)
        if not team: continue
        if any(t[2]==0 or t[2]>1440 for t in team): continue
        if any(t[1]<1 or t[1]>100 for t in team): continue
        cls = rom.u8(o+1)
        is_boss = tid in BOSS_IDS
        is_special = is_boss or cls in RIVAL_CLASSES
        # --- add route mons (skip bosses & rivals: they keep curated rosters) ---
        if not is_special and len(team)<6:
            maxlv=max(t[1] for t in team)
            want=min(6-len(team), _addcount(maxlv, tid))
            # team types to theme additions
            tts=[]
            for t in team:
                sstat=gamedata.stats(rom,t[2]); tts+= [sstat["t1"],sstat["t2"]]
            tts=[x for x in tts] or [0]
            for k in range(want):
                type_id=tts[(tid+k)%len(tts)]
                lv=maxlv if k==0 else max(2, maxlv-((k)%2))
                sp=pick_add(by_type, type_id, lv, tid*3+k)
                team.append([100, lv, sp, 0])
                nadded+=1
        # --- competitive movesets (structType 3) + iv ---
        blob=bytearray()
        team.sort(key=lambda t:t[1])   # weakest first, ace (highest level) last
        for idx,(iv,lv,sp,item) in enumerate(team):
            is_ace = is_boss and idx==len(team)-1
            mv=build_moveset(M, rom, sp, lv, boss=(is_boss and (is_ace or lv>=40)), L=L)
            new_iv = 255 if is_boss else 100
            blob += struct.pack("<HHHH", new_iv, lv, sp, item)
            blob += struct.pack("<HHHH", mv[0],mv[1],mv[2],mv[3])
            nmoves+=1
        off=rom.alloc(len(blob))
        rom.data[off:off+len(blob)]=blob
        rom.wu8(o+0x00, 3)             # structType 3 = item + custom moves
        rom.wu8(o+0x20, len(team))     # party count
        rom.wptr(o+0x24, off)
        # smarter AI (check bad move + try to faint + check viability)
        rom.wu8(o+0x1C, 0x07)
        nproc+=1
    if verbose:
        print("[trainers] processed %d trainers; +%d route Pokemon added; %d mons given competitive movesets"
              % (nproc, nadded, nmoves))
    return dict(processed=nproc, added=nadded, mons=nmoves)

if __name__=="__main__":
    import romlib
    rom=romlib.Rom()
    apply(rom)
