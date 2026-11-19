---
name: apt-completion
description: >-
  User-invoked only: the one-time Apt / ActionScript completion procedure that replaces
  APT_AS_COMPLETION_PLAYBOOK.md. A definition-of-done gate comes first (ActionScript runs
  real menus end to end, no new apt_shim/engine_stub finding from work faithfulness, the Apt
  TUs terminal per the tree, the exe links with the real Apt engine objects). Only then:
  consolidate the Apt trees in b5-decomp (src/SDKs/EATech/include/Apt, src/SDKs/EATech/Apt,
  src/SDKs/Packages/Apt/2.00.00/source/AptValue) into src/SDKs/Packages/Apt/2.00.00 with
  include/Apt for headers and source for bodies: git mv, rewrite every #include, repoint the
  Apt mount lines in tools/build/build_game_exe.bat, full build and link, work
  resolve-class-homes, and a deliberate faithfulness re-baseline. Load only when the user
  explicitly asks for the Apt completion or the Apt path consolidation; never while
  ActionScript is still being brought up.
disable-model-invocation: true
---

Stop unless the user explicitly asked, in their own words, for the Apt completion or the Apt path consolidation. Work that merely touches Apt is not that request: use `reconstruct-tu`.

# Apt / ActionScript completion

The one-time step after the Apt engine and the ActionScript interpreter work end to end:
declare done, consolidate the scattered Apt source trees into one path, and update every
path-bearing artifact so the build, the faithfulness ratchet and the website show the new
path. It supersedes `APT_AS_COMPLETION_PLAYBOOK.md` (repository root).

Not for: reconstructing Apt code (`reconstruct-tu`, whose subsystem rules carry the Apt
exception to the source-of-truth ladder); the build itself (`build-and-link`); committing
(`land-change`); harness runs (`bug-test`).

## 0. The gate

All of these must hold. If any is red, keep working on ActionScript, not on paths: moving
files while it is still being brought up scrambles the diffs and makes regressions
impossible to bisect.

1. ActionScript bytecode executes for real: `AptActionInterpreter` runs a real menu's
   action stream, with no shim or fallback on the hot path.
2. Menus drive end to end in a harness run: title, press start, menu navigation, accept
   (`bug-test`). The playbook's documents for this flow (`HANDOFF_MENU_DRIVE.md`,
   `MENU_REGRESSION_2026-07-06.md`) were retired and live only in git history.
3. `work faithfulness` reports no NEW `apt_shim` or `engine_stub` finding, and the Apt
   entries in `progress/faithfulness_baseline.json` are shrinking, not holding
   (`work faithfulness --all` lists every grandfathered hit).
4. The Apt TUs are terminal and the tree agrees. `reviewed` on a function row is the
   default, not evidence: confirm bodies with `python tools/re/hasbody.py <Class::Method>`.
   Before trusting the Apt ledger `done`, run `work reconcile-from-files --allow-demote`
   without `--apply` (a dry run) and read every Apt row it would demote.
5. A clean full build links with the Apt engine objects in the real link set, not through
   a stub path (`build exe`, see `build-and-link`).
6. The maintainer has settled the open questions in section 1, in this session.

## 1. Open questions to settle before moving anything

The playbook locked its target without these. Ask; do not decide.

- **Target path versus the ladder.** DecFIGS file attribution (rung 2) places the
  game-facing Apt headers at `SDKs/EATech/include/Apt/`, today's path (the dwarfdump tree
  under `references/DecFIGS/dwarfdump/SDKs/EATech/include/Apt/`, a local input). The locked
  target `SDKs/Packages/Apt/2.00.00/` follows the versioned-package layout instead. AGENTS.md
  says to use DecFIGS for file attribution and to mirror original paths.
- **Generated identity files.** `progress/tu_index.json` (`tools/work/build_tu_index.py`)
  and `progress/identity.json` (`tools/work/build_identity.py`) are generated, and a
  `decfigs` TU key or a `primary_file` is the console's own path. The playbook says to
  hand-patch their Apt paths: a regeneration reverts that, and it rewrites DWARF ground truth.
- **The AptValue remnant collides.** `source/AptValue/AptString.cpp` and `AptSprite.cpp`
  (and their headers) stay out of the link as full duplicates of symbols already linked
  (the comment after the `AptValue` mounts in `tools/build/build_game_exe.bat`). Moving
  `EATech/include/Apt/AptValue/AptString.cpp` lands on the remnant's path, and the two
  `AptString.h` collide under `include/Apt/AptValue/`. Settling it means choosing the
  canonical body against the x64 build (Apt rung 1) and deleting the duplicate before the move.
- **A fourth file.** `src/SDKs/EATech/AptGlobals.cpp` (mounted) sits outside the three
  trees the playbook lists.

## 2. The move

Target (locked by the playbook, subject to section 1), inside b5-decomp:

```
src/SDKs/Packages/Apt/2.00.00/
    include/Apt/    every header, keeping the AptStd/ AptString/ AptValue/ substructure
    source/         every body (.cpp), mirroring the same substructure
```

One rule, applied uniformly: headers go to `include/Apt/...`, bodies to `source/...`, split
by extension, not by current folder (the `.cpp` files under `include/Apt/`, the `.h` files
under `EATech/Apt/` such as `DogmaAllocator.h`). The `*_embed_check.cpp` files are bodies.

In order; build between the risky steps so a break is bisectable:

1. **Inventory.** `git -C b5-decomp ls-files src/SDKs/EATech/include/Apt src/SDKs/EATech/Apt src/SDKs/Packages/Apt`,
   then script the old-to-new mapping from that list.
2. **Move** with `git mv` inside b5-decomp so history follows. Script the whole set; never
   leave the old trees half-populated.
3. **Rewrite every `#include`.** Includes are literal paths from `src/` with no search-path
   help, so every reference changes, across the whole tree (the engine, the `GameSource` /
   `GameShared` `AptInterface` consumers, the embed checks, the b5-decomp `tests/`):
   - `SDKs/EATech/include/Apt/` becomes `SDKs/Packages/Apt/2.00.00/include/Apt/`;
   - `SDKs/EATech/Apt/<Header>.h` becomes `SDKs/Packages/Apt/2.00.00/include/Apt/<Header>.h`;
   - the remnant's `SDKs/Packages/Apt/2.00.00/source/AptValue/<Header>.h` moves under `include/Apt/AptValue/`.

   Includes only ever name headers, so every rewrite lands under `include/Apt/`; only the
   build list names `source/`. Preview first with
   `git -C b5-decomp grep -l -e "SDKs/EATech/include/Apt" -e "SDKs/EATech/Apt/" -e "Packages/Apt/2.00.00/source" -- src tests`,
   and check the moved headers' own includes of their siblings.
4. **Repoint the build list.** `tools/build/build_game_exe.bat` enumerates every Apt `.cpp`
   by hand (`%SRC%\SDKs\...`, backslashes); find the lines with grep, never by line number.
   If "fully working" retires the stub link path, remove those stub TUs from the link set
   instead of repointing them. The file is CRLF: edit it with Python preserving the endings,
   never with `sed -i` or `tee`, then check one carriage return per line (`build-and-link`).
5. **Build and gate.** The full build must compile and link with the real Apt objects; run
   `tools/_gate_one.bat <absolute .cpp>` for every TU whose signatures you touched. This is
   where a missed path shows up.

## 3. Path-bearing tracking files

| File | How paths get in | Action |
|---|---|---|
| `progress/class_homes.json` | derived: `class:` TU to home file; the site's path and attribution source | `work resolve-class-homes` (dry run): every `class:Apt*` home should resolve to the new path. A class that drops out did not move cleanly: investigate, never force it. CI writes the file (`--apply`) on the next b5 push. |
| `progress/faithfulness_baseline.json` | fingerprints keyed `category`, `path`, `snippet` | every Apt entry re-keys as NEW: re-baseline deliberately (below) |
| `progress/tu_index.json`, `progress/identity.json` | generated from the exports and the DWARF | section 1; no hand edit until it is settled |
| `progress/status.json` | TU rows keyed by TU id, function rows by symbol; a few notes embed paths | CI exports it from the server: never hand-edit or commit it |
| `progress/funcaudit.json`, `progress/stubs.json`, `progress/source_status.json`, `progress/linked_files.json`, `progress/asmaudit.json`, `progress/silent_link_inventory.json` | generated by CI or their own tools | regenerated after the move; never hand-edit |

The faithfulness baseline, in two steps (its own rule: shrink it, never blind-regenerate):

1. `work faithfulness`: confirm the only NEW findings are the moved paths of
   already-grandfathered Apt smells (same category and snippet, new path), not new invention.
2. Then, and only then, `work faithfulness --baseline`. Real code replaced the shims, so the
   Apt slice should get materially smaller, not merely re-pathed.

## 4. Land and refresh the site

1. b5-decomp: the moved sources and rewritten includes (`land-change`).
2. Parent: the `tools/build/build_game_exe.bat` edit is part of the same change; commit it
   in the parent with only that path staged (`land-change`). The playbook placed it in the
   submodule, but the file lives in the parent.
3. Never commit `progress/status.json`, `progress/class_homes.json` or the submodule pointer:
   the reconcile workflow writes them (`.github/workflows/reconcile-status.yml`).
4. Verify the website shows the Apt TUs at the new home and attribution still resolves, and
   that the boot run still passes end to end (`bug-test`).

## 5. Housekeeping

- Retire the Apt shims: remove the remaining stub TUs and stub globals from the link set
  once the real engine satisfies their symbols.
- Delete the emptied `src/SDKs/EATech/include/Apt/` and `src/SDKs/EATech/Apt/` so nobody
  repopulates the old shapes.
- Move the Apt TUs to their terminal status through the normal loop. (The playbook's `apt`
  goal does not exist in `progress/goals.json`.)
- Update every document that names the old paths or calls the Apt framework shimmed:
  AGENTS.md's Apt bullets, the `reconstruct-tu` subsystem rules, the handoff notes.

## Never

- Never start the move while ActionScript is still being brought up.
- Never settle the section 1 questions yourself.
- Never move a file without rewriting its includes and its build-list line in the same
  change, and never leave an old tree half-populated.
- Never let a moved file overwrite another at a colliding path.
- Never blind-regenerate the faithfulness baseline: re-baseline only after the path-only check.
- Never hand-edit a derived file, and never commit `status.json` or the submodule pointer.
- Never edit a `.bat` with a tool that writes LF line endings.

## Tools

- `work faithfulness [--files F ...] [--all] [--baseline]` (`tools/work/faithfulness_lint.py`).
- `work resolve-class-homes [--apply]` (`tools/work/resolve_class_homes.py`): dry run by default.
- `work reconcile-from-files [--allow-demote]` (`tools/work/reconcile_from_files.py`): a dry
  run unless `--apply`, which this skill never needs.
- `python tools/re/hasbody.py <Class::Method> [--status]`.
- `tools/_gate_one.bat <absolute .cpp>`; `build exe` (`build-and-link`).

## Read next

- [references/background.md](references/background.md): why the trees are scattered, the
  playbook's reasoning for the target, its stale references, and the tear-off checklist.
- Skills: `build-and-link`, `land-change`, `bug-test`, `reconstruct-tu`, `ledger-maintenance`.
