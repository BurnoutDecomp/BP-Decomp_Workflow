# APT / ActionScript — Completion Playbook

**What this is:** the step-by-step to run *after* the Apt engine + ActionScript
interpreter are confirmed fully working end-to-end. It covers (a) declaring done,
(b) consolidating the three scattered `Apt` source trees into one clean path, and
(c) updating every path-bearing artifact so the build, the faithfulness ratchet,
and the **website** all show the correct new path.

Read order for the mechanics referenced below: [AGENTS.md](AGENTS.md) →
[STRATEGY.md](STRATEGY.md) → `progress/` ledger.

> ⚠️ Do **not** start the move until the "Definition of done" gate below is green.
> Relocating files while AS is still being brought up will scramble your diffs and
> make regressions impossible to bisect.

---

## 0. Definition of done (gate before touching anything)

Treat these as hard preconditions. If any is red, keep working on AS — not on paths.

- [ ] AS bytecode executes for real: `AptActionInterpreter` runs a real menu's
      action stream (no `_embed_check` / shim fallbacks on the hot path).
- [ ] Menus drive end-to-end through the boot test (title → press-start → menu
      navigation → accept). Verify with `tools/diagnostics/boot_test.ps1`; the
      per-session menu-drive and menu-regression handoff notes this originally
      pointed at were never committed to the repo, so the boot test is the gate.
- [ ] `python tools/work/faithfulness_lint.py` reports **no new** `apt_shim` /
      `engine_stub` smells, and the Apt-related entries in
      `progress/faithfulness_baseline.json` are shrinking, not holding. (Per the
      lint mechanics: the Apt engine is ~95% reconstructed; the remaining smells
      should be naming/leaf/serialized debt, not missing code.)
- [ ] The Apt TUs in `progress/status.json` are `reviewed` (or your project's
      terminal state), not `in_progress`.
- [ ] A clean `tools/build/build_game_exe.bat` build **links** with the Apt
      engine object files in the real link set (not the `AptRenderLinkStubs` /
      `AptGlobals` stub path).

Only when all five are checked do you proceed.

---

## 1. Why the paths are scattered (context for the move)

Today the one Apt library is spread across **three** path shapes — a fossil of
EA's original versioned middleware package (`Apt 2.00.00`) being partially
relocated under `SDKs/EATech/` during decomp:

| # | Current path | Contents | Notes |
|---|---|---|---|
| 1 | `src/SDKs/EATech/include/Apt/` | bulk engine: interpreter, `AptCIH`, `AptMovie`, `AptArray`, characters, `AptStd/`, `AptString/`, `AptValue/` | Holds **both** `.h` and `.cpp` despite being named `include/` |
| 2 | `src/SDKs/EATech/Apt/` | init/bootstrap, GC (`AptValueGC*`), `DogmaAllocator`, `Apt*MembersIndex` tables, `AptMath` | |
| 3 | `src/SDKs/Packages/Apt/2.00.00/source/AptValue/` | `AptSprite`, `AptString` | Un-migrated remnant sitting at the *original* EA package path |

File counts drift as the engine is reconstructed, so **measure at move time** rather than
trusting a number written here:

```bash
for d in src/SDKs/EATech/include/Apt src/SDKs/EATech/Apt src/SDKs/Packages/Apt; do
  echo "$d: $(find b5-decomp/$d -name '*.h' | wc -l) .h, $(find b5-decomp/$d -name '*.cpp' | wc -l) .cpp"
done
```

(At the time of writing that was roughly 253 / 26 / 4 files respectively — a little over
280 in total, split about 115 headers to 165 bodies.)

Original EA layout (preserved in `references/Feb-2007/.../SDKs/Packages/Apt/2.00.00/`):
`include/Apt/...` for public headers, `source/...` for bodies. The decomp flattened
most of that into `SDKs/EATech/` but left the `AptValue` sub-package behind, and let
`.cpp` files leak into `include/Apt/`.

### Target layout (LOCKED: `Packages/Apt/2.00.00`)

Consolidate everything to the **original EA package path** — the historically
faithful location, matching the layout preserved in
`references/Feb-2007/.../SDKs/Packages/Apt/2.00.00/`. Every Apt file lands here:

```
src/SDKs/Packages/Apt/2.00.00/
    include/Apt/            ← every header (.h)
        AptStd/             ← (substructure already matches the Feb-2007 reference exactly)
        AptString/
        AptValue/
    source/                 ← all bodies (.cpp), mirroring the include/Apt substructure
        AptStd/
        AptString/
        AptValue/
```

Rationale for choosing this over `EATech/Apt/`: it stops the tree lying about where
the middleware lived, restores the versioned-package identity (`Apt 2.00.00`), and
the `source/AptValue/` remnant that's *already* at this path stops being an orphan —
everything else moves **to** it rather than away from it. The reference confirms the
`include/Apt/{AptStd,AptString,AptValue}` shape, and the current `include/Apt/`
substructure is identical, so headers map 1:1.

> The three shapes being retired: `src/SDKs/EATech/include/Apt/`,
> `src/SDKs/EATech/Apt/`, and the partial `src/SDKs/Packages/Apt/2.00.00/source/AptValue/`
> (those 4 files stay in place; the rest join them). Delete the two `EATech/` dirs
> once emptied. Note `src/SDKs/EATech/` also holds the two Apt stub TUs
> (`AptGlobals.cpp`, `AptRenderLinkStubs.cpp`) plus unrelated middleware (`eathread`,
> `rw*`, `eajobs`) — only the Apt engine moves.

---

## 2. The move — order of operations (nothing breaks if you follow it)

Do these in sequence. Build/gate between the risky steps so a break is bisectable.

### 2.1 Move the files (git-tracked, in the `b5-decomp` submodule)

Use `git mv` inside the submodule so history follows the files:

```bash
cd b5-decomp
P=src/SDKs/Packages/Apt/2.00.00
# headers: EATech/include/Apt/**  ->  Packages/.../include/Apt/**  (substructure is identical, 1:1)
git mv src/SDKs/EATech/include/Apt/AptCIH.h              $P/include/Apt/AptCIH.h
git mv src/SDKs/EATech/include/Apt/AptStd/AptCXForm.h    $P/include/Apt/AptStd/AptCXForm.h
# bodies: the .cpp that leaked into include/Apt  ->  Packages/.../source/**
git mv src/SDKs/EATech/include/Apt/AptCIH.cpp            $P/source/AptCIH.cpp
# the 24-file bootstrap set: EATech/Apt/**  ->  split by extension into include/ vs source/
git mv src/SDKs/EATech/Apt/AptInit.cpp                   $P/source/AptInit.cpp
git mv src/SDKs/EATech/Apt/DogmaAllocator.h             $P/include/Apt/DogmaAllocator.h
# AptValue remnant already at $P/source/AptValue/ — leave in place; everything else joins it.
# ...script the rest; do NOT leave the old EATech/ dirs half-populated.
```

> Decide one rule and apply it uniformly: **headers → `include/Apt/…`, bodies →
> `source/…`**, mirroring substructure. The tricky files are the `.cpp` currently
> under `include/Apt/` and the `.h` currently under `EATech/Apt/` (e.g.
> `DogmaAllocator.h`) — they split by extension, not by their current folder.

### 2.2 Rewrite every `#include` (this is the big one)

Includes are **literal repo-relative paths from `src/`**, e.g.
`#include "SDKs/EATech/include/Apt/AptCIH.h"`. There is no include-search-path
magic — every reference is the full path, so **every** one must be rewritten,
across the whole tree (Apt engine *and* the `GameSource` / `GameShared/.../AptInterface`
consumers). Sweep and rewrite mechanically:

```bash
# from repo root; preview first, then apply.
grep -rln 'SDKs/EATech/include/Apt\|SDKs/EATech/Apt/' b5-decomp/src
# rewrite per mapping (note: includes always point at the HEADER, so they resolve to include/Apt/):
#   SDKs/EATech/include/Apt/          ->  SDKs/Packages/Apt/2.00.00/include/Apt/
#   SDKs/EATech/Apt/<Header>.h        ->  SDKs/Packages/Apt/2.00.00/include/Apt/<Header>.h
#     (e.g. the lone `#include "SDKs/EATech/Apt/DogmaAllocator.h"` -> .../include/Apt/DogmaAllocator.h)
```

Note the asymmetry: `#include`s only ever reference **headers**, so every rewrite
lands under `include/Apt/` — the `source/` tree is named only by the build batch
(§2.3), never by an `#include`.

Double-check the moved headers' **own** includes of siblings — those are relative
paths too and must land on the new location.

### 2.3 Update the build source list — `tools/build/build_game_exe.bat`

The build does **not** glob; it enumerates every Apt `.cpp` by hand. Find the block with
`grep -n "EATech" tools/build/build_game_exe.bat | grep -i apt` rather than trusting a line
number — it was around **lines 373–566** when this was written, with a couple of stragglers
near the end of the file. It lists paths like:

```
echo "%SRC%\SDKs\EATech\Apt\AptInit.cpp"
echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreter.cpp"
...
```

Rewrite each `%SRC%\...` path to the new location (note: Windows backslashes here,
forward slashes in the `#include`s — keep them consistent per file). Also check the
sibling stub TUs referenced in that block (`AptRenderLinkStubs.cpp`,
`AptGlobals.cpp`, `AptRenderHooks.cpp`) — if AS being "fully working" means the
stub link path is retired, **remove the stub TUs from the link set** rather than
just repointing them.

### 2.4 Build + gate

Run the full `build_game_exe.bat` (and the per-TU gate `tools/_gate_tu.bat` if you
touched signatures). It must compile **and link** with the real Apt objects. Fix
include fallout here — this is the checkpoint where a missed path shows up.

---

## 3. Update the tracking JSON so the **website shows the correct path**

Paths appear in five artifacts. Two are **derived** (regenerate — never hand-edit),
the rest need attention:

| Artifact | Path refs | How paths get in | Action |
|---|---|---|---|
| `progress/class_homes.json` | ~100 | **Derived** — `class:X → home .cpp` | **Regenerate.** This is what the site/attribution uses to show each class's home path. |
| `progress/faithfulness_baseline.json` | ~276 | Fingerprints keyed `category\tPATH\tsymbol` | **Regenerate deliberately** (see caveat). |
| `progress/tu_index.json` | ~26 | TU identity keyed by source-list path | Update the moved Apt TU keys. |
| `progress/status.json` | ~6 | Mostly **symbol-keyed** (`Class::method`) → path-independent; a few notes embed paths | Fix path strings in notes only; keys don't move. |
| `progress/identity.json` | ~2 | path strings | Update the 2 refs. |

### 3.1 `class_homes.json` — the website's path source (regenerate)

This file maps every `class:`-TU to its real home file and is what the work server
uses for Git-based contribution attribution and the path the site displays. It is
**auto-resolved from the committed sources** — do not edit by hand:

```bash
python tools/work/resolve_class_homes.py            # dry run — inspect the new homes
python tools/work/resolve_class_homes.py --apply     # writes progress/class_homes.json
```

After the move + include rewrite, every `class:Apt*` entry should resolve to the
new path automatically. If any class drops out (the resolver is deliberately
conservative and won't guess), that's a signal its bodies didn't move cleanly —
investigate rather than forcing it.

### 3.2 `faithfulness_baseline.json` — regenerate, but deliberately

The fingerprints embed full paths, so the move invalidates the Apt ones. **But**
per the ratchet's own rule: *shrink this file, never blind-regen it* — a bulk
regen hides fresh invention. Two-step it:

1. First run the lint as-is to confirm the only failures are the **path renames**
   of already-grandfathered Apt smells (not new invention):
   `python tools/work/faithfulness_lint.py`
2. Then, and only then, pay down + regenerate:
   `python tools/work/faithfulness_lint.py --baseline`

Because AS is now fully working, expect many `apt_shim` / `engine_stub` entries to
**disappear** (real code replaced the shims) — the Apt slice of the baseline should
get materially smaller, not just re-pathed.

### 3.3 `tu_index.json` / `status.json` / `identity.json`

- `tu_index.json`: update the ~26 Apt path keys to the new source-list paths.
  Confirm they match exactly what `build_game_exe.bat` now names, or the
  source-list identity check will drift.
- `status.json`: keys are `Class::method` symbols, so the move itself doesn't
  touch them — only fix any path strings that appear inside `notes`.
- `identity.json`: patch the 2 path refs.

---

## 4. Commit & website refresh (submodule + CI reconcile)

**Commit only `b5-decomp` source.** Do not commit the reconciled `status.json` or
the submodule pointer by hand — CI auto-reconciles `status.json` + the submodule
pointer on `main`. (This is the standing "never commit JSON/pointers" rule.)

Concretely:
1. Commit + push the moved sources, rewritten includes, and the `build_game_exe.bat`
   path edits **inside the `b5-decomp` submodule**.
2. Push the regenerated `class_homes.json` per whatever channel the site consumes
   it (it is a `progress/` artifact, not submodule source) — this is what makes the
   **website display the new path**.
3. Let CI reconcile `status.json` + the pointer. Verify the site shows Apt TUs at
   the new home path and attribution still resolves.

---

## 5. Post-completion housekeeping

Once paths are consolidated and the site is correct:

- [ ] **Retire the AS/Apt shims.** Remove `AptRenderLinkStubs.cpp` / stub globals
      from the link set if the real engine now satisfies those symbols; delete the
      `_embed_check` fallbacks that were interpreter-bring-up scaffolding.
- [ ] **Delete the emptied directories** (`src/SDKs/EATech/include/Apt/` and
      `src/SDKs/EATech/Apt/`) so no one re-populates the old shapes. The Apt engine
      now lives entirely under `src/SDKs/Packages/Apt/2.00.00/`.
- [ ] **Update the goal/ledger.** Mark the `apt` goal done in the ledger; move the
      Apt TUs to their terminal status.
- [ ] **Update the handoff docs** — if a session is carrying one-to-one/menu-drive
      handoff notes in its own worktree, reconcile them to reflect AS-complete (they
      are not committed here, so they will not turn up in a clone).
- [ ] **Update agent memory.** The memory notes that currently describe the Apt
      framework as shimmed / not-fully-loaded (PERSISTENTAPT menu framework,
      title-flow bring-up, apt-decomp-campaign) will be stale — refresh or retire
      them, and record the new canonical path so future agents don't grep the old
      one.

---

## Quick checklist (tear-off)

```
[ ] DoD gate green (AS runs, menus drive, lint clean, TUs reviewed, links)
[ ] Target LOCKED: src/SDKs/Packages/Apt/2.00.00/{include/Apt,source}
[ ] git mv every Apt file into new layout (headers->include/Apt, bodies->source)
[ ] Rewrite every #include across src/ (engine + AptInterface consumers)
[ ] Repoint tools/build/build_game_exe.bat Apt block (locate it by grep, not line no.)
[ ] Full build + link gate green
[ ] resolve_class_homes.py --apply           (site path source)
[ ] faithfulness_lint.py, then --baseline     (deliberate, expect shrink)
[ ] Fix tu_index.json / identity.json / status.json notes paths
[ ] Boot test still passes end-to-end
[ ] Commit b5-decomp source only; let CI reconcile status.json + pointer
[ ] Verify website shows new path + attribution
[ ] Retire shims, delete old dirs, update ledger + handoffs + memory
```
