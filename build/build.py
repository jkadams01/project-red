"""Master build: apply all feature edits to a fresh copy of the UCDEP gen1-9 FireRed base
and write build/project-red.gba. Reproducible from scratch every run."""
import os, shutil, romlib

BASE_ROM  = r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).gba"
BASE_TOML = r"C:\Users\James\Documents\GitHub\project-red\Roms\UCDEP\Pokemon - FireRed Version (USA).toml"
HERE = os.path.dirname(__file__)
OUT_ROM  = os.path.join(HERE, "project-red.gba")
OUT_TOML = os.path.join(HERE, "project-red.toml")

def main():
    # fresh copy from pristine base
    shutil.copyfile(BASE_ROM, OUT_ROM)
    shutil.copyfile(BASE_TOML, OUT_TOML)
    print("[build] fresh copy from UCDEP base (%d bytes)" % os.path.getsize(OUT_ROM))

    rom = romlib.Rom(OUT_ROM)

    import feature_towngrass, feature_wild, feature_bosses, feature_trainers
    print("--- Town grass: add grass + encounter tables to cities/towns ---")
    feature_towngrass.apply(rom)
    print("--- Feature 1+2: gen1-9 lines catchable before the league (themed) ---")
    feature_wild.apply(rom)
    print("--- Feature 3: 6-mon boss teams (Gen-1 aces) ---")
    feature_bosses.apply(rom)
    print("--- Trainers: competitive movesets + bigger route teams ---")
    feature_trainers.apply(rom)

    import feature_megastones
    print("--- Mega Stones: bosses hold them; scatter the rest as item balls ---")
    feature_megastones.apply(rom)

    import feature_starterregion
    print("--- Starter region select: choose which region's starters at the first ball ---")
    feature_starterregion.apply(rom)

    try:
        import feature_hms
        print("--- Feature 4: reduce HM necessity ---")
        feature_hms.apply(rom)
    except ImportError:
        print("--- Feature 4: (feature_hms not present yet) ---")

    import feature_pallet_grass
    print("--- Pallet grass gate: bottom-left grass also triggers the Oak-to-lab scene ---")
    feature_pallet_grass.apply(rom)

    rom.save(OUT_ROM)
    print("[build] wrote", OUT_ROM)

if __name__ == "__main__":
    main()
