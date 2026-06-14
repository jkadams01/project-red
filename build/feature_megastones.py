"""Scatter Mega Stones across Kanto as overworld item balls for the player to grab.

Repoints a geographic spread of EXISTING low-value item balls (potions, X-items, repels, etc.)
to a freshly written "find item" script that gives a Mega Stone instead. This reuses each ball's
working pickup flag (so it vanishes once collected) and never touches TMs / Rare Candy / key items.
Stones are handed out roughly in story order: starter & Gen-1 megas early, pseudo-legends late."""
import mapinfo, feature_wild

# items we are willing to overwrite for a Mega Stone (consumables + stat boosters / sellables).
# TMs, Rare Candy, evolution stones, Max Revive and key items are deliberately NOT here.
LOW_VALUE = {"Potion","Super Potion","Hyper Potion","Antidote","Paralyz Heal","Burn Heal",
 "Awakening","Ice Heal","Full Heal","X Attack","X Defend","X Speed","X Sp. Atk","X Sp. Def",
 "X Accuracy","Dire Hit","Guard Spec","Guard Spec.","Ether","Elixir","Max Ether","Max Elixir",
 "Repel","Super Repel","Max Repel","Escape Rope","Pok? Ball","Poke Ball","Great Ball","Ultra Ball",
 "Stardust","Star Piece","Lucky Punch","Fresh Water","Soda Pop","Lemonade","Revive",
 "Calcium","Protein","Iron","Carbos","Zinc","HP Up","PP Up","Nugget"}

# story-ordered map priority (lower = earlier). Section names as they appear in data.maps.names.
MAP_ORDER = ["VIRIDIAN CITY","VIRIDIAN FOREST","ROUTE 2","ROUTE 3","MT. MOON","ROUTE 4","CERULEAN CITY",
 "ROUTE 24","ROUTE 25","ROUTE 5","ROUTE 6","ROUTE 9","ROUTE 10","ROCK TUNNEL","ROUTE 8","LAVENDER TOWN",
 "POK?MON TOWER","S.S. ANNE","VERMILION CITY","ROUTE 11","DIGLETT","ROUTE 7","CELADON CITY","ROCKET HIDEOUT",
 "ROUTE 16","ROUTE 17","ROUTE 18","ROUTE 12","ROUTE 13","SAFFRON CITY","SILPH CO.","POWER PLANT",
 "FUCHSIA CITY","ROUTE 15","ROUTE 14","SEAFOAM","POK?MON MANSION","CINNABAR","ROUTE 21","ROUTE 23",
 "VICTORY ROAD"]
def map_rank(nm):
    u=nm.upper()
    for i,k in enumerate(MAP_ORDER):
        ki=u.find(k)
        if ki>=0:
            end=ki+len(k)
            if end<len(u) and u[end].isdigit(): continue   # 'ROUTE 2' must not match 'ROUTE 22'
            return i
    return 999

MEGA_RING=353
import struct
def give_player_mega_ring(rom):
    """Put the Mega Ring (key item required to Mega Evolve) in the player's new-game bedroom PC,
    so it's guaranteed from minute one. Relocates the tiny PC-item table and repoints its single ref."""
    a=rom.tables["scripts.newgame.pc.item"]["addr"]
    entries=[]; k=0
    while k<=20:
        it=rom.u16(a+k*4); ct=rom.u16(a+k*4+2)
        if it==0 and ct==0: break
        entries.append((it,ct)); k+=1
    if any(it==MEGA_RING for it,ct in entries): return "already"
    entries.append((MEGA_RING,1))
    blob=bytearray()
    for it,ct in entries: blob+=struct.pack("<HH",it,ct)
    blob+=struct.pack("<HH",0,0)
    off=rom.alloc(len(blob)); rom.data[off:off+len(blob)]=blob
    pat=(a+0x08000000).to_bytes(4,"little")
    refs=[]; i=0
    while True:
        j=rom.data.find(pat,i)
        if j<0: break
        refs.append(j); i=j+1
    if len(refs)!=1:    # safety: a wrong repoint would leave the player unable to Mega Evolve at all
        raise RuntimeError("PC-item table has %d refs (expected 1); refusing to ship without Mega Ring"%len(refs))
    rom.wptr(refs[0], off)
    return "PC now has Potion + Mega Ring (ref @0x%X -> 0x%X)"%(refs[0],off)

# Mega Stones to scatter (non-legendary mons only), in PRIORITY order (placed first if balls run out):
# Gen-1 megas -> boss-held cross-gen megas -> strong/iconic -> niche (cut last).
STONES = [
 # Gen-1 (early)
 ("Venusaurite",533),("CharzarditeX",534),("CharzarditeY",535),("Blastoisnite",536),
 ("Beedrillite",537),("Pidgeotite",538),("Pinsirite",543),("Kangaskanite",542),
 ("Aerodactlite",545),("Gyaradosite",544),("Alakazite",539),("Slowbronite",540),("Gengarite",541),
 # boss-held cross-gen (so the player can field what the bosses do)
 ("Manectite",562),("Garchompite",574),("Glalitite",568),("Lucarionite",575),("Salamencite",569),
 # strong / iconic
 ("Tyranitarite",553),("Metagrossite",570),("Gardevoirite",557),("Scizorite",550),("Heracronite",551),
 ("Houndoomnite",552),("Mawilite",559),("Aggronite",560),("Absolite",567),("Sharpedonite",563),
 ("Medichamite",561),("Ampharosite",548),("Steelixite",549),("Sceptilite",554),("Blazikenite",555),
 ("Swampertite",556),("Abomasite",576),
 # niche (cut first if item balls run short)
 ("Cameruptite",564),("Altarianite",565),("Banettite",566),("Sablenite",558),
 ("Galladite",577),("Lopunnite",573),("Audinite",578),
]

def bank_mapcount(rom,b):
    BA=mapinfo.banks_addr(rom); p0=rom.ptr(BA+b*4); p1=rom.ptr(BA+(b+1)*4)
    if p0 is None: return 0
    if p1 is None or p1<=p0 or (p1-p0)//4>120: return 60
    return (p1-p0)//4

def itemballs(rom,b,m):
    h=mapinfo.header(rom,b,m)
    if h is None: return []
    ev=rom.ptr(h+4)
    if not ev: return []
    oc=rom.u8(ev); op=rom.ptr(ev+4); out=[]
    if not op: return []
    for i in range(oc):
        o=op+i*0x18
        if rom.u8(o+1)!=0x5C: continue
        sc=rom.ptr(o+0x10)
        if sc and rom.u8(sc)==0x1A and rom.u16(sc+1)==0x8000:
            out.append((o, rom.u16(sc+3)))   # (object offset, current item id)
    return out

def write_stone_script(rom, item):
    code=bytes([0x1A,0x00,0x80, item&0xFF,(item>>8)&0xFF,
                0x1A,0x01,0x80, 0x01,0x00, 0x09,0x01, 0x02])
    off=rom.alloc(len(code)); rom.data[off:off+len(code)]=code
    return off

def apply(rom, verbose=True):
    IST=rom.tables["data.items.stats"]["addr"]
    def itname(i): return rom.read_name(IST+i*44,14)
    # gather candidate low-value balls in pre-league Kanto, with story rank
    cands=[]
    for b in range(43):
        for m in range(bank_mapcount(rom,b)):
            nm=mapinfo.map_name(rom,b,m)
            if nm=="?" or not feature_wild.is_preleague(nm): continue
            if map_rank(nm)==999: continue          # only the curated story maps
            for o,item in itemballs(rom,b,m):
                if 533<=item<=579: continue          # already a stone
                if rom.u16(o+0x14)==0: continue       # ball has no pickup flag -> would never vanish; skip
                if itname(item) in LOW_VALUE:
                    cands.append(dict(rank=map_rank(nm),nm=nm,obj=o,olditem=item))
    # order by story rank, cap per-map for spread, then assign stones in order
    cands.sort(key=lambda c:(c["rank"], c["obj"]))
    percap={}; chosen=[]
    for c in cands:
        if percap.get(c["nm"],0)>=6: continue       # cap per map for geographic spread
        percap[c["nm"]]=percap.get(c["nm"],0)+1
        chosen.append(c)
        if len(chosen)>=len(STONES): break
    placed=[]
    for c,(sname,sid) in zip(chosen, STONES):
        off=write_stone_script(rom, sid)
        rom.wptr(c["obj"]+0x10, off)
        placed.append((c["nm"], sname))
    unplaced=[s for s,_ in STONES[len(placed):]]
    ring = give_player_mega_ring(rom)
    if verbose:
        print("[megastones] Mega Ring (player) -> %s" % ring)
        print("[megastones] scattered %d/%d Mega Stones across %d locations%s"
              % (len(placed), len(STONES), len(set(p[0] for p in placed)),
                 (" (unplaced: %s)"%", ".join(unplaced) if unplaced else "")))
        for nm in MAP_ORDER:
            here=[s for loc,s in placed if loc.upper().find(nm)>=0 or nm in loc.upper()]
            if here: print("   %-16s %s"%(nm, ", ".join(here)))
    return dict(placed=placed, unplaced=unplaced)

if __name__=="__main__":
    import romlib
    apply(romlib.Rom())
