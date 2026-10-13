# Debug-menu behavior campaign

Match every entry to ARTIST, including original no-ops and broken leftovers.
Do not revive removed features. Commit and push coherent progress in both repos,
using separate branches for unverified recovery and staging only owned paths.

## Current state

**Recovery is incomplete. Implementation, integration, review and behavior checks
are all still in progress.** The count of fully implemented but unverified entries
is unknown. Source coverage must never be reported as implementation completion.

The inventory contains **1,355 static registration sites**. Final dispositions are
**27 verified, three original no-ops and 1,325 pending**. Loop-generated rows,
fifteen symbolic captions, two missing wrapper exports and native additions also
need explicit accounting; 1,355 is not the final visible-row count.

The latest verified repair is the GPU monitor chain: original twenty categories,
real native GPU timings, graph/table drawing and visibility. Three full-game cases
pass 39 checks with inspected frames and zero asserts/exceptions. See
[GPU monitors](GPU_MONITORS_20261013.md) and the
[exact native receipt](gpu_monitors_native_20261013.json).

The reported Start crash with vehicle INI settings is also repaired. The exact
normal-build case reaches driving, applies all five LOD overrides and passes nine
checks without asserts/exceptions. See [startup repair](START_CRASH_20261013.md).

The normal executable now includes the reviewed CPU allocator repair at
`e4acac75f`. Its shipping build passes; Start and GPU graph integration regressions
pass 22 checks with zero assertions/exceptions. CPU menu/HUD behavior still needs
its own witness. See [CPU allocator](CPU_ALLOCATOR_20261013.md).

## Active work

| Work | State and next gate |
| --- | --- |
| Remaining 130-site source batch | Combined source review passes; integrated at `d6da13056`, normal build links, Start/GPU regressions pass. Per-entry native/backend work remains. |
| Triangle collision and occlusion | Original review failed. G1-G10 repairs, explicit owner seams and constructor calls are pushed and compile; repair review runs alongside recovery. Clipping passes 8 checks; old source fails 5. Renderer state/backend/capacity/lifetime remain open. |
| Resource memory map and statistics | Original review found one descriptor mismatch. Regenerated repair, 45-lane validation and exact DrawDataSize owner compile; supplement review running. Typed allocator consumers and native checks remain. |
| CPU profiler allocator | Reviewed, integrated and pushed. Whole-production checks 12/12; shipping build and 22 Start/GPU integration checks pass. CPU menu/HUD witness remains. |
| DLC owner and asynchronous file operations | Owner/Prepare, canonical AsyncOp, typed patch events, repeated pump and disk-status chain compile across 8 TUs. Source review and missing discovery/backend/full Prepare work remain. |
| Coarse scene queries | Line/Volume/Frustum consumers, payloads, backend entry and event IDs pushed; 4 TUs compile. Source review/native checks pending. Unattested plain producer APIs were not invented. |
| Earlier integrated pages | Targeted consumer, lifetime, backend and native proofs remain. GameState's recovered full update still needs the PC caller integration. |

The historical [source-scope union](remaining_source_checkpoint_20261012.json)
records 1,351 examined sites. It includes existing code and incomplete chains and
is retained for provenance only. It does not mean 1,351 recovered controls.

Current receipts: [supporting repairs](supporting_systems_repairs_20261013.json),
[resource Prepare](resource_prepare_source_20261013.json), and
[scene queries](scene_query_source_20261013.json). Source recovery continues on
isolated branches while the combined repair review runs.

## Pipeline

Keep two Luna Max source workers recovering exclusive subsystem slices while
Root integrates/tests/publishes and one Sol reviewer handles a combined batch.
No Astra. Do not make source workers wait for review or native checks. Prefer
large page/subsystem batches around 130 sites; commit/push smaller coherent
increments frequently, including source that is explicitly unverified.

Use ARTIST assembly for behavior and ABI, DecFIGS for declaration shape, and old
source only for style. Freeze each handed-off source set while its author moves
to a distinct slice. Preserve unknown WIP, shared build/run locks and provenance.
Use exactly one combined reviewer for a batch. General status mirrors and
submodule pointers remain with their existing reconciliation workflow.

`entries.json` is the inventory; `verdicts.json` holds final behavior dispositions.
`batches.json` tracks overlapping source/review scopes. Registration, saved values,
compile success and a clean boot do not establish each control's behavior. The
goal is complete only when every original/native entry has a supported disposition.

## Evidence index

- [Tailgate](TAILGATE_20261011.md), [reset/history](RESET_HISTORY_20261011.md),
  [spawn and dormant controls](FORCE_SPAWN_RAM_20261011.md), [race-car HUD](RACECAR_HUD_20261011.md).
- [Sound](SOUND_BATCH_20261011.md), [audio clock/history](SOUND_CLOCK_20261011.md),
  [Traffic/AI](TRAFFIC_BATCH_20261011.md).
- [319-site source review](SOURCE_BATCH_319_20261012.md),
  [Effects/Director](EFFECTS_DIRECTOR_130_20261012.md), [remaining 130](REMAINING130_20261013.md),
  [GameState caller gaps](GAMESTATE_UPDATE_CHAIN_20261012.md),
  [Resource windows](RESOURCE_WINDOWS_20261012.md).
- [Supporting systems](SUPPORTING_SYSTEMS_20261013.md), [CPU allocator](CPU_ALLOCATOR_20261013.md), [memory map](MEMORY_MAP_STARTUP_20261013.md), [scene manager](SCENE_MANAGER_20261012.md),
  [environment/graphics](ENVIRONMENT_GRAPHICS_20261012.md),
  [pipeline checkpoints](PIPELINE_CHECKPOINTS_20261012.md).

Regenerate inventory: `python tools/re/debug_menu_inventory.py`.
Parser checks: `python -m unittest discover -s tools/re -p test_debug_menu_inventory.py`.
