import romlib, map_recon as M
rom = M.rom
WILD = rom.tables["data.pokemon.wild"]["addr"]

# wild entries present (bank,map)
wild_entries=set(); a=WILD
while not (rom.u8(a)==0xFF and rom.u8(a+1)==0xFF):
    wild_entries.add((rom.u8(a),rom.u8(a+1))); a+=20
term=a
print("wild table: %d entries, terminator at 0x%X" % (len(wild_entries), term))
# space after terminator
free_after=0; p=term+2
while rom.u8(p)==0xFF: free_after+=1; p+=1
print("contiguous 0xFF after terminator: %d bytes (room for %d new 20-byte entries in place)" %
      (free_after, free_after//20))

# references to the wild table pointer 0x083C9CB8
target = (WILD+0x08000000).to_bytes(4,"little")
refs=[i for i in range(0,len(rom.data)-4,4) if rom.data[i:i+4]==target]
print("pointers to wild table (0x%08X):"%(WILD+0x08000000), [hex(r) for r in refs])

# Enumerate Kanto TOWN maps (section names that are cities/towns) across banks, with grass + wild-entry status
TOWN_SECTIONS = {88:"PALLET",89:"VIRIDIAN",90:"PEWTER",91:"CERULEAN",92:"LAVENDER",93:"VERMILION",
                 94:"CELADON",95:"FUCHSIA",96:"CINNABAR",97:"INDIGO",98:"SAFFRON"}
print("\n=== Kanto town maps ===")
seen=set()
for b in range(43):
    mp=rom.ptr(M.BANKS+b*4)
    if mp is None: continue
    for m in range(60):
        h=rom.ptr(mp+m*4)
        if h is None: break
        sec=rom.u8(h+20)
        if sec in TOWN_SECTIONS and (sec) not in seen:
            lay=M.layout_of(b,m)
            if not lay: continue
            grass=sum(1 for x,y,mt,col,el in M.scan_blocks(lay) if M.behavior(lay,mt)==0x02)
            print("  %-9s b%d.m%-2d %dx%d grass_tiles=%-4d wild_entry=%s primary_bd1=%s" % (
                TOWN_SECTIONS[sec], b, m, lay["width"], lay["height"], grass,
                (b,m) in wild_entries, hex(lay["bd1"])))
            seen.add(sec)
