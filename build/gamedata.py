"""Rom-parameterized data readers + species analysis for the UCDEP FireRed base."""
import romlib

NAME_W=11; STATS_W=28; EVO_W=128; N=1440

def addrs(rom):
    t=rom.tables
    return dict(
        names=t["data.pokemon.names"]["addr"],
        stats=t["data.pokemon.stats"]["addr"],
        evo=t["data.pokemon.evolutions"]["addr"],
        types=t["data.pokemon.type.names"]["addr"],
    )

def spname(rom, i):
    return rom.read_name(addrs(rom)["names"] + i*NAME_W, NAME_W)
def type_name(rom, i):
    return rom.read_name(addrs(rom)["types"] + i*7, 7)
def stats(rom, i):
    o = addrs(rom)["stats"] + i*STATS_W; d=rom.data
    hp,atk,df,spd,spa,spdf = d[o],d[o+1],d[o+2],d[o+3],d[o+4],d[o+5]
    return dict(hp=hp,atk=atk,df=df,spd=spd,spa=spa,spdf=spdf,
                bst=hp+atk+df+spd+spa+spdf, t1=d[o+6], t2=d[o+7])
def evolutions(rom, i):
    base = addrs(rom)["evo"] + i*EVO_W; out=[]
    for s in range(16):
        o=base+s*8
        m=rom.u16(o); arg=rom.u16(o+2); tgt=rom.u16(o+4); val=rom.u16(o+6)
        if m==0 and tgt==0: continue
        out.append((m,arg,tgt,val))
    return out
def is_true_evo_method(m): return 1 <= m <= 0x4A

def norm(s): return "".join(c for c in s.upper() if c.isalnum())

LEG_MYTH = {
 "Articuno","Zapdos","Moltres","Mewtwo","Mew",
 "Raikou","Entei","Suicune","Lugia","Ho-Oh","Celebi",
 "Regirock","Regice","Registeel","Latias","Latios","Kyogre","Groudon","Rayquaza","Jirachi","Deoxys",
 "Uxie","Mesprit","Azelf","Dialga","Palkia","Heatran","Regigigas","Giratina","Cresselia",
 "Phione","Manaphy","Darkrai","Shaymin","Arceus",
 "Victini","Cobalion","Terrakion","Virizion","Tornadus","Thundurus","Reshiram","Zekrom",
 "Landorus","Kyurem","Keldeo","Meloetta","Genesect",
 "Xerneas","Yveltal","Zygarde","Diancie","Hoopa","Volcanion",
 "Tapu Koko","Tapu Lele","Tapu Bulu","Tapu Fini","Cosmog","Cosmoem","Solgaleo","Lunala",
 "Necrozma","Magearna","Marshadow","Zeraora","Meltan","Melmetal",
 "Type: Null","Silvally","Nihilego","Buzzwole","Pheromosa","Xurkitree","Celesteela",
 "Kartana","Guzzlord","Poipole","Naganadel","Stakataka","Blacephalon",
 "Zacian","Zamazenta","Eternatus","Kubfu","Urshifu","Regieleki","Regidrago","Glastrier",
 "Spectrier","Calyrex","Zarude","Enamorus",
 "Wo-Chien","Chien-Pao","Ting-Lu","Chi-Yu","Koraidon","Miraidon","Walking Wake","Iron Leaves",
 "Gouging Fire","Raging Bolt","Iron Boulder","Iron Crown","Okidogi","Munkidori","Fezandipiti",
 "Ogerpon","Terapagos","Pecharunt",
 # exact ROM (hand-abbreviated) spellings
 "WalkinWake","GouginFire","IronBouldr","Fezandipti","Blacphalon","Type? Null","IronCrown",
}
LEG_NORM = {norm(x) for x in LEG_MYTH}
def is_legendary(name): return norm(name) in LEG_NORM

def valid_species(rom):
    out=[]
    for i in range(1, N):
        nm=spname(rom,i)
        if not nm or nm.startswith("?"): continue
        if stats(rom,i)["bst"]==0: continue
        out.append(i)
    return out

def water_type_id(rom):
    for ti in range(25):
        if type_name(rom,ti).upper().startswith("WATER"): return ti
    return 11

def base_lines(rom):
    """Return list of dicts for each non-legendary base-form line: idx,name,bst,t1,t2."""
    valids = valid_species(rom); vset=set(valids)
    targets=set()
    for i in valids:
        for (m,arg,tgt,val) in evolutions(rom,i):
            if is_true_evo_method(m) and tgt in vset:
                targets.add(tgt)
    lowest={}
    for i in valids:
        n=norm(spname(rom,i))
        if n not in lowest: lowest[n]=i
    lines=[]
    for i in valids:
        nm=spname(rom,i)
        if i in targets: continue
        if lowest[norm(nm)]!=i: continue
        if is_legendary(nm): continue
        if nm.startswith("Unown ") or nm.startswith("Unown-"): continue  # keep only base "Unown"
        st=stats(rom,i)
        lines.append(dict(idx=i,name=nm,bst=st["bst"],t1=st["t1"],t2=st["t2"]))
    return lines
