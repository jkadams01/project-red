import romlib, mapinfo
rom=romlib.Rom()  # built output (current grass placement)

def analyze(b,m,name):
    lay=mapinfo.layout(rom,b,m); W,H=lay["width"],lay["height"]
    # locate tall-grass patch (metatile 13) and histogram walkable metatiles
    grass=[]; hist={}
    for y in range(H):
        for x in range(W):
            v=rom.u16(lay["blockmap"]+(y*W+x)*2); mt=v&0x3FF; col=(v>>10)&0x3
            bh=mapinfo.behavior(rom,lay,mt)
            if mt==mapinfo.GRASS_METATILE: grass.append((x,y))
            if col==0 and bh==0x00:
                hist[mt]=hist.get(mt,0)+1
    print("\n=== %s (%dx%d) ==="%(name,W,H))
    if grass:
        xs=[g[0] for g in grass]; ys=[g[1] for g in grass]
        print("  grass patch: x %d..%d  y %d..%d (top-left=%d,%d)"%(min(xs),max(xs),min(ys),max(ys),min(xs),min(ys)))
    print("  top walkable(normal) metatiles by count:",
          sorted(hist.items(),key=lambda kv:-kv[1])[:8])
    # show the metatiles immediately around the patch (what did we plant ON / next to)
    if grass:
        x0,y0=min(xs),min(ys)
        print("  metatiles in a window around the patch:")
        for y in range(max(0,y0-1), min(H,max(ys)+2)):
            row=""
            for x in range(max(0,x0-2), min(W,max(xs)+3)):
                v=rom.u16(lay["blockmap"]+(y*W+x)*2); mt=v&0x3FF; col=(v>>10)&0x3
                if mt==mapinfo.GRASS_METATILE: row+="[GG]"
                elif col!=0: row+=" ## "
                else: row+="%4d"%mt
            print("   ",row)

for nm,b,m in [("PEWTER CITY",3,2),("VIRIDIAN CITY",3,1),("CELADON CITY",3,6),("PALLET TOWN",3,0)]:
    analyze(b,m,nm)
