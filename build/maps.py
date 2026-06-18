import romlib
rom = romlib.Rom()
BANKS = rom.tables["data.maps.banks"]["addr"]
MNAMES = rom.tables["data.maps.names"]["addr"]   # [name<"">] pointers, indexed by section-88

def map_name_index_name(i):
    # data.maps.names entry i: pointer to string
    p = rom.ptr(MNAMES + i*4)
    if p is None: return "?"
    return rom.read_name(p, 20)

def map_header_ptr(bank, mp):
    mapsPtr = rom.ptr(BANKS + bank*4)
    if mapsPtr is None: return None
    hdr = rom.ptr(mapsPtr + mp*4)
    return hdr

def region_section(bank, mp):
    hdr = map_header_ptr(bank, mp)
    if hdr is None: return None
    # header offsets: layout(4) events(4) mapscripts(4) connections(4) music(2) layoutID(2) regionSectionID(1)
    return rom.u8(hdr + 20)

def map_label(bank, mp):
    sec = region_section(bank, mp)
    if sec is None: return "(no header)"
    nm = map_name_index_name(sec - 88) if sec >= 88 else "sec%d" % sec
    return "%s [sec=%d]" % (nm, sec)

if __name__ == "__main__":
    # sanity: bank 3 map 0
    for (b,m) in [(3,0),(3,1),(3,2),(3,4),(2,27),(1,0)]:
        print("bank %d map %d -> %s" % (b,m, map_label(b,m)))
    print("--- first 15 map names ---")
    for i in range(15):
        print("  names[%d] = %s" % (i, map_name_index_name(i)))
