# project-red — a Gen 1–9 FireRed hack

A romhack of **Pokémon FireRed** built headlessly on top of the **UCDEP** base
(Ultra's CFRU/DPE Expansion, which already contains every Gen 1–9 Pokémon, move,
ability, mega and form). All edits are applied as reproducible Python byte-edits
driven by HexManiacAdvance's `.toml` table metadata.

## Output

| File | What it is |
|------|------------|
| `build/project-red.gba` | The finished ROM. Open in an emulator or in HexManiacAdvance. |
| `build/project-red.toml` | HMA metadata for the ROM (rename to match if you rename the `.gba`). |

Boot-tested in mGBA (loads without crashing); all data structures verified intact
(header untouched, wild table terminator intact, trainer pointers valid).

## Features

### 1 + 2 — Every non-legendary line catchable before the League, **themed by location**
Implemented in [`feature_wild.py`](feature_wild.py) + [`themer.py`](themer.py) + [`feature_towngrass.py`](feature_towngrass.py).
- Built the full evolution graph and isolated **436 non-legendary / non-mythical base-form lines**
  spanning Gen 1–9 (paradox Pokémon like Roaring Moon / Iron Valiant are kept; the paradox
  *legendaries* Walking Wake, Iron Leaves, etc. are excluded along with all box legendaries,
  Ultra Beasts, Tapus, mythicals, and the 26 redundant Unown form-variants).
- **Habitat-themed distribution:** every species is classified into Kanto habitats (forest, cave,
  water, graveyard, power-plant, volcano, safari, urban, rare…) and each of the 46 pre-League
  locations is themed accordingly, so encounters *make sense*: Viridian Forest is bugs, Mt. Moon /
  Rock Tunnel are rock/ground, Pokémon Tower is ghosts, Power Plant is electric, Pokémon Mansion /
  Cinnabar are fire, the Safari Zone is rare game (incl. Dratini/pseudos), Victory Road is the
  pseudo-legendaries. Native level ranges are preserved so the curve stays natural (Route 1 = L2–3,
  Victory Road = L32–48). Water (surf/fishing) slots get Water-types. All 436 lines remain
  guaranteed catchable before Indigo Plateau.
- The design was **adversarially audited by a multi-agent workflow** ([`theme_audit_workflow.js`](theme_audit_workflow.js));
  it scored mean coherence 4.7/5 and its rule-level fixes (electric/ice/steel habitat leaks, paradox
  placement) were applied.

### Town grass
[`feature_towngrass.py`](feature_towngrass.py) adds a tall-grass patch + a 12-slot encounter table to
every Kanto city/town that lacked one (Viridian, Pewter, Cerulean, Lavender, Vermilion, Celadon,
Saffron, Fuchsia, Cinnabar; Pallet & Saffron already had grass tiles). Towns without a wild-data
slot reuse the redundant duplicate Altering-Cave entries, so no risky wild-table relocation was
needed. Patches are placed on open walkable ground; if any looks awkward you can drag it in HMA's map editor.

### 3 — All bosses field 6-mon teams with a Gen-1 ace
Implemented in [`feature_bosses.py`](feature_bosses.py).
- The 8 Gym Leaders, **Giovanni** (Rocket Hideout / Silph Co. / Viridian Gym), the **Elite Four**
  (+ rematch) and the **Champion** (all 3 starter variants + rematch) — 24 trainer slots —
  now run **6 Pokémon each**.
- Teams are upgraded with cross-generation Pokémon themed to each boss (e.g. Brock now has
  Rockruff/Nacli/Rolycoly/Larvitar; Lance runs Salamence/Garchomp/Hydreigon), but **each boss's
  ace — its last, highest-level Pokémon — is kept as its signature Gen-1 species** (Onix, Starmie,
  Raichu, Vileplume, Weezing, Alakazam, Arcanine, Nidoking, Lapras, Machamp, Gengar, Dragonite,
  and the starter finals for the Champion).
- Every boss mon has max IVs and a held item (ace = Leftovers, rest = Sitrus Berry).

### Competitive trainers (all 742)
Implemented in [`feature_trainers.py`](feature_trainers.py).
- **Every trainer** (gyms, rivals, Elite Four, Champion, and all route trainers) is rewritten with a
  **competitive custom moveset**: STAB matched to the Pokémon's *better attacking stat* (physical vs
  special), strong off-type coverage that varies per Pokémon, and a setup/status move (Swords Dance /
  Calm Mind / Dragon Dance, etc.) on bosses and aces. Move power is capped by level so early fights
  stay fair. Trainers also get a smarter battle AI (check-bad-move + try-to-faint + check-viability).
- **Route trainers gain extra Pokémon** scaled by progression — early trainers skew to **+1**, mid to
  **+2**, late to **+3** (capped at 6); added Pokémon are themed to the team's types and level-appropriate
  (BST-matched evolutionary stage). Bosses (already 6) and rivals keep their curated rosters and only
  get the moveset/AI upgrade. (+1415 Pokémon added across the game.)
- All trainers are rewritten as trainer struct type 3 (held item + 4 custom moves) into fresh free space.

### 4 — HMs less necessary to proceed *(partial — see note)*
Implemented in [`feature_hms.py`](feature_hms.py).
- **Flash is no longer required:** Rock Tunnel (the only place Flash is mandatory) has been
  de-darkened by clearing its map-header `cave` flag, so it's lit and walkable without Flash.

**Not done headless (and why):** the remaining mandatory HM gates — **Surf** (water crossings on
Route 23 and to Cinnabar Island) and **Strength** (the Victory Road boulder/switch puzzle) — can't
be removed safely by blind byte-editing. Removing the Strength boulders alone soft-locks the doors
they open, and making water walkable requires per-tile collision edits. These need the
HexManiacAdvance **map editor**:

> *To finish Feature 4 in HMA:* open `project-red.gba`, go to the **Map** tab.
> - **Strength:** open Victory Road (1F/2F/3F). Either delete the Strength-boulder object events
>   and set the barrier doors open by default, or re-route the walkable path around them.
> - **Surf:** open Route 23 and the Pallet/Route 21 → Cinnabar water; edit the affected water
>   metatiles' collision so the critical path is walkable (or add a land bridge).
> - **Cut:** delete any cuttable-tree object events that block a required path.

## Rebuilding

Everything is reproducible from the pristine UCDEP base:

```
cd build
py build.py        # copies the base, applies all features, writes project-red.gba
py verify.py       # re-reads the output and checks bosses + wild coverage
```

Core pipeline: [`romlib.py`](romlib.py) (ROM I/O, pointers, free-space allocator),
[`gamedata.py`](gamedata.py) (species/evolution/legendary analysis),
`feature_wild.py`, `feature_bosses.py`, `feature_hms.py`, orchestrated by `build.py`.
(The `recon*.py`, `wild.py`, `maps.py`, `species_analysis.py` files are exploratory scratch
used while reverse-engineering the data formats.)

## Known rough edges
- Wild placement is habitat-themed + level-matched but rule-driven, so a handful of slots are
  "close enough" rather than perfect (e.g. an occasional dual-type mon in an adjacent habitat).
- Town grass patches are auto-placed on the first open ground found; functional but you may want
  to reposition one or two in HMA's map editor for looks.
- Legendaries/mythicals keep their original (often static / post-game) availability; only the
  evolution **lines** were made pre-League catchable, per the spec.
- Boss movesets are the game's default level-up sets (legal and level-appropriate) rather than
  hand-tuned competitive sets.
- Feature 4 is partial (Flash only) headless; Surf/Strength need the HMA map editor as above.
