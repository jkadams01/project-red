import romlib, json, os
rom = romlib.Rom()
names_addr = rom.tables["data.pokemon.names"]["addr"]
NAME_W = 11
N = 1440

# Build index<->name
idx2name = {}
for i in range(N):
    nm = rom.read_name(names_addr + i*NAME_W, NAME_W)
    idx2name[i] = nm
# dump to file
with open("species_names.txt","w",encoding="utf-8") as f:
    for i in range(N):
        f.write("%4d\t%s\n" % (i, idx2name[i]))
print("dumped species_names.txt")

# ---- Decode evolution table for known species to confirm stride=128, 16 slots of 8 bytes ----
evo_addr = rom.tables["data.pokemon.evolutions"]["addr"]
STRIDE = 128
def dump_evo(i):
    base = evo_addr + i*STRIDE
    slots = []
    for s in range(16):
        o = base + s*8
        method = rom.u16(o)
        arg    = rom.u16(o+2)
        species= rom.u16(o+4)
        value  = rom.u16(o+6)
        if method != 0 or species != 0:
            slots.append((method, arg, species, idx2name.get(species,"?"), value))
    return slots

for i,label in [(1,"Bulbasaur"),(4,"Charmander"),(133,"Eevee"),(25,"Pikachu"),(151,"Mew")]:
    print("evo[%d %s]:"%(i,label), dump_evo(i))

# Determine stats element stride empirically: find by reading two species and locating known catchRate.
# Instead, read stats table format-derived size:
stats_addr = rom.tables["data.pokemon.stats"]["addr"]
# Bulbasaur base stats are 45/49/49/45/65/65. Search stride by checking index1 matches.
def stats_at(stride, i):
    o = stats_addr + i*stride
    return rom.data[o:o+6].hex(), tuple(rom.data[o:o+6])
for stride in [28,30,32,36]:
    print("stride %d  idx1=%s idx4=%s" % (stride, stats_at(stride,1)[1], stats_at(stride,4)[1]))
