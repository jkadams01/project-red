"""Add tall grass + wild-encounter tables to Kanto towns so they have catchable encounters.
- Adds a grass patch (metatile 13) to towns that lack grass tiles.
- Gives each town a 12-slot grass encounter table (placeholder species; themer fills them):
    * towns with an existing wild entry -> set the (currently null) grass pointer.
    * towns with no wild entry          -> repurpose a redundant duplicate Altering Cave entry.
"""
import mapinfo

# (name, bank, map, level_lo, level_hi). Story-ordered level ranges.
TOWNS = [
  ("VIRIDIAN CITY",3,1,3,5),("PEWTER CITY",3,2,4,7),("CERULEAN CITY",3,3,10,14),
  ("VERMILION CITY",3,5,14,18),("LAVENDER TOWN",3,4,16,20),("CELADON CITY",3,6,18,24),
  ("SAFFRON CITY",3,10,24,30),("FUCHSIA CITY",3,7,24,30),("CINNABAR ISLAND",3,8,32,40),
]
PATCH_W, PATCH_H, MARGIN = 3, 3, 2

def wild_entries(rom):
    WILD=rom.tables["data.pokemon.wild"]["addr"]; a=WILD; out=[]
    while not (rom.u8(a)==0xFF and rom.u8(a+1)==0xFF):
        out.append(a); a+=20
    return out, a

def find_patch(rom, lay, b, m, pw=PATCH_W, ph=PATCH_H, margin=MARGIN):
    """Pick a natural grass spot: a pw x ph block of plain walkable ground that is in OPEN space,
    clear of doors (warps) and NPCs/signs, and as close to a map corner (town outskirts) as possible."""
    W,H=lay["width"],lay["height"]
    objs,warps,signs=mapinfo.read_events(rom,b,m)
    blockers=warps+signs+objs
    def cell(x,y): v=rom.u16(lay["blockmap"]+(y*W+x)*2); return v&0x3FF,(v>>10)&0x3
    def normal_ground(x,y):
        if not(0<=x<W and 0<=y<H): return False
        mt,col=cell(x,y); return col==0 and mapinfo.behavior(rom,lay,mt)==0x00
    def walkable(x,y):
        return 0<=x<W and 0<=y<H and cell(x,y)[1]==0
    corners=[(margin,margin),(W-1-margin,margin),(margin,H-1-margin),(W-1-margin,H-1-margin)]
    best=None; bestscore=-1e18
    for y in range(margin, H-margin-ph+1):
        for x in range(margin, W-margin-pw+1):
            cells=[(x+dx,y+dy) for dy in range(ph) for dx in range(pw)]
            if not all(normal_ground(cx,cy) for cx,cy in cells): continue
            # the 1-tile frame around the patch must be mostly OPEN (not jammed in a nook/corridor)
            frame=[(fx,fy) for fy in range(y-1,y+ph+1) for fx in range(x-1,x+pw+1)
                   if (fx,fy) not in cells]
            open_frac=sum(walkable(fx,fy) for fx,fy in frame)/max(1,len(frame))
            if open_frac < 0.72: continue
            # clearance from doors / NPCs / signs (Chebyshev)
            def mind(pts):
                return 99 if not pts else min(max(abs(cx-px),abs(cy-py)) for cx,cy in cells for px,py in pts)
            if mind(warps) < 3 or mind(objs) < 2 or mind(signs) < 2: continue
            ccx,ccy=x+pw/2.0,y+ph/2.0
            cdist=min(max(abs(ccx-cx2),abs(ccy-cy2)) for cx2,cy2 in corners)
            score = -cdist*3 + mind(blockers)   # closest to a corner, with a clearance tiebreak
            if score>bestscore: bestscore=score; best=(x,y)
    if best is None:   # relax the frame/clearance requirements if nothing qualified
        for y in range(margin, H-margin-ph+1):
            for x in range(margin, W-margin-pw+1):
                if all(normal_ground(x+dx,y+dy) for dy in range(ph) for dx in range(pw)):
                    return x,y
    return best

def make_grass_table(rom, lo, hi, rate=22):
    slots=rom.alloc(12*4)
    for s in range(12):
        o=slots+s*4
        rom.wu8(o,lo); rom.wu8(o+1,hi); rom.wu16(o+2,0)   # species filled by themer
    info=rom.alloc(8)
    rom.wu8(info,rate); rom.wu8(info+1,0); rom.wu8(info+2,0); rom.wu8(info+3,0)
    rom.wptr(info+4, slots)
    return info

def apply(rom, verbose=True):
    entries, term = wild_entries(rom)
    by_bm={(rom.u8(a),rom.u8(a+1)):a for a in entries}   # last entry wins (fine)
    # redundant Altering Cave (1,122) duplicates available to repurpose (skip the FIRST one)
    alt=[a for a in entries if (rom.u8(a),rom.u8(a+1))==(1,122)]
    spare=alt[1:]            # keep alt[0] for Altering Cave itself
    tiles_added=[]; tables_added=[]; new_entries=[]
    for (name,b,m,lo,hi) in TOWNS:
        lay=mapinfo.layout(rom,b,m)
        # 1) add grass tiles if none
        if lay and mapinfo.count_grass(rom,lay)==0:
            pos=find_patch(rom,lay,b,m)
            if pos:
                x0,y0=pos
                for dy in range(PATCH_H):
                    for dx in range(PATCH_W):
                        mapinfo.set_block_metatile(rom,lay,x0+dx,y0+dy,mapinfo.GRASS_METATILE)
                tiles_added.append((name,x0,y0))
        # 2) ensure grass encounter table
        entry=by_bm.get((b,m))
        info=make_grass_table(rom,lo,hi)
        if entry is not None:
            if rom.ptr(entry+4) is None:        # null grass pointer -> set it
                rom.wptr(entry+4, info)
                tables_added.append((name,"existing"))
            else:
                tables_added.append((name,"already-had-grass"))
        else:
            if not spare:
                if verbose: print("[towngrass] no spare entry for",name); continue
            e=spare.pop()
            rom.wu8(e,b); rom.wu8(e+1,m); rom.wu16(e+2,0)  # bank,map,unused
            rom.wptr(e+4, info)                              # grass
            rom.wptr(e+8, 0); rom.wptr(e+12,0); rom.wptr(e+16,0)  # no surf/tree/fish
            new_entries.append((name,b,m))
    if verbose:
        print("[towngrass] grass patches added to %d towns: %s" % (len(tiles_added),[t[0] for t in tiles_added]))
        print("[towngrass] grass tables: %d (new repurposed entries: %s)" %
              (len(tables_added)+len(new_entries),[n[0] for n in new_entries]))
    return dict(tiles=tiles_added, tables=tables_added, new=new_entries)
