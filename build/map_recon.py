import romlib, gamedata
rom = romlib.Rom('C:/Users/James/Documents/GitHub/project-red/Roms/UCDEP/Pokemon - FireRed Version (USA).gba')
BANKS = rom.tables["data.maps.banks"]["addr"]
MN = rom.tables["data.maps.names"]["addr"]
def hdr(b,m):
    mp=rom.ptr(BANKS+b*4); return rom.ptr(mp+m*4) if mp is not None else None
def secname(s):
    p=rom.ptr(MN+(s-88)*4); return rom.read_name(p,18) if p and s>=88 else '?'

NUM_PRIMARY = 0x280  # metatiles 0..0x27F primary, rest secondary

def layout_of(b,m):
    h=hdr(b,m)
    if h is None: return None
    lay=rom.ptr(h+0)
    if lay is None: return None
    return dict(
        h=h, lay=lay,
        width=rom.u32(lay+0), height=rom.u32(lay+4),
        blockmap=rom.ptr(lay+0x0C),
        bd1=rom.ptr(lay+0x10), bd2=rom.ptr(lay+0x14),
        sec=rom.u8(h+20),
    )
def attrs_ptr(bd):  # blockdata struct: attributes pointer at +0x14
    return rom.ptr(bd+0x14) if bd is not None else None

def behavior(lay, metatile):
    """metatile behavior byte for a given metatile id, using primary/secondary attributes."""
    if metatile < NUM_PRIMARY:
        ap = attrs_ptr(lay["bd1"]); idx = metatile
    else:
        ap = attrs_ptr(lay["bd2"]); idx = metatile - NUM_PRIMARY
    if ap is None: return None
    # FRLG metatile attributes are u32 each; behavior is low byte (try u32)
    return rom.u32(ap + idx*4) & 0xFF

def scan_blocks(lay):
    """yield (x,y,metatile,collision,elevation) for each block."""
    w,hh = lay["width"], lay["height"]; bm=lay["blockmap"]
    for y in range(hh):
        for x in range(w):
            v = rom.u16(bm + (y*w+x)*2)
            yield x,y, v & 0x3FF, (v>>10)&0x3, (v>>12)&0xF

# --- Validate on Route 1 (bank3 map19): should contain TALL_GRASS (behavior 0x02) ---
def _demo():
    for (b,m,label) in [(3,19,"ROUTE 1"),(3,1,"VIRIDIAN CITY"),(3,0,"PALLET TOWN"),(3,2,"PEWTER CITY")]:
        lay=layout_of(b,m)
        if not lay: print(label,"no layout"); continue
        grass_ids={}; behav_count={}
        for x,y,mt,col,el in scan_blocks(lay):
            bh=behavior(lay,mt)
            behav_count[bh]=behav_count.get(bh,0)+1
            if bh==0x02: grass_ids[mt]=grass_ids.get(mt,0)+1
        print("%-14s %dx%d  bd1=%s bd2=%s" % (label,lay["width"],lay["height"],
              hex(lay["bd1"]) if lay["bd1"] else None, hex(lay["bd2"]) if lay["bd2"] else None))
        print("   tall-grass(0x02) metatile ids & counts:", grass_ids)
        print("   top behaviors:", dict(sorted(behav_count.items(), key=lambda kv:-kv[1])[:6]))

if __name__ == "__main__":
    _demo()
