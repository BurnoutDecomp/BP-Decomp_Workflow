# Apt completion: background

Depth for [`../SKILL.md`](../SKILL.md). The procedure is there; this file holds the reasoning
the playbook gave, what in it has gone stale, and its tear-off checklist.

## Why the Apt paths are scattered

The one Apt library sits under three path shapes inside b5-decomp, a fossil of the
versioned middleware package path (`Packages/Apt/2.00.00`) being partly relocated under `SDKs/EATech/`
during the decompilation:

| Path (inside b5-decomp) | Holds | Notes |
|---|---|---|
| `src/SDKs/EATech/include/Apt/` | the bulk of the engine: interpreter, `AptCIH`, `AptMovie`, `AptArray`, the characters, `AptStd/`, `AptString/`, `AptValue/` | holds both `.h` and `.cpp` despite its `include/` name |
| `src/SDKs/EATech/Apt/` | init and bootstrap, the GC (`AptValueGC*`), `DogmaAllocator`, the `Apt*MembersIndex` tables, `AptMath` | |
| `src/SDKs/Packages/Apt/2.00.00/source/AptValue/` | `AptSprite`, `AptString` | an un-migrated remnant at the package path; out of the link (duplicates) |

Count the files from `git -C b5-decomp ls-files` when you start; the playbook's counts were
a snapshot.

A versioned package keeps its public headers under `include/Apt/...` and its bodies under
`source/...`. The decompilation flattened most of that into `SDKs/EATech/`, left
the `AptValue` remnant behind, and let `.cpp` files spill into `include/Apt/`.

## The playbook's case for `Packages/Apt/2.00.00`

- It stops the tree misreporting where the middleware lived and restores the
  versioned-package identity (`Apt 2.00.00`).
- The remnant already at that path stops being an orphan: everything moves to it.
- The current `include/Apt/{AptStd,AptString,AptValue}` substructure maps one to one onto
  the package's `include/Apt/`, so headers move without renames.

Against it, and unanswered by the playbook: DecFIGS attributes the
game-facing Apt headers to `SDKs/EATech/include/Apt/` (no Apt `.cpp` appears in the DecFIGS
DWARF at all: the library was prebuilt). That is why the skill makes the target a question
for the maintainer rather than a given.

## What in the playbook is stale

| Playbook says | Now |
|---|---|
| gate references `HANDOFF_MENU_DRIVE.md`, `MENU_REGRESSION_2026-07-06.md` | both retired (in git history): the menu drive was declared complete and the regression long fixed |
| housekeeping reconciles `ONE_TO_ONE_REMAINING.md` | retired the same way; live tracking is the ledger and the faithfulness baseline |
| stub link path `AptRenderLinkStubs.cpp` | retired in b5-decomp ("Retire five of the six link-stub files with real bodies"); `AptGlobals.cpp` and `AptRenderHooks.cpp` remain |
| "no `_embed_check` fallbacks on the hot path"; delete them after | the Apt `*_embed_check.cpp` files are header ODR/embed checks flagged as PC leaves and are not in the exe build list; they are not interpreter fallbacks. Move and rewrite them with the rest; deleting them is a separate decision |
| the Apt block of the batch file is at a fixed line range | it moved; grep for `SDKs\EATech` |
| two remnants sharing the `AptString.cpp` basename clobber each other's object | `tools/build/compile_exe.py` names each object by basename plus a path hash, so objects no longer collide; the duplicate symbols and the source path collision remain |
| push `class_homes.json` by hand so the site shows the path | the reconcile workflow regenerates and publishes it on every b5 push |
| commit the batch-file edit inside the submodule | the file is in the parent; it lands as a parent mount commit (`land-change`) |
| mark the `apt` goal done | no such goal in `progress/goals.json` |
| `tu_index.json`, `status.json` and `identity.json` carry many Apt path keys | nearly all Apt TUs are `class:` or `module:` TUs with no path; read the files for the real set, and see the skill's section 1 before editing generated files |

## Tear-off checklist

```
[ ] Gate green: ActionScript runs real menus, menus drive end to end, faithfulness clean,
    Apt TUs terminal per the tree, the exe links with the real Apt objects
[ ] Maintainer settled: target path, generated-file policy, AptValue remnant, AptGlobals.cpp
[ ] git mv every file (headers -> include/Apt, bodies -> source), no tree half-populated
[ ] Every #include rewritten across src/ and tests/ (engine + AptInterface consumers + embed checks)
[ ] tools/build/build_game_exe.bat Apt mounts repointed (CRLF preserved), stub TUs dropped if retired
[ ] Full build + link green; _gate_one.bat on any TU whose signatures changed
[ ] work resolve-class-homes dry run: every class:Apt* resolves to the new path
[ ] work faithfulness (only re-pathed Apt smells NEW), then work faithfulness --baseline (shrinks)
[ ] Boot run still passes end to end
[ ] b5-decomp commit + parent mount commit; CI reconciles status.json, class_homes.json, pointer
[ ] Website shows the new path and attribution resolves
[ ] Shims retired, old directories deleted, ledger and documents updated
```
