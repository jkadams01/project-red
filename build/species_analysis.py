import romlib
rom = romlib.Rom()
names_addr = rom.tables["data.pokemon.names"]["addr"]
stats_addr = rom.tables["data.pokemon.stats"]["addr"]
evo_addr   = rom.tables["data.pokemon.evolutions"]["addr"]
types_addr = rom.tables["data.pokemon.type.names"]["addr"]
NAME_W=11; STATS_W=28; EVO_W=128; N=1440

def spname(i): return rom.read_name(names_addr + i*NAME_W, NAME_W)
def type_name(i): return rom.read_name(types_addr + i*7, 7)  # [name""7] guess

def stats(i):
    o = stats_addr + i*STATS_W
    d = rom.data
    hp,atk,df,spd,spa,spdf = d[o],d[o+1],d[o+2],d[o+3],d[o+4],d[o+5]
    t1,t2 = d[o+6],d[o+7]
    return dict(hp=hp,atk=atk,df=df,spd=spd,spa=spa,spdf=spdf,bst=hp+atk+df+spd+spa+spdf,t1=t1,t2=t2)

# True evolution methods (exclude form/mega/gmax markers). Methods >=250 are special (mega/forms/etc.)
def evolutions(i):
    base = evo_addr + i*EVO_W
    out=[]
    for s in range(16):
        o=base+s*8
        method=rom.u16(o); arg=rom.u16(o+2); target=rom.u16(o+4); value=rom.u16(o+6)
        if method==0 and target==0: continue
        out.append((method,arg,target,value))
    return out

def is_true_evo_method(method):
    # 1..0x2A are standard evolution methods in CFRU; >=250 (0xFA..) are mega/form/gmax/primal markers
    return 1 <= method <= 0x4A

def norm(s):
    return "".join(c for c in s.upper() if c.isalnum())

LEG_MYTH = {
 # gen1
 "Articuno","Zapdos","Moltres","Mewtwo","Mew",
 # gen2
 "Raikou","Entei","Suicune","Lugia","Ho-Oh","Celebi",
 # gen3
 "Regirock","Regice","Registeel","Latias","Latios","Kyogre","Groudon","Rayquaza","Jirachi","Deoxys",
 # gen4
 "Uxie","Mesprit","Azelf","Dialga","Palkia","Heatran","Regigigas","Giratina","Cresselia",
 "Phione","Manaphy","Darkrai","Shaymin","Arceus",
 # gen5
 "Victini","Cobalion","Terrakion","Virizion","Tornadus","Thundurus","Reshiram","Zekrom",
 "Landorus","Kyurem","Keldeo","Meloetta","Genesect",
 # gen6
 "Xerneas","Yveltal","Zygarde","Diancie","Hoopa","Volcanion",
 # gen7 (incl. UBs + Type:Null/Silvally as restricted)
 "Tapu Koko","Tapu Lele","Tapu Bulu","Tapu Fini","Cosmog","Cosmoem","Solgaleo","Lunala",
 "Necrozma","Magearna","Marshadow","Zeraora","Meltan","Melmetal",
 "Type: Null","Silvally","Nihilego","Buzzwole","Pheromosa","Xurkitree","Celesteela",
 "Kartana","Guzzlord","Poipole","Naganadel","Stakataka","Blacephalon",
 # gen8
 "Zacian","Zamazenta","Eternatus","Kubfu","Urshifu","Regieleki","Regidrago","Glastrier",
 "Spectrier","Calyrex","Zarude","Enamorus",
 # gen9
 "Wo-Chien","Chien-Pao","Ting-Lu","Chi-Yu","Koraidon","Miraidon","Walking Wake","Iron Leaves",
 "Gouging Fire","Raging Bolt","Iron Boulder","Iron Crown","Okidogi","Munkidori","Fezandipiti",
 "Ogerpon","Terapagos","Pecharunt",
 # exact ROM (hand-abbreviated) spellings that don't match canonical normalization
 "WalkinWake","GouginFire","IronBouldr","Fezandipti","Blacphalon","Type? Null",
}
# NOTE: regular Paradox mons (Roaring Moon, Iron Valiant, Sandy Shocks, Iron Treads,
# Iron Bundle, Iron Hands, Iron Jugulis, Iron Moth, Iron Thorns) are NOT legendary -> stay catchable.
LEG_NORM = {norm(x) for x in LEG_MYTH}
def is_legendary(name): return norm(name) in LEG_NORM

def valid_species():
    out=[]
    for i in range(1, N):
        nm = spname(i)
        if not nm or nm.startswith("?"): continue
        st = stats(i)
        if st["bst"] == 0: continue
        out.append(i)
    return out

def analyze():
    valids = valid_species()
    validset = set(valids)
    # evolution target set (true evolutions only)
    evo_targets = set()
    for i in valids:
        for (m,arg,tgt,val) in evolutions(i):
            if is_true_evo_method(m) and tgt in validset:
                evo_targets.add(tgt)
    # lowest index per name (to dedupe alternate forms which reuse names)
    lowest_for_name = {}
    for i in valids:
        n = norm(spname(i))
        if n not in lowest_for_name:
            lowest_for_name[n] = i
    base_lines = []
    for i in valids:
        nm = spname(i)
        if i in evo_targets:           # has a pre-evolution -> not a base form
            continue
        if lowest_for_name[norm(nm)] != i:   # alternate form (a lower index shares the name)
            continue
        if is_legendary(nm):
            continue
        st = stats(i)
        base_lines.append((i, nm, st["bst"], st["t1"], st["t2"]))
    return valids, evo_targets, base_lines

if __name__ == "__main__":
    valids, targets, lines = analyze()
    print("valid species:", len(valids))
    print("base lines (non-legendary, deduped):", len(lines))
    # check legendary names that didn't match any species (spelling problems)
    allnorm = {norm(spname(i)) for i in valids}
    missing = [x for x in LEG_MYTH if norm(x) not in allnorm]
    print("legendary names with NO matching species (check spelling):", sorted(missing))
    # show sample of base lines sorted by bst
    lines_sorted = sorted(lines, key=lambda x:x[2])
    print("weakest 12:", [(n,b) for _,n,b,_,_ in lines_sorted[:12]])
    print("strongest 12:", [(n,b) for _,n,b,_,_ in lines_sorted[-12:]])
    # water lines count
    WATER = None
    for ti in range(20):
        if type_name(ti).upper().startswith("WATER"): WATER=ti
    print("WATER type id:", WATER)
    water = [n for _,n,b,t1,t2 in lines if WATER is not None and (t1==WATER or t2==WATER)]
    print("water base lines:", len(water))
