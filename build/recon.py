import romlib
rom = romlib.Rom()

# ---- species names: confirm indexing & count ----
names_addr = rom.tables["data.pokemon.names"]["addr"]
NAME_W = 11  # from format [name""11]1440
print("=== species name spot-check (index = National Dex #?) ===")
for idx in [0,1,4,6,9,131,143,150,151,152,251,252,386,387,494,495,649,650,721,722,809,810,898,899,905,906,1000,1008,1010,1017,1024,1025,1026]:
    nm = rom.read_name(names_addr + idx*NAME_W, NAME_W)
    print("  %4d: %s" % (idx, nm))

# count "real" species (non-blank, non '?')
count = 0
for i in range(1440):
    nm = rom.read_name(names_addr + i*NAME_W, NAME_W)
    if nm.strip() and not nm.startswith("?"):
        count = i
print("last non-empty species index:", count)

print()
print("=== trainer class names (107) ===")
tc_addr = rom.tables["data.trainers.classes.names"]["addr"]
for i in range(107):
    nm = rom.read_name(tc_addr + i*13, 13)
    if nm.strip():
        print("  %3d: %s" % (i, nm))
