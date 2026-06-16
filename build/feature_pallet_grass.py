"""Make Pallet Town's BOTTOM-LEFT grass patch trigger the same 'Prof. Oak runs up and takes you
to his lab' outcome as the existing NORTH-exit gate, so the player can't slip past the starter gate
by walking onto the south-west grass before getting a Pokemon.

WHY A CUSTOM SCRIPT (not a clone of the north coord0):
  The north gate's shared body @0x08165605 is POSITION-DEPENDENT: after the intro it runs a hardcoded
  applymovement choreography (Oak walks out of the lab; the PLAYER is force-walked from the north gate
  down-and-right into the lab door) driven by VAR_0x4001. Re-running it from the bottom-left grass walks
  the player into town-edge collisions and the following waitmovement(0) blocks FOREVER -> soft-lock
  (verified by full opcode decode of the 176-byte body). So we do NOT goto/call that body.

WHAT WE DO INSTEAD:
  Show Oak's two canonical lines from THIS scene, then replicate ONLY the body's terminal side-state
  (the exact bytes it sets right before warping) and the warp itself -- but NONE of the position-dependent
  applymovement/waitmovement choreography. The destination warp (Oak's Lab, bank4 map3, x6 y12) is
  identical to the north flow, so the lab ends up in the IDENTICAL post-warp state; the lab's own
  ON_TRANSITION / ON_WARP_TABLE / ON_FRAME_TABLE map scripts (all gated on VAR_0x4055==1, confirmed by
  reconning map (4,3)) then play Oak's full monologue + the 'choose a starter' selection exactly as if
  the player had come through the north gate. We set VAR_0x4055=1 just like the body does.
      msgbox 0x0817D72C  "OAK: Hey! Wait! Don't go out!"           (the 'stop' line)
      msgbox 0x0817D74A  "It's unsafe! ... Here, come with me!"    (explains + leads to the lab)
      16 55 40 01 00   setvar  VAR_0x4055, 1   (lab 'choose a starter' scene gate)
      2A 2B 00         clearflag 0x2B
      16 50 40 01 00   setvar  VAR_0x4050, 1   (self-disables BOTH the north AND these new triggers)
      29 2C 00         setflag 0x2C            (un-hide Oak obj2 in town for later)
      29 01 40         setflag 0x4001
      39 04 03 FF 06 00 0C 00   warp 4,3,0xFF,(6,12)
  We run under `69 lockall` (the body always ran under the entry script's lockall) and append a defensive
  `02 end`. The only difference from the north gate is the skipped in-town Oak-walk animation (the part
  that is hardcoded to the north tiles and would soft-lock from the bottom-left); the dialog + lab scene
  are identical. The Oak texts (0x0817D72C / 0x0817D74A) and the msgbox sequence are taken verbatim from
  the shared body, so they are guaranteed to render correctly.

  We add ONE coord event per bottom-left grass tile, each gated on VAR_0x4050==0 (same gate as the north
  tiles), pointing at the single shared custom script. The body sets VAR_0x4050=1 on completion, so all
  triggers (north + these) permanently disable after the first one fires -- the scene never replays.

RELOCATION:
  Pallet's coord-event array (3 entries @ROM 0x71AC80) has no slack, so we copy it into rom.alloc'd space,
  append the 8 new entries, then repoint events+12 and bump the count u8 at events+2 (3 -> 11).

NOTE: edits the pre-starter flow -> MUST be mGBA-playtested per CLAUDE.md.
"""
import romlib, mapinfo

PALLET_BANK, PALLET_MAP = 3, 0

# 8 bottom-left tall-grass tiles (verified col=0 walkable, elev=3, metatile 13). No coord trigger today.
GRASS_TILES = [(2, 17), (3, 17), (4, 17), (5, 17),
               (2, 18), (3, 18), (4, 18), (5, 18)]

ELEV = 3
GATE_VAR = 0x4050        # same gate the north tiles use; body sets it =1 on completion (auto-disable)
GATE_VAL = 0

# Custom Oak-stop -> warp-to-lab script: lockall; Oak's 2 lines; <verbatim body side-state>; warp; end
NEW_SCRIPT = bytes([
    0x69,                                            # lockall
    0x0F, 0x00, 0x2C, 0xD7, 0x17, 0x08, 0x09, 0x04,  # msgbox 0x0817D72C "OAK: Hey! Wait! Don't go out!"
    0x0F, 0x00, 0x4A, 0xD7, 0x17, 0x08, 0x09, 0x04,  # msgbox 0x0817D74A "It's unsafe!... come with me!"
    0x68,                                            # closemessage
    0x16, 0x55, 0x40, 0x01, 0x00,        # setvar VAR_0x4055, 1   (lab 'choose starter' scene gate)
    0x2A, 0x2B, 0x00,                    # clearflag 0x002B
    0x16, 0x50, 0x40, 0x01, 0x00,        # setvar VAR_0x4050, 1   (self-disable all gate triggers)
    0x29, 0x2C, 0x00,                    # setflag 0x002C         (un-hide Oak obj2 in town)
    0x29, 0x01, 0x40,                    # setflag 0x4001
    0x39, 0x04, 0x03, 0xFF, 0x06, 0x00, 0x0C, 0x00,  # warp bank4 map3 warpId0xFF x6 y12 -> Oak's Lab
    0x02,                                # end (defensive; warp is terminal)
])


def _events_struct(rom):
    h = mapinfo.header(rom, PALLET_BANK, PALLET_MAP)
    assert h is not None, "Pallet Town header not found"
    ev = rom.ptr(h + 4)
    assert ev is not None, "Pallet Town events struct not found"
    return ev


def apply(rom, verbose=True):
    ev = _events_struct(rom)
    count = rom.u8(ev + 2)
    old_arr = rom.ptr(ev + 12)
    assert old_arr is not None, "Pallet coord array pointer is null"

    # 1) write the shared custom warp-to-lab script to free space
    scr = rom.alloc(len(NEW_SCRIPT))
    rom.data[scr:scr + len(NEW_SCRIPT)] = NEW_SCRIPT
    scr_gba = rom.to_gba(scr)

    # 2) relocate the coord array: copy existing entries verbatim, then append the new ones
    new_count = count + len(GRASS_TILES)
    new_arr = rom.alloc(new_count * 0x10)
    # copy the existing 'count' entries byte-for-byte (keeps north gate + post-starter coord2 intact)
    rom.data[new_arr:new_arr + count * 0x10] = rom.data[old_arr:old_arr + count * 0x10]
    # append one 16-byte coord entry per bottom-left grass tile
    for i, (x, y) in enumerate(GRASS_TILES):
        e = new_arr + (count + i) * 0x10
        rom.wu16(e + 0x0, x)         # x
        rom.wu16(e + 0x2, y)         # y
        rom.wu8(e + 0x4, ELEV)       # elevation
        rom.wu8(e + 0x5, 0)          # pad
        rom.wu16(e + 0x6, GATE_VAR)  # var
        rom.wu16(e + 0x8, GATE_VAL)  # value
        rom.wu16(e + 0xA, 0)         # pad
        rom.wptr(e + 0xC, scr)       # scriptPtr -> shared custom script

    # 3) repoint the array and bump the count (u8 at events+2)
    rom.wptr(ev + 12, new_arr)
    rom.wu8(ev + 2, new_count)

    if verbose:
        print("[pallet_grass] script@0x%X, coord array 0x%X(%d) -> 0x%X(%d), +%d bottom-left triggers"
              % (scr_gba, rom.to_gba(old_arr), count, rom.to_gba(new_arr), new_count, len(GRASS_TILES)))
    return dict(script=scr, new_array=new_arr, count=new_count, tiles=list(GRASS_TILES))


if __name__ == "__main__":
    # standalone dry-run against the pristine base (the output ROM's free region is already consumed)
    base = r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba"
    import os
    tml = base[:-4] + ".toml"
    r = romlib.Rom.__new__(romlib.Rom)
    r.path = base
    with open(base, "rb") as f:
        r.data = bytearray(f.read())
    r.tables = romlib.parse_toml_anchors(tml)
    r._free = romlib.Rom.FREE_BASE
    info = apply(r)
    print("dry-run OK:", {k: (hex(v) if isinstance(v, int) else v) for k, v in info.items()})
