"""Feature 4: reduce HM necessity to proceed.

Safely removable headless:
  * FLASH  - the only place Flash is mandatory is Rock Tunnel (dark cave). We clear the map
             header 'cave' (darkness) byte so Rock Tunnel is lit and Flash is never required.

Documented as HMA map-editor follow-up (NOT done headless, because they require removing/rerouting
physical map obstacles and risk soft-locks if done blind):
  * SURF      - mandatory water crossings (Route 23 to the League; reaching Cinnabar Island).
  * STRENGTH  - Victory Road boulder/switch puzzle (removing boulders alone soft-locks the doors).
  * CUT       - a few cuttable trees on side paths.
See README "Feature 4" for exact steps.
"""
ROCK_TUNNEL_SECTION = 138  # raw region-section value (map header offset 20) for ROCK TUNNEL

def apply(rom, verbose=True):
    # Only touch REAL, player-visited maps: those that appear in the wild-encounter table.
    import feature_wild as fw
    BANKS = rom.tables["data.maps.banks"]["addr"]
    def header(b, m):
        mp = rom.ptr(BANKS + b*4)
        return rom.ptr(mp + m*4) if mp is not None else None
    cleared = []
    seen = set()
    for e in fw.walk_wild(rom):
        key = (e["bank"], e["map"])
        if key in seen: continue
        seen.add(key)
        hdr = header(e["bank"], e["map"])
        if hdr is None: continue
        sec = rom.u8(hdr + 20)
        cave = rom.u8(hdr + 21)
        if sec == ROCK_TUNNEL_SECTION and cave != 0:
            rom.wu8(hdr + 21, 0)        # de-darken: Flash no longer needed
            cleared.append(key)
    if verbose:
        print("[hms] Rock Tunnel maps de-darkened (Flash not required): %d  %s"
              % (len(cleared), cleared))
        print("[hms] Surf / Strength / Cut obstacle removal -> documented HMA follow-up (see README)")
    return dict(flash_maps=len(cleared))

if __name__ == "__main__":
    import romlib
    rom = romlib.Rom()
    apply(rom)
