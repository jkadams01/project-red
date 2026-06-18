"""Rom-parameterized map layout / blockmap / metatile-behavior helpers."""
NUM_PRIMARY = 0x280          # metatiles 0..0x27F use primary tileset attrs, rest secondary
TALL_GRASS_BEHAVIOR = 0x02
GRASS_METATILE = 13          # tall-grass metatile id in the shared Kanto overworld tileset

def banks_addr(rom): return rom.tables["data.maps.banks"]["addr"]
def names_addr(rom): return rom.tables["data.maps.names"]["addr"]

def header(rom, b, m):
    mp = rom.ptr(banks_addr(rom) + b*4)
    return rom.ptr(mp + m*4) if mp is not None else None
def region_section(rom, b, m):
    h = header(rom, b, m); return rom.u8(h+20) if h is not None else None
def section_name(rom, sec):
    if sec is None or sec < 88: return "?"
    p = rom.ptr(names_addr(rom) + (sec-88)*4)
    return rom.read_name(p, 18) if p else "?"
def map_name(rom, b, m): return section_name(rom, region_section(rom, b, m))

def layout(rom, b, m):
    h = header(rom, b, m)
    if h is None: return None
    lay = rom.ptr(h+0)
    if lay is None: return None
    return dict(h=h, lay=lay, width=rom.u32(lay+0), height=rom.u32(lay+4),
                blockmap=rom.ptr(lay+0x0C), bd1=rom.ptr(lay+0x10), bd2=rom.ptr(lay+0x14),
                sec=rom.u8(h+20))

def _attrs_ptr(rom, bd): return rom.ptr(bd+0x14) if bd is not None else None
def behavior(rom, lay, metatile):
    if metatile < NUM_PRIMARY:
        ap = _attrs_ptr(rom, lay["bd1"]); idx = metatile
    else:
        ap = _attrs_ptr(rom, lay["bd2"]); idx = metatile - NUM_PRIMARY
    if ap is None: return None
    return rom.u32(ap + idx*4) & 0xFF

def block_at(rom, lay, x, y):
    v = rom.u16(lay["blockmap"] + (y*lay["width"]+x)*2)
    return v
def set_block_metatile(rom, lay, x, y, metatile):
    off = lay["blockmap"] + (y*lay["width"]+x)*2
    v = rom.u16(off)
    v = (v & ~0x3FF) | (metatile & 0x3FF)   # keep collision+elevation bits
    rom.wu16(off, v)
def iter_blocks(rom, lay):
    w, hh = lay["width"], lay["height"]; bm = lay["blockmap"]
    for y in range(hh):
        for x in range(w):
            v = rom.u16(bm + (y*w+x)*2)
            yield x, y, v & 0x3FF, (v >> 10) & 0x3, (v >> 12) & 0xF

def count_grass(rom, lay):
    return sum(1 for x,y,mt,c,e in iter_blocks(rom, lay) if behavior(rom, lay, mt) == TALL_GRASS_BEHAVIOR)

def read_events(rom, b, m):
    """Return (objects, warps, signposts) as lists of (x,y) tile coords."""
    h = header(rom, b, m)
    if h is None: return [], [], []
    ev = rom.ptr(h+4)
    if ev is None: return [], [], []
    oc, wc, sc, gc = rom.u8(ev), rom.u8(ev+1), rom.u8(ev+2), rom.u8(ev+3)
    op, wp, _spp, gp = rom.ptr(ev+4), rom.ptr(ev+8), rom.ptr(ev+12), rom.ptr(ev+16)
    objs, warps, signs = [], [], []
    if op:
        for i in range(min(oc,64)): objs.append((rom.u16(op+i*0x18+4), rom.u16(op+i*0x18+6)))
    if wp:
        for i in range(min(wc,64)): warps.append((rom.u16(wp+i*8+0), rom.u16(wp+i*8+2)))
    if gp:
        for i in range(min(gc,64)): signs.append((rom.u16(gp+i*0x0C+0), rom.u16(gp+i*0x0C+2)))
    return objs, warps, signs
