"""Read-back verification of the Pallet bottom-left-grass Oak gate (run after `py build.py`)."""
import romlib, mapinfo, feature_pallet_grass as F

rom = romlib.Rom()                       # built project-red.gba
h = mapinfo.header(rom, 3, 0); ev = rom.ptr(h + 4)
count = rom.u8(ev + 2); arr = rom.ptr(ev + 12)

assert count == 11, "coord count not 11 (got %d)" % count
print("coord count = %d (3 original + 8 new) OK" % count)

# original 3 entries must be byte-identical to the pristine base
base = romlib.Rom(r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba")
bh = mapinfo.header(base, 3, 0); bev = base.ptr(bh + 4); barr = base.ptr(bev + 12)
for i in range(3):
    a = bytes(rom.data[arr + i*0x10: arr + i*0x10 + 16])
    b = bytes(base.data[barr + i*0x10: barr + i*0x10 + 16])
    assert a == b, "original coord%d changed!" % i
print("original 3 coord events byte-identical to base OK")

# 8 new entries
scr_ref = None
for i in range(3, 11):
    e = arr + i*0x10
    x, y = rom.u16(e), rom.u16(e+2)
    elev, p5 = rom.u8(e+4), rom.u8(e+5)
    var, val, pA = rom.u16(e+6), rom.u16(e+8), rom.u16(e+0xA)
    scr = rom.ptr(e+0xC)
    exp = F.GRASS_TILES[i-3]
    assert (x, y) == exp, "tile mismatch coord%d: %s != %s" % (i, (x, y), exp)
    assert elev == 3 and var == 0x4050 and val == 0 and p5 == 0 and pA == 0, "field mismatch coord%d" % i
    scr_ref = scr_ref or scr
    assert scr == scr_ref, "new entries must share one script ptr"
    print("  coord%d (%2d,%2d) elev=%d var=0x%04X val=%d -> 0x%X" % (i, x, y, elev, var, val, rom.to_gba(scr)))

# shared script bytes == feature module's NEW_SCRIPT exactly
got = bytes(rom.data[scr_ref: scr_ref + len(F.NEW_SCRIPT)])
assert got == F.NEW_SCRIPT, "script bytes mismatch:\n got %s\n exp %s" % (got.hex(), F.NEW_SCRIPT.hex())
print("shared script @0x%X = %s (%d bytes) OK" % (rom.to_gba(scr_ref), F.NEW_SCRIPT.hex(), len(F.NEW_SCRIPT)))

# the script must warp to bank4/map3 (Oak's Lab) and set the lab-scene gate VAR_0x4055
s = F.NEW_SCRIPT
assert bytes([0x16, 0x55, 0x40, 0x01, 0x00]) in s, "missing setvar VAR_0x4055,1"
assert bytes([0x39, 0x04, 0x03, 0xFF, 0x06, 0x00, 0x0C, 0x00]) in s, "missing warp to Oak's Lab (4,3,6,12)"
assert bytes([0x16, 0x50, 0x40, 0x01, 0x00]) in s, "missing setvar VAR_0x4050,1 (self-disable)"
print("script sets VAR_0x4055=1, VAR_0x4050=1, and warps to Oak's Lab(4,3,6,12) OK")

print("\nALL VERIFY CHECKS PASSED")
