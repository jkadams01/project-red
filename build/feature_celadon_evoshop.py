"""Adds an NPC just outside the Celadon City Pokemon Center who runs a Poke Mart selling EVERY
evolution item in the game for 1000 each.

WHAT COUNTS AS AN "EVOLUTION ITEM": data-driven from the ROM's own evolution table. We collect the
`arg` (item id) of every evolution that uses an ITEM-based method -- trade-with-item (6), use-item /
stone (7), level-up-holding-item day/night (24, 25) and the use-item-under-condition variants (34, 36,
39). That yields the 51 items that actually trigger a PERMANENT evolution in this UCDEP base (the 10
evolution stones, the trade items King's Rock / Metal Coat / Dragon Scale / Up-Grade / Dubious Disc /
Protector / Electirizer / Magmarizer / Prism Scale / Sachet / Whipped Dream / DeepSea Tooth+Scale /
Gimmighoul Coin, the Link Cable that completes all 14 trade evolutions solo, Razor Claw/Fang, Oval Stone,
Reaper Cloth, the 7 Milcery sweets, the apples/pots, Galarica Cuff/Wreath, and the Gen-9 items this hack
remaps onto Charcadet/Applin/Poltchageist/Duraludon/Bisharp/Meltan). MEGA stones (evolution "method" 254)
are deliberately EXCLUDED -- mega evolution is temporary and feature_megastones.py already scatters those.

HOW IT WORKS:
  - Each evo item's buy price (u16 @ items.stats + id*44 + 0x10) is set to 1000. A Poke Mart charges the
    item's own price, so this is what makes them 1000 each. SIDE-EFFECT: this is the single global price
    field, so it also lowers these items in any other mart and halves their sell-back to 500.
  - A product list (u16 LE ids + 0x0000 terminator) and a small interaction script are written to free
    space: lock; faceplayer; msgbox greeting; pokemart <list>; release; end. (pokemart = opcode 0x86 +
    a 4-byte pointer; the greeting/list pointers are patched after their allocs.)
  - A 16th object event is appended to Celadon City (bank 3, map 6). The map's 15-object array
    has no slack (it abuts the warp array), so it is relocated via rom.alloc() -- the 15 existing objects
    are copied byte-for-byte, the new NPC is appended, events+4 is repointed and the u8 count @events+0
    is bumped 15 -> 16. The NPC stands at (33,22), one tile SW of the PC door (34,21), on the open plaza;
    it deliberately avoids the warp-exit landing tile (34,22) so it never blocks leaving the PC.

NOTE: edits a city map + adds an object event -> MUST be mGBA-playtested per CLAUDE.md.
"""
import romlib, mapinfo, gamedata

CELADON_BANK, CELADON_MAP = 3, 6
ITEM_STRIDE = 44
PRICE_OFF = 0x10
SHOP_PRICE = 1000

# Evolution methods whose `arg` field is an ITEM id (verified against this UCDEP base: every resulting id
# resolves to a real item that a real species evolves with). Excludes mega (254) and the form method (253).
ITEM_EVO_METHODS = {6, 7, 24, 25, 34, 36, 39}

# New NPC outside the Celadon PC (struct fields verified by decoding the 15 existing Celadon objects).
NPC_X, NPC_Y = 33, 22          # one tile SW of the PC door (34,21); avoids the (34,22) warp-exit tile
NPC_GFX = 27                   # a clerk/townsperson overworld sprite
NPC_ELEV = 3
NPC_MOVETYPE = 7               # look-around-in-place (movementRange 0 = never walks)
NPC_FLAG = 0x0000              # always visible, never gated

GREETING = "Evolution items for sale!\nEvery one is 1000!"


def evo_item_ids(rom):
    """All distinct item ids used by item-based evolution methods, sorted. Resolves names to skip blanks."""
    IST = rom.tables["data.items.stats"]["addr"]
    ids = set()
    for i in range(1, gamedata.N):
        nm = gamedata.spname(rom, i)
        if not nm or nm.startswith("?"):
            continue
        for (m, arg, tgt, val) in gamedata.evolutions(rom, i):
            if m in ITEM_EVO_METHODS and 0 < arg < 900:
                if rom.read_name(IST + arg * ITEM_STRIDE, 14).strip():
                    ids.add(arg)
    return sorted(ids)


def encode_text(s):
    """FireRed PCS-encode a string ('\\n' -> 0xFE newline), 0xFF terminated. Chars must be in RCHARMAP."""
    out = bytearray()
    for ch in s:
        if ch == "\n":
            out.append(0xFE); continue
        out.append(romlib.RCHARMAP.get(ch, 0x00))   # unmapped -> space (0x00)
    out.append(0xFF)
    return bytes(out)


def apply(rom, verbose=True):
    IST = rom.tables["data.items.stats"]["addr"]
    ids = evo_item_ids(rom)

    # 1) set every evo item's buy price to 1000
    for iid in ids:
        rom.wu16(IST + iid * ITEM_STRIDE + PRICE_OFF, SHOP_PRICE)

    # 2) Poke Mart product list: u16 LE ids + 0x0000 terminator
    list_off = rom.alloc((len(ids) + 1) * 2)
    for k, iid in enumerate(ids):
        rom.wu16(list_off + k * 2, iid)
    rom.wu16(list_off + len(ids) * 2, 0)

    # 3) greeting text
    g = encode_text(GREETING)
    greet_off = rom.alloc(len(g))
    rom.data[greet_off:greet_off + len(g)] = g

    # 4) interaction script: lock; faceplayer; loadpointer 0,<greet>; callstd 4 (msgbox); closemessage;
    #    pokemart <list>; release; end. greet ptr @+0x04, list ptr @+0x0C.
    scr = bytearray([0x6A, 0x5A, 0x0F, 0x00, 0, 0, 0, 0, 0x09, 0x04, 0x68,
                     0x86, 0, 0, 0, 0, 0x6C, 0x02])
    scr_off = rom.alloc(len(scr))
    rom.data[scr_off:scr_off + len(scr)] = scr
    rom.wptr(scr_off + 0x04, greet_off)
    rom.wptr(scr_off + 0x0C, list_off)

    # 5) relocate+grow Celadon(3,6)'s object-event array and append the NPC
    ev = rom.ptr(mapinfo.header(rom, CELADON_BANK, CELADON_MAP) + 4)
    count = rom.u8(ev + 0)
    old_arr = rom.ptr(ev + 4)
    assert old_arr is not None, "Celadon object array pointer is null"
    new_arr = rom.alloc((count + 1) * 0x18)
    rom.data[new_arr:new_arr + count * 0x18] = rom.data[old_arr:old_arr + count * 0x18]
    # next free localId = max existing + 1
    local_id = max(rom.u8(new_arr + k * 0x18) for k in range(count)) + 1
    e = new_arr + count * 0x18
    for j in range(0x18):            # zero the new 24-byte entry first
        rom.wu8(e + j, 0)
    rom.wu8(e + 0x00, local_id)
    rom.wu8(e + 0x01, NPC_GFX)
    rom.wu16(e + 0x04, NPC_X)
    rom.wu16(e + 0x06, NPC_Y)
    rom.wu8(e + 0x08, NPC_ELEV)
    rom.wu8(e + 0x09, NPC_MOVETYPE)
    # +0x0A movementRange, +0x0C trainerType, +0x0E sightRadius all 0 (already zeroed)
    rom.wptr(e + 0x10, scr_off)      # scriptPtr -> shop script
    rom.wu16(e + 0x14, NPC_FLAG)
    rom.wptr(ev + 0x04, new_arr)     # repoint object array
    rom.wu8(ev + 0x00, count + 1)    # bump object count 15 -> 16

    if verbose:
        names = [rom.read_name(IST + i * ITEM_STRIDE, 14) for i in ids]
        print("[celadon_evoshop] %d evo items @%d each; NPC localId=%d gfx=%d @(%d,%d); "
              "objects %d->%d (array 0x%X->0x%X); script@0x%X list@0x%X"
              % (len(ids), SHOP_PRICE, local_id, NPC_GFX, NPC_X, NPC_Y, count, count + 1,
                 rom.to_gba(old_arr), rom.to_gba(new_arr), rom.to_gba(scr_off), rom.to_gba(list_off)))
        print("           items:", ", ".join(names))
    return dict(items=ids, npc=(NPC_X, NPC_Y), script=scr_off, list=list_off, count=count + 1)


if __name__ == "__main__":
    # standalone dry-run against the pristine UCDEP base (the output ROM's free region is already consumed)
    base = r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba"
    r = romlib.Rom.__new__(romlib.Rom)
    r.path = base
    with open(base, "rb") as f:
        r.data = bytearray(f.read())
    r.tables = romlib.parse_toml_anchors(base[:-4] + ".toml")
    r._free = romlib.Rom.FREE_BASE
    info = apply(r)
    print("dry-run OK: %d items, NPC@%s" % (len(info["items"]), info["npc"]))
