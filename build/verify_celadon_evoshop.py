"""Read-back verification of the Celadon evolution-item shop (run after `py build.py`)."""
import romlib, mapinfo, feature_celadon_evoshop as F

rom = romlib.Rom()
base = romlib.Rom(r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba")
IST = rom.tables["data.items.stats"]["addr"]

ev = rom.ptr(mapinfo.header(rom, 3, 6) + 4)
count = rom.u8(ev + 0); arr = rom.ptr(ev + 4)
bev = base.ptr(mapinfo.header(base, 3, 6) + 4)
bcount = base.u8(bev + 0); barr = base.ptr(bev + 4)

assert count == bcount + 1 == 16, "object count %d (expected 16)" % count
print("object count %d -> %d  OK" % (bcount, count))

# The 15 existing objects must be relocated FAITHFULLY. (We compare against the orphaned original array
# still sitting at the base array address in the built ROM -- NOT against base, because an earlier feature
# (feature_megastones) legitimately repoints one Celadon item-ball object's script before we copy it.)
orig = barr   # 0x3B565C, now-orphaned original array location inside the built ROM
for i in range(bcount):
    a = bytes(rom.data[arr + i*0x18: arr + i*0x18 + 0x18])
    o = bytes(rom.data[orig + i*0x18: orig + i*0x18 + 0x18])
    assert a == o, "object %d not faithfully relocated!" % i
diffs = sum(bytes(rom.data[orig+i*0x18:orig+i*0x18+0x18]) != bytes(base.data[barr+i*0x18:barr+i*0x18+0x18]) for i in range(bcount))
print("15 existing objects relocated faithfully OK (%d were already modified by earlier features)" % diffs)

# warp array untouched (the old object array abutted it -> make sure relocation didn't corrupt it)
nwarp = rom.u8(ev + 1); pwarp = rom.ptr(ev + 8); bpwarp = base.ptr(bev + 8)
assert pwarp == bpwarp, "warp pointer changed!"
assert bytes(rom.data[pwarp:pwarp + nwarp*8]) == bytes(base.data[bpwarp:bpwarp + nwarp*8]), "warp array changed!"
print("warp array (%d warps) byte-identical to base  OK" % nwarp)

# new NPC
e = arr + bcount * 0x18
lid = rom.u8(e); gfx = rom.u8(e+1); x = rom.u16(e+4); y = rom.u16(e+6)
elev = rom.u8(e+8); mv = rom.u8(e+9); scr = rom.ptr(e+0x10); flag = rom.u16(e+0x14)
assert (x, y) == (F.NPC_X, F.NPC_Y), "NPC pos %s" % ((x, y),)
assert gfx == F.NPC_GFX and elev == F.NPC_ELEV and mv == F.NPC_MOVETYPE and flag == F.NPC_FLAG, "NPC field mismatch"
assert scr, "NPC has no script pointer"
print("new NPC localId=%d gfx=%d @(%d,%d) elev=%d mv=%d flag=0x%04X scr=0x%X  OK"
      % (lid, gfx, x, y, elev, mv, flag, rom.to_gba(scr)))

# decode the shop script
b = rom.data
assert b[scr] == 0x6A and b[scr+1] == 0x5A, "script must start lock;faceplayer"
assert b[scr+2] == 0x0F, "expected loadpointer"
greet = rom.ptr(scr+4)
assert b[scr+8] == 0x09 and b[scr+9] == 0x04, "expected callstd 4 (msgbox)"
assert b[scr+10] == 0x68, "expected closemessage"
assert b[scr+11] == 0x86, "expected pokemart opcode 0x86"
listp = rom.ptr(scr+0x0C)
assert b[scr+0x10] == 0x6C and b[scr+0x11] == 0x02, "script must end release;end"
print("script OK: lock;faceplayer;msgbox(0x%X);closemessage;pokemart(0x%X);release;end"
      % (rom.to_gba(greet), rom.to_gba(listp)))

# greeting text decodes
txt = []
p = greet
for _ in range(80):
    c = b[p]
    if c == 0xFF: break
    txt.append("\\n" if c == 0xFE else romlib.CHARMAP.get(c, "?")); p += 1
print("greeting: '%s'" % "".join(txt))

# mart list = the 51 evo ids + 0x0000 terminator
ids = F.evo_item_ids(rom)
for k, iid in enumerate(ids):
    got = rom.u16(listp + k*2)
    assert got == iid, "mart list[%d] = %d, expected %d" % (k, got, iid)
assert rom.u16(listp + len(ids)*2) == 0, "mart list not 0x0000-terminated"
print("mart list = %d items + terminator  OK" % len(ids))

# all 51 prices == 1000
bad = [(i, rom.read_name(IST+i*44,14), rom.u16(IST+i*44+0x10)) for i in ids if rom.u16(IST+i*44+0x10) != 1000]
assert not bad, "prices not 1000: %s" % bad[:5]
print("all %d evo item prices == 1000  OK" % len(ids))

print("\nALL VERIFY CHECKS PASSED")
