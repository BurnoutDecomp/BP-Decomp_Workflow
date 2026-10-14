# Debug-menu behavior campaign

Match every entry to ARTIST, including original no-ops and broken leftovers.
Do not revive removed features. Commit and push coherent progress in both repos,
using separate branches for unverified recovery and staging only owned paths.

## Current state

**Recovery is incomplete. Implementation, integration, review and behavior checks
are all still in progress.** The count of fully implemented but unverified entries
is unknown. Source coverage must never be reported as implementation completion.

The inventory contains **1,355 static registration sites**. Final dispositions are
**31 verified, seven original no-ops and 1,317 pending**. Loop-generated rows,
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

The normal executable now includes the reviewed scene and allocator integration
at `8cbd95c6d`. All 2,973 shipping files compile and link. Private Start/GPU graph
regressions pass 22 checks; the exact normal executable passes its ten-check
startup case, all with zero assertions/exceptions. CPU command storage and
procedural sky allocation repairs are included. See the
[current delivery receipt](native_sdk_scene_integration_20261013.json).

## Active work

| Work | State and next gate |
| --- | --- |
| Remaining 130-site source batch | Combined source review passes; integrated at `d6da13056`, normal build links, Start/GPU regressions pass. Per-entry native/backend work remains. |
| Triangle collision and occlusion | Reviewed 42-path integration and dependency/startup repairs are built and pushed at `058f17072`; startup/GPU regressions pass. Clipping passes 8 checks and frustum predicates pass 6. Renderer activation/backend/capacity/lifetime and collision menu effects remain open. |
| Resource memory map and statistics | Descriptor repair, 45-lane validation and DrawDataSize owner are integrated. Heap reporting passed source review and 18 production-allocator checks. Typed allocator consumers and resource HUD effects remain. |
| CPU profiler allocator | Reviewed, integrated and pushed. Whole-production checks 12/12; shipping build and 22 Start/GPU integration checks pass. CPU menu/HUD witness remains. |
| DLC owner and asynchronous file operations | Full Prepare, callbacks and PC directory overrides compile across 17 TUs. The missing yields and monitor flag clear are repaired and pass source review. Native startup would reach the missing XContent producer, so this batch remains unactivated. |
| Coarse scene queries and shared renderer state | Reviewed scene integration is delivered at `8cbd95c6d`. Separate query-provider checks pass 47/47, with a real failed-draw witness unavailable. The texture-switch filtering and optional anisotropic-filter coexistence repair passes bounded source review and 20 native checks; follow-on integration is pushed separately. Renderer activation and original query polarity remain open. |
| Original allocator construction | Reviewed native storage is delivered; 14 production checks pass. Original resource, 24-allocator and 27-pool creation sequences pass bounded source review and remain unactivated. The borrowed LinearMalloc repair passes source review and 38 focused checks; executable validation remains. Owned/RW lifecycle recovery passes source review and 58 focused checks in a separate pushed integration branch. Full constructor activation and GPU/DMA behavior remain open. |
| Original GameState path | Original caller, all28 Prepare cases and canonical Flyby providers are pushed at `df336bbff`; seven TUs compile and native bodies remain preserved. Fresh review/integration and initialization/activation gates remain. |
| Original Pool create path | Nine-owner source checkpoint is pushed at `0eced16a`. Review found four protocol/layout/worker-assert defects; a separate repair worker is fixing them. Original startup remains inactive. |
| Earlier integrated pages | Targeted consumer, lifetime, backend and native proofs remain. |

The historical [source-scope union](remaining_source_checkpoint_20261012.json)
records 1,351 examined sites. It includes existing code and incomplete chains and
is retained for provenance only. It does not mean 1,351 recovered controls.

Current receipts: [supporting repairs](supporting_systems_repairs_20261013.json),
[link dependencies](link_dependencies_20261013.json),
[resource Prepare](resource_prepare_source_20261013.json), and
[scene queries](scene_query_source_20261013.json). Source recovery continues on
isolated branches while review and integration continue. The normal executable
remains the tested `8cbd95c6d` build, with a healthy byte-exact backup and provenance.
The allocator/sampler/query/Stack follow-on is pushed in primary source at
`5ad64d67f`. Its 2,974-file shipping build links and three native cases pass34
checks with zero assertions/exceptions. **Inspected frames expose a texture
regression, so the tested8cbd normal artifacts were restored.** Root is isolating
the rendering change before delivery; see [delivery gate](FOLLOWON_DELIVERY_20261014.md).

Native batches have now exercised **149 bindings** across Physical Traffic,
Route Map and Traffic: 141 literal variables and eight action paths, with 1,937
actual path/value reads across 27 phases. These are registry/storage observations;
the final behavior count above remains separate. Four Route Map effects now have
final verified dispositions, and four dormant Physical Traffic settings are
classified original no-ops within the original valid-object/index domain; see the
[native checkpoint](PHYSICAL_ROUTE_NATIVE_20261014.md). Physical/conditional effects and the
Traffic page's dynamic-caption row still need suitable evidence.

Global `SAVE` hits DLC feature24's original NULL caption; an independent original
assembly review confirms this broken expansion and it remains preserved. Targeted
alias queries avoid that unrelated row. The private candidate also initializes
the real DLC manager/table without activating DLC enumeration/monitoring.

Recovery continues on the original GameState PreWorld caller/controller transport
and PoolModule create/FIFO/descriptor/host-layout family in separate branches.
The GameState provider checkpoint is pushed at `df336bbff`; neither GameState nor
Pool family is claimed integrated or behavior-verified. The four Traffic Stats
readouts pass the rebuilt candidate's56 actual reads, including nonempty
purgatory and full cleanup; final recording waits for corrected delivery.

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
