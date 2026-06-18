# Project Red — Planned Features (Backlog)

Features I want to add later. None are implemented yet — this is a planning/feasibility document.
Each was researched against the actual **UCDEP (CFRU/DPE) base** (`Roms/UCDEP/config.h`), the HMA
metadata (`build/project-red.toml`), and the proven feature patterns in `build/` (`feature_starterregion.py`,
`feature_pallet_grass.py`, `feature_celadon_evoshop.py`).

## The one constraint that decides everything

This project **byte-edits a prebuilt ROM with Python** — it does **not** compile the game engine. The
machine has the .NET runtime but **no C compiler / SDK**, and the CFRU/DPE C source isn't here (only the
prebuilt UCDEP patch + `config.h`). So a feature is only feasible here if it is one of:

- **flip a flag/var that's already compiled into the engine** (a `setflag`/`setvar` in a script), or
- **edit a data table in place**, or
- **allocate new scripts/data** in the free region (`rom.alloc()` @ `0x71AE00`) and repoint to it, or
- **add/move map objects, coord-events, and map-scripts**.

Anything that needs **new engine code** (a new battle hook, a new overworld actor, a new UI renderer)
is **not feasible headless** — it would require uncommenting a `#define` in `config.h` and **recompiling
CFRU/DPE**, which can't be done on this machine. In `config.h`, a commented `//#define …` is the tell:
that code path is **not in the shipped binary**.

This single split sorts the four features into: **flip-a-flag easy (DexNav)** → **script workaround,
partial (Nuzlocke, Level Caps)** → **needs a recompile (Followers)**.

| Feature | Verdict | Effort |
|---|---|---|
| **DexNav** | ✅ Feasible (engine already ships it) | Easy |
| **Nuzlocke mode** | 🟡 ~70% feasible; faint-auto-release needs engine | Moderate |
| **Hard level caps** | 🟠 True cap needs engine; only an ugly workaround is headless | Hard |
| **Follower Pokémon** | ❌ Not feasible headless (needs recompile + art) | Blocked |

**Recommended order:** DexNav → Nuzlocke (partial) → Level Caps (soft/deferred) → Followers (parked).

---

## 1. DexNav — ✅ Easy (do this first)

**Goal:** an in-game menu that shows which Pokémon are available in the current area (ideally with levels,
odds, and held items).

**Big finding:** CFRU/DPE **already ships a complete, ORAS-style DexNav** that is compiled into the UCDEP
base — there's nothing to build. `config.h` defines `FLAG_SYS_DEXNAV` (`0x91E`, *not* commented), plus
`VAR_DEXNAV 0x500C` and the held-items flag `FLAG_UNLOCKED_DEXNAV_HELD_ITEMS 0x92A`. The DexNav UI reads
the per-map wild table (`data.pokemon.wild`), which this hack has **already themed** via `feature_wild.py`,
so it will list our custom encounters for free.

**Approach:** a tiny `feature_dexnav.py` that injects `setflag 0x91E` (and `setflag 0x92A` for held-item
display) into the new-game flag-init script (`scripts.newgame.setflags` @ `0x1A6481`). If there's no slack
to add the opcodes in place, copy the script to `rom.alloc()`'d space, append the two `setflag`s before the
terminator, and repoint — the exact pattern used by the existing features. Then mGBA-playtest: open the
start menu and confirm DexNav appears and lists the current map's species.

**Hook points:** `FLAG_SYS_DEXNAV 0x91E`, `FLAG_UNLOCKED_DEXNAV_HELD_ITEMS 0x92A`, `VAR_DEXNAV 0x500C`
(`config.h`); `scripts.newgame.setflags` @ `0x1A6481`; `data.pokemon.wild` @ `0x3C9CB8`.

**Caveats:** runtime-only behavior → must be confirmed in mGBA (no static check). DexNav's search/spawn
pulls a wild mon from the map table, so define how it interacts with a future Nuzlocke first-encounter
rule (it could be a loophole). Search-chain/level tuning lives in source and is baked in (not editable
headless), but the feature works fine untouched.

---

## 2. Nuzlocke mode — 🟡 Moderate (~70% headless; one rule needs the engine)

**Goal:** a new-game toggle that enforces Nuzlocke rules — (a) fainted = dead (boxed/released),
(b) only the **first** wild encounter per area is catchable, (c) nickname everything.

**What the base provides:** `FLAG_NO_CATCHING 0x902`, `FLAG_NO_CATCHING_AND_RUNNING 0x904`,
`FLAG_NO_RANDOM_WILD_ENCOUNTERS 0x911`, `FLAG_SCALE_WILD_POKEMON_LEVELS 0x90D`, and — usefully — CFRU's
built-in **"Ignore/Engage" pre-battle screen** (`IgnoreWildPokemon`, flags `0xA02`/`0xA03`). There is **no**
built-in on-faint hook or permadeath framework.

**Headless-feasible slice (~70%):**
- **New-game toggle** — clone `feature_starterregion.py`'s proven Oak's-Lab menu plumbing (it already
  repoints the starter-ball objects and runs a `multichoice`); add a Nuzlocke yes/no choice and set a mode var.
- **Force-nickname** — trivial (flag/prompt).
- **First-encounter lock** — in Nuzlocke mode, default `FLAG_NO_CATCHING 0x902` on, and clear it on entering
  an area that hasn't been encountered yet, gated by one "already-encountered" flag per area. Drive this from
  each pre-League area's **`ON_TRANSITION` map-script** (the pattern `recon_oaklab.py` decoded and
  `feature_pallet_grass.py` proved) — far cleaner and more auditable than repointing every grass tile. CFRU's
  Ignore/Engage screen can front it.

**Not feasible headless:** **auto-boxing/releasing a fainted mon.** On-faint logic is compiled C
(`atk19_tryfaintmon` / faint handlers) with no script hook, and scripts only run *after* a battle ends. The
best we can do headlessly is a **post-battle party sweep** that boxes 0-HP mons — which catches the common
case but misses mid-battle switch-faints and full wipes. Ship it as best-effort + an **honor rule** (and
optionally a companion save-editor), and label true auto-release as needing an engine recompile.

**Hook points:** `config.h` flags above; `scripts.text.multichoice` @ `0x3E04B0`; `scripts.newgame.setflags`
@ `0x1A6481`; Oak's-Lab ball objects (bank 4, map 3, obj 4/5/6); per-area `ON_TRANSITION` map-scripts;
`rom.alloc()` free space for the menu/check/sweep scripts.

**Caveats:** pick a genuinely-free mode var + per-area flag range — `feature_starterregion.py` already uses
`0x40E9/EA/ED/B8`, so audit `config.h`/`.toml` first to avoid collisions. A single missed pre-League area
silently breaks the first-encounter rule, so the area list must be complete. Edits the new-game flow → mGBA
playtest mandatory.

---

## 3. Hard level caps — 🟠 Hard (true cap needs the engine)

**Goal:** the player's Pokémon can't out-level the next gym leader; the cap rises per badge.

**Reality:** there is **no EXP/level-cap engine hook** and **no config flag** for this. EXP is added in
compiled C (`GiveExp`/`CalcExpMod`) that we can't recompile or patch headlessly. Two partial paths exist,
neither clean:

- **(A) Soft "difficulty" knob (data-only, easy):** the badge-**obedience** thresholds *are* editable single
  bytes — `scripts.battle.badge.obey.{0,2,4,6}badges` @ `0x1D492 / 0x1D4A0 / 0x1D4AE / 0x1D4BC`
  (`config.h` `BADGE_n_OBEDIENCE_LEVEL`, defaults 10/30/50/70). Obedience makes **over-cap mons disobey**,
  which is a real soft deterrent — but it only applies to *traded* mons unless
  `OBEDIENCE_CHECK_FOR_PLAYER_ORIGINAL_POKEMON` is enabled, and that `#define` is **commented off** in this
  base (so it'd need a recompile). As-is, this nudges difficulty but isn't a hard cap.
- **(B) Script de-level (headless but ugly):** a `feature_levelcap.py` routine that, after each battle, reads
  the badge count, computes the cap from a badge→level table (gym ace levels live in `feature_bosses.py`),
  and **rolls any over-cap mon's level back down**. The mon visibly levels up and then gets yanked back —
  poor UX — and there's **no single global post-battle hook**, so it has to be attached to many trainer/wild
  battle scripts (fragile, easy to miss a path, and de-leveling can strip a just-learned move or drop below
  an evo gate → softlock risk).

**Recommendation:** if you want *something* now, ship **(A)** as a tunable difficulty setting; treat the real
hard cap as **(B) deferred** until/unless a build toolchain appears (the clean version shares the same
"no global post-battle hook" problem as Nuzlocke's faint-release).

**Hook points:** obedience bytes @ `0x1D492/A0/AE/BC`; `config.h:230 OBEDIENCE_BY_BADGE_AMOUNT`,
`:323 //OBEDIENCE_CHECK_FOR_PLAYER_ORIGINAL_POKEMON` (commented); badge-count flag/var (pin exactly before
building); `GiveExp` (engine, not headless-hookable).

---

## 4. Follower Pokémon — ❌ Not feasible headless (parked)

**Goal:** the lead party Pokémon trails the player around the overworld (HGSS / Let's Go style).

**Reality:** the skeleton exists in CFRU source but is **not in this binary**. `config.h:359` has
`//#define FOLLOWING_POKEMON` **commented out**, and the UCDEP **README explicitly states followers are
non-functional in this version**. The flag `FLAG_FOLLOWER_POKEMON 0x4BD` and
`ucdep.scripts.followermon` @ `0x10442C8` exist, but **flipping the flag without the compiled engine code
will do nothing useful and likely crash/softlock**.

Enabling it requires **(1)** obtaining the CFRU/DPE source, uncommenting the `#define`, and **recompiling**
to a new base ROM (needs a C toolchain this machine lacks), **and (2)** sourcing/inserting **overworld
sprite sheets for ~1000 Gen 1–9 species** (the base has none for the expanded dex) — a large, separate art
deliverable. GBA VRAM/OAM limits may also constrain an extra overworld actor even after a recompile.

**Status:** **blocked** — revisit only if a build toolchain *and* an overworld-sprite art set become
available. Do **not** attempt to flip `FLAG_FOLLOWER_POKEMON` on the current base.

**Hook points (for reference):** `config.h:359 //FOLLOWING_POKEMON`, `:360 FLAG_FOLLOWER_POKEMON 0x4BD`;
`ucdep.scripts.followermon` @ `0x10442C8`; `graphics.overworld.sprites` @ `0x39FDB0` (unpopulated for
follower mons); UCDEP `READ-ME.txt:62`.

---

### Summary

DexNav is essentially free (the engine already has it — just enable the flag). Nuzlocke is mostly doable as
a scripted feature, with the faint-death rule degraded to best-effort + honor. Hard level caps can only be
approximated headlessly (soft obedience knob, or an ugly de-level hack). Followers are off the table until a
recompile + sprite-art pipeline exists. The dividing line every time is **"does the engine code already
exist in the UCDEP binary?"** — DexNav yes, the rest no.
