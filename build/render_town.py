"""Render a top-down schematic PNG of a town map: walkable ground / buildings / water / grass,
with warps (doors), object events (NPCs/signs) and the current tall-grass patch marked.
Pure-stdlib PNG writer (zlib) so no Pillow needed."""
import zlib, struct, binascii, os
import romlib, mapinfo

def write_png(path, w, h, rgb):
    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", binascii.crc32(typ+data) & 0xFFFFFFFF)
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        raw += rgb[y*w*3:(y+1)*w*3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)

WATER_BEHAVS = set(range(0x10,0x20)) | {0x21,0x22,0x23,0x24,0x2B,0x2C}  # rough FRLG water set

def read_events(rom, b, m):
    h = mapinfo.header(rom, b, m)
    ev = rom.ptr(h+4)
    if ev is None: return [], [], []
    oc, wc, _sc, gc = rom.u8(ev), rom.u8(ev+1), rom.u8(ev+2), rom.u8(ev+3)
    op, wp, _sp, gp = rom.ptr(ev+4), rom.ptr(ev+8), rom.ptr(ev+12), rom.ptr(ev+16)
    objs, warps, signs = [], [], []
    if op:
        for i in range(min(oc,64)): objs.append((rom.u16(op+i*0x18+4), rom.u16(op+i*0x18+6)))
    if wp:
        for i in range(min(wc,64)): warps.append((rom.u16(wp+i*8+0), rom.u16(wp+i*8+2)))
    if gp:
        for i in range(min(gc,64)): signs.append((rom.u16(gp+i*0x0C+0), rom.u16(gp+i*0x0C+2)))
    return objs, warps, signs

def classify_color(rom, lay, mt, col):
    bh = mapinfo.behavior(rom, lay, mt)
    if bh == 0x02: return (60, 200, 60)        # tall grass -> bright green
    if col != 0:
        if bh in WATER_BEHAVS: return (60, 90, 200)   # water-ish blocked
        return (70, 70, 78)                    # building / wall
    if bh in WATER_BEHAVS: return (90, 140, 230)       # walkable water (surf)
    if bh == 0x00: return (196, 184, 140)      # normal walkable ground
    return (150, 150, 165)                     # other walkable (paths, mats, ledges)

def render(rom, b, m, name, scale=11, out_dir="maps"):
    os.makedirs(out_dir, exist_ok=True)
    lay = mapinfo.layout(rom, b, m)
    W, H = lay["width"], lay["height"]
    objs, warps, signs = read_events(rom, b, m)
    px_w, px_h = W*scale, H*scale
    img = bytearray(px_w*px_h*3)
    def put(x, y, c):
        if 0<=x<px_w and 0<=y<px_h:
            o=(y*px_w+x)*3; img[o],img[o+1],img[o+2]=c
    # blocks
    for by in range(H):
        for bx in range(W):
            v = rom.u16(lay["blockmap"]+(by*W+bx)*2)
            c = classify_color(rom, lay, v&0x3FF, (v>>10)&0x3)
            for dy in range(scale):
                for dx in range(scale):
                    put(bx*scale+dx, by*scale+dy, c)
    # grid lines (faint)
    for by in range(H):
        for x in range(px_w): put(x, by*scale, (40,40,45))
    for bx in range(W):
        for y in range(px_h): put(bx*scale, y, (40,40,45))
    # markers: warps=red, signs=yellow, objects=orange (draw a centered square)
    def marker(tx, ty, c):
        cx, cy = tx*scale+scale//2, ty*scale+scale//2
        for dy in range(-3,4):
            for dx in range(-3,4):
                put(cx+dx, cy+dy, c)
    for (x,y) in warps: marker(x,y,(230,40,40))
    for (x,y) in signs: marker(x,y,(230,210,40))
    for (x,y) in objs:  marker(x,y,(235,140,30))
    path = os.path.join(out_dir, name.replace(" ","_").replace(".","").replace("'","")+".png")
    write_png(path, px_w, px_h, img)
    g = mapinfo.count_grass(rom, lay)
    print("  %-16s %2dx%-2d grass_tiles=%-3d warps=%d objs=%d -> %s" %
          (name, W, H, g, len(warps), len(objs), path))
    return path

TOWNS = [("VIRIDIAN CITY",3,1),("PEWTER CITY",3,2),("CERULEAN CITY",3,3),("LAVENDER TOWN",3,4),
         ("VERMILION CITY",3,5),("CELADON CITY",3,6),("SAFFRON CITY",3,10),("FUCHSIA CITY",3,7),
         ("CINNABAR ISLAND",3,8),("PALLET TOWN",3,0)]

if __name__ == "__main__":
    rom = romlib.Rom()   # built output (shows current grass patches)
    print("Legend: green=grass  tan=walkable ground  gray=building/wall  blue=water"
          "  red=warp  orange=NPC  yellow=sign")
    for nm,b,m in TOWNS:
        render(rom, b, m, nm)
