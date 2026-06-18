# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

This is **not a normal application** — it's a **GBA ROM-hacking pipeline**. It headlessly byte-edits a
Pokémon FireRed ROM to produce a Gen 1–9 hack (`build/project-red.gba`), using table addresses/formats
parsed from HexManiacAdvance's (HMA) `.toml` metadata. HMA itself (`Hexmaniac/`) is a GUI-only WPF app
and **cannot be hosted headless here** (the machine has the .NET runtime but no SDK), so all edits are
done in Python against raw ROM bytes. The detailed feature write-up is in [build/README.md](build/README.md).

## Commands

Run everything with the **`py` launcher** (Python 3.8). Plain `python`/`python3` is **not on PATH**.
All scripts live in and are run from `build/`.

```
cd build
py build.py            # rebuild build/project-red.gba from the pristine UCDEP base (full pipeline)
py verify.py           # read back the output ROM: checks boss teams + wild coverage
py dump_encounters.py  # print themed wild encounters per location; writes encounters_summary.json
py inventory.py        # rebuild the location + species-pool inventory (inv_*.json / theme_input.json)
```

Each `feature_*.py` and `recon*.py` module is also runnable standalone (`py feature_wild.py`) for a
dry-run / inspection — they print diagnostics under `if __name__ == "__main__"`.

There is **no test framework, linter, or build system** — these are plain scripts. "Testing" = run
`build.py` then `verify.py` (structural read-back) and boot-test the ROM:

```
# boot smoke-test (Windows): launch the ROM, confirm it doesn't crash on load
C:\Users\James\Documents\Emulator\mGBA\mgba-sdl.exe build\project-red.gba
```

Multi-agent thematic audit of the encounters (regenerate after changing themes):
`py gen_audit_workflow.py` writes `theme_audit_workflow.js`, then run it via the Workflow tool.

## Architecture

**Pipeline (`build.py`)**: copies the pristine base ROM **and** its `.toml` to `build/project-red.gba` /
`.toml`, then calls each feature module's `apply(rom)` in order — **towngrass → wild → bosses → trainers
→ megastones → starterregion → hms** — and saves once. It is reproducible from scratch every run; **never** rely on editing the output ROM in
place across runs (always rebuild from the base). The base is `Roms/UCDEP/...gba` (a CFRU/DPE expansion
that already contains all Gen 1–9 species/moves/abilities/forms — *not* the smaller `Roms/Firered/` gen8 base).

**Core layers** (the modules you'll actually edit):
- `romlib.py` — `Rom` class: byte I/O, GBA pointer helpers (ROM base `0x08000000`), the PCS name
  codec (FireRed text encoding), `.toml` NamedAnchor parser (`rom.tables[...]["addr"]`), and `rom.alloc()`
  — a bump allocator over a verified 6 MB free region at ROM offset `0x71AE00` (used for new boss teams,
  town grass tables, etc.). `Rom()` defaults to the **output** ROM; recon scripts pass the UCDEP base path explicitly.
- `gamedata.py` — rom-parameterized data readers + `base_lines(rom)`: builds the evolution graph,
  derives base-form species, excludes legendaries/mythicals (`LEG_MYTH`, matched against ROM spellings),
  and dedupes alternate forms by name. This is the canonical "what's catchable" list.
- `mapinfo.py` — map layout / blockmap / metatile-behavior helpers (de-darkening caves, placing grass tiles, labeling maps).
- `themer.py` — habitat classification (`TYPE_HAB` type rules + per-species `OVERRIDE`) and per-location
  themes (`location_theme`). This is the knob for *what spawns where*; the audit feedback was applied here.
- `feature_wild.py` — themed, coverage-guaranteed wild-encounter assignment (the core of features 1+2).
- `feature_towngrass.py` — adds tall-grass tiles + encounter tables to towns (reuses redundant duplicate
  wild entries instead of relocating the wild table).
- `feature_bosses.py` — rewrites gym leader / Giovanni / Elite Four / Champion trainers to 6-mon themed
  teams keeping a Gen-1 ace. Also arms each boss for **Mega Evolution**: the mega mon holds its stone AND
  the trainer carries a Mega Ring (item 353) in an `item1..4` slot — CFRU's `FindTrainerKeystone` requires
  that trainer-side key item, the held stone alone is inert.
- `feature_trainers.py` — competitive custom movesets (structType 3) for all trainers + 1–3 extra
  route Pokémon scaled by progression. Runs **after** `feature_bosses` and preserves held items. Every
  generated move is filtered through `learnset.Learnset` so a mon never gets a move outside its real
  Gen-9 learnset. **Exception:** the first rival fight (`feature_bosses.FIRST_RIVAL_IDS`, Oak's Lab right
  after the starter pick) is skipped, so it keeps `feature_bosses`' easy level-up-only (structType 2) team.
- `learnset.py` — per-species **real Gen-9** legal-move sets, loaded from `gen9_legal.py`; `feature_trainers`
  filters every pick against it (falling back to the mon's actual ROM level-up moves). NOTE: the ROM's *own*
  TM/tutor compatibility tables are broad/older-gen and **not** Gen-9-accurate (they let Abra "learn" Sand
  Tomb / Dual Chop / Charge Beam), so we do not use them.
- `gen9_gen.py` / `gen9_legal.py` — `gen9_gen.py` builds the vendored `gen9_legal.py` (species idx → legal
  move ids) from Pokémon Showdown's learnset dataset: each species' latest-generation learnset (Gen 9 for
  SV mons, else its most recent gen) matched by name to this ROM's moves, ∪ the ROM's level-up moves. Run
  `curl -L -o build/_sd_learnsets.json https://play.pokemonshowdown.com/data/learnsets.json` then
  `py gen9_gen.py --write` to regenerate (the `_sd_learnsets.json` download is gitignored; `gen9_legal.py`
  is committed so the build is offline-reproducible).
- `feature_megastones.py` — scatters Mega Stones by repointing low-value overworld item balls (preserving
  each ball's pickup flag) and gives the player the Mega Ring via the new-game bedroom PC (`scripts.newgame.pc.item`).
- `feature_starterregion.py` — lets the player choose which **region's** starters to pick from at the first
  Oak's-Lab ball: repoints the 3 ball objects (Oak Lab = bank 4 map 3, obj4/5/6) to a wrapper that runs a
  paginated region menu and fills 3 verified-unused vars (0x40E9/EA/ED/B8); the ball
  `setvar VAR_0x4002,<species>` is swapped in-place to `copyvar`. Rival stays Kanto (position-based).
  Gotchas learned the hard way (all needed for the menu to not freeze): use **`6F multichoice`** not the
  `71` grid (CFRU doesn't implement grid); FRLG menus cap at **6 options** so the 9 regions are paginated
  across two list slots (64 + 63: 5+MORE / 4+BACK); and the script must `lock` before showing the menu.
  This feature edits the new-game/starter flow → **mGBA-playtested** (confirmed working).
- `feature_hms.py` — reduces HM necessity (currently: de-darkens Rock Tunnel so Flash isn't required).
- `map_render.py` — stdlib tileset/metatile renderer (LZ77 + palettes) → PNG; its `GreenGround` classifier
  keeps town grass on real lawn, not paved roads.
- `verify.py` / `dump_encounters.py` — read-back verification of the built ROM.

**Scratch/recon scripts** (`recon*.py`, `trainer_recon*.py`, `wild.py`, `maps.py`, `species_analysis.py`,
`town_recon.py`, `map_recon.py`, `wild_classify.py`, `inventory.py`) were used to reverse-engineer the
data formats and are largely **superseded** by the core modules — read them for format details, but make
real changes in the `feature_*` / `themer` / `gamedata` modules.

## Critical conventions

- **The UCDEP ROM uses non-vanilla (CFRU-expanded) structures.** Species index = internal GBA index, NOT
  National Dex: Gen 1 = 1–151, indices 252–276 are a blank gap, Gen 3 starts at 277, and alternate forms
  are interspersed and reuse the base name. **Always work by species *name*** (resolve via `gamedata`),
  never assume index == dex number. Struct sizes: stats 28 B, evolutions 128 B (16 slots), trainers 40 B,
  wild entries 20 B (FFFF-terminated). (Full offset notes are in the project memory files.)
- **Edits are mostly in-place byte writes** keyed off `.toml` table addresses; anything that grows data
  (boss teams, new wild tables) is written to free space via `rom.alloc()` and repointed — never assume
  there's slack after a table.
- **Map-block / obstacle removal is risky headless** (can soft-lock). That's why Surf/Strength HM gates
  are documented as HMA-GUI follow-up rather than auto-edited; only safe map edits (e.g. clearing the
  `cave` darkness byte) are done in code.
