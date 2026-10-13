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

"Pending" means an unresolved registration site. It may still need source
recovery, integration, a fix, review, behavior testing, or classification as an
original leftover. It does not mean finished code awaiting a separate manual
in-game check. Related controls can share tests, and one site can create many rows.

The latest verified repair is the GPU monitor chain: original twenty categories,
real native GPU timings, graph/table drawing and visibility. Three full-game cases
pass 39 checks with inspected frames and zero asserts/exceptions. See
[GPU monitors](GPU_MONITORS_20261013.md) and the
[exact native receipt](gpu_monitors_native_20261013.json).

The reported Start crash with vehicle INI settings is also repaired. The exact
normal-build case reaches driving, applies all five LOD overrides and passes nine
checks without asserts/exceptions. See [startup repair](START_CRASH_20261013.md).

The normal executable includes the reviewed supporting integration and repairs
at `058f17072`. All 2,972 shipping files compile and link; Start and GPU graph
integration regressions pass 22 checks with zero assertions/exceptions. The
first integration exposed a startup allocator handoff bug; its original caller
and bounded native-provider repairs pass review and those regressions. See
[latest integration](SUPPORTING_INTEGRATION_20261013.md).

## Active work

| Work | State and next gate |
| --- | --- |
| Remaining 130-site source batch | Combined source review passes; integrated at `d6da13056`, normal build links, Start/GPU regressions pass. Per-entry native/backend work remains. |
| Triangle collision and occlusion | Reviewed 42-path integration and dependency/startup repairs are built and pushed at `058f17072`; startup/GPU regressions pass. Clipping passes 8 checks and frustum predicates pass 6. Renderer activation/backend/capacity/lifetime and collision menu effects remain open. |
| Resource memory map and statistics | Descriptor repair, 45-lane validation and DrawDataSize owner are integrated. Heap reporting passed source review and 18 production-allocator checks. Typed allocator consumers and resource HUD effects remain. |
| CPU profiler allocator | Reviewed, integrated and pushed. Whole-production checks 12/12; shipping build and 22 Start/GPU integration checks pass. CPU menu/HUD witness remains. |
| DLC owner and asynchronous file operations | Full Prepare, callbacks and PC directory overrides compile across 17 TUs. The missing yields and monitor flag clear are repaired and pass source review. Native startup would reach the missing XContent producer, so this batch remains unactivated. |
| Coarse scene queries and shared renderer state | Coarse consumers, shared state/caller guards, native SM3 pairs and wrappers compile. White-texture format and sampler-store repairs pass source review. Native sampler application and predication remain no-ops. |
| Original allocator construction | Canonical globals/wrappers and RW placement/adoption are recovered on a source branch, with no startup activation. Six production TUs compile; 14 storage/ownership/rollback checks pass. Fresh source review remains. See [allocator recovery](ALLOCATOR_CONSTRUCT_20261013.md). |
| Earlier integrated pages | Targeted consumer, lifetime, backend and native proofs remain. GameState's recovered full update still needs the PC caller integration. |

The historical [source-scope union](remaining_source_checkpoint_20261012.json)
records 1,351 examined sites. It includes existing code and incomplete chains and
is retained for provenance only. It does not mean 1,351 recovered controls.

Current receipts: [supporting repairs](supporting_systems_repairs_20261013.json),
[link dependencies](link_dependencies_20261013.json),
[resource Prepare](resource_prepare_source_20261013.json), and
[scene queries](scene_query_source_20261013.json). Source recovery continues on
isolated branches while review and integration continue. The normal executable
is the tested `058f17072` build, with a byte-exact healthy backup and provenance.
The next [combined source review](loading_scene_review_20261013.json) covers
50 files across loading/filesystem and scene/renderer work. Its first verdict is
fail on five source defects; all five repairs now pass bounded source review while
allocator recovery, native boundary audits and integration preparation continue. The tested normal
executable remains `058f17072` until the next coherent batch passes its gates.

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
