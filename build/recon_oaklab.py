"""Recon Oak's Lab (bank 4, map 3): map-scripts (ON_LOAD/ON_TRANSITION/ON_WARP/ON_FRAME tables) and
coord events, to independently confirm what var/flag gates the 'choose a starter' scene after the warp."""
import romlib, mapinfo
rom = romlib.Rom()
B, M = 4, 3

h = mapinfo.header(rom, B, M)
print("Oak Lab (%d,%d) header=0x%X name=%s" % (B, M, h, mapinfo.map_name(rom, B, M)))
ev = rom.ptr(h + 4); msp = rom.ptr(h + 8)
print("events=0x%X mapscripts=0x%X" % (ev or 0, msp or 0))

TYPES = {1: "ON_LOAD", 2: "ON_FRAME_TABLE", 3: "ON_TRANSITION", 4: "ON_WARP_TABLE",
         5: "ON_RESUME", 6: "ON_DIVE_WARP", 7: "ON_RETURN_TO_FIELD"}

def sbytes(p, n=40):
    return " ".join("%02X" % rom.u8(p + i) for i in range(n)) if p else "(null)"

print("\n=== MAP SCRIPTS (type:u8, ptr:u32; type 0 terminates) ===")
p = msp
while p and rom.u8(p) != 0:
    t = rom.u8(p); sp = rom.ptr(p + 1)
    print(" type=%d (%s) ptr=0x%X" % (t, TYPES.get(t, "?"), rom.to_gba(sp) if sp else 0))
    if t in (2, 4):  # table: (var u16, value u16, script u32) until var==0
        q = sp
        for _ in range(8):
            var = rom.u16(q); val = rom.u16(q + 2)
            if var == 0 and val == 0: break
            tscr = rom.ptr(q + 4)
            print("     entry var=0x%04X val=%d -> 0x%X  bytes: %s"
                  % (var, val, rom.to_gba(tscr) if tscr else 0, sbytes(tscr, 32)))
            q += 8
    else:           # direct script
        print("     bytes:", sbytes(sp, 40))
    p += 5

print("\n=== COORD EVENTS ===")
nCoord = rom.u8(ev + 2); pCoord = rom.ptr(ev + 12)
for i in range(nCoord):
    c = pCoord + i * 0x10
    x = rom.u16(c); y = rom.u16(c + 2); var = rom.u16(c + 6); val = rom.u16(c + 8); scr = rom.ptr(c + 0xC)
    print("  coord%d (%d,%d) var=0x%04X val=%d script=0x%X" %
          (i, x, y, var, val, rom.to_gba(scr) if scr else 0))
    print("     bytes:", sbytes(scr, 40))

# Search the whole ROM for references to VAR_0x4055 in script context is hard; instead grep the lab
# scripts' raw bytes for the 0x4055 var id (55 40) to see who reads/sets it.
print("\n=== occurrences of var 0x4055 (bytes '55 40' after a var-op) near lab scripts ===")
def scan(p, n, label):
    hits = []
    for i in range(n - 1):
        if rom.u8(p + i) == 0x55 and rom.u8(p + i + 1) == 0x40:
            op = rom.u8(p + i - 1) if i > 0 else 0
            hits.append((i, op))
    if hits:
        print("  %s: %s" % (label, ["+%d(prevop=0x%02X)" % (i, op) for i, op in hits]))
for (lbl, addr, n) in [("ON_TRANSITION area", rom.ptr(msp + 1) if msp else None, 64)]:
    pass
