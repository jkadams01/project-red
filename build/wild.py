import romlib
rom = romlib.Rom()
names_addr = rom.tables["data.pokemon.names"]["addr"]
NAME_W = 11
def spname(i): return rom.read_name(names_addr + i*NAME_W, NAME_W)

WILD = rom.tables["data.pokemon.wild"]["addr"]
CATS = [("grass",12),("surf",5),("tree",5),("fish",10)]

def walk():
    """Yield dict per wild map entry with slot offsets."""
    a = WILD
    entries = []
    while True:
        bank = rom.u8(a); mp = rom.u8(a+1)
        if bank == 0xFF and mp == 0xFF:
            break
        e = {"addr":a, "bank":bank, "map":mp, "cats":{}}
        p = a + 4
        for name, nslots in CATS:
            ptr = rom.ptr(p)
            p += 4
            if ptr is None:
                e["cats"][name] = None
                continue
            # struct: rate (4 bytes incl pad), then list pointer (4 bytes)
            rate = rom.u8(ptr)
            listptr = rom.ptr(ptr+4)
            slots = []
            if listptr is not None:
                for s in range(nslots):
                    so = listptr + s*4
                    slots.append({"off":so, "lo":rom.u8(so), "hi":rom.u8(so+1), "sp":rom.u16(so+2)})
            e["cats"][name] = {"rate":rate, "slots":slots}
        entries.append(e)
        a += 20
    return entries

if __name__ == "__main__":
    entries = walk()
    print("wild entries:", len(entries))
    # validate: print first 6 entries
    for e in entries[:6]:
        print("entry bank=%d map=%d @0x%X" % (e["bank"], e["map"], e["addr"]))
        for name,_ in CATS:
            c = e["cats"][name]
            if not c:
                print("   %-5s none"%name); continue
            ss = ", ".join("%s(L%d-%d)"%(spname(s["sp"]), s["lo"], s["hi"]) for s in c["slots"][:4])
            print("   %-5s rate=%d: %s ..." % (name, c["rate"], ss))
    # totals
    tot = {name:0 for name,_ in CATS}
    banks = {}
    for e in entries:
        banks.setdefault((e["bank"]), 0)
        banks[e["bank"]] += 1
        for name,_ in CATS:
            c = e["cats"][name]
            if c: tot[name] += len(c["slots"])
    print("slot totals:", tot, "=> total slots:", sum(tot.values()))
    print("entries per bank:", dict(sorted(banks.items())))
