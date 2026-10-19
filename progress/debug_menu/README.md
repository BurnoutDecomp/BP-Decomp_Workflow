# Debug-menu behavior campaign

Match every entry to ARTIST, including original no-ops and broken leftovers.
Do not revive removed features. Commit and push coherent progress in both repos,
using separate branches for unverified recovery and staging only owned paths.

## Current state

**Recovery resumed on 19 October. Implementation, integration, review and
behavior checks remain unfinished.** The count of fully implemented but unverified entries
is unknown. Source coverage must never be reported as implementation completion.

The inventory contains **1,355 static registration sites**. Final dispositions are
**35 verified, seven original no-ops and 1,313 pending**. Loop-generated rows,
fifteen symbolic captions, two missing wrapper exports and native additions also
need explicit accounting; 1,355 is not the final visible-row count.

"Pending" means an unresolved registration site. It may still need source
recovery, integration, a fix, review, behavior testing, or classification as an
original leftover. It does not mean finished code awaiting a separate manual
in-game check. Related controls can share tests, and one site can create many rows.

The GPU monitor repair supplies the original twenty categories,
real native GPU timings, graph/table drawing and visibility. Three full-game cases
pass 39 checks with inspected frames and zero asserts/exceptions. See
[GPU monitors](GPU_MONITORS_20261013.md) and the
[exact native receipt](gpu_monitors_native_20261013.json).

The reported Start crash with vehicle INI settings is also repaired. The exact
normal-build case reaches driving, applies all five LOD overrides and passes ten
checks without asserts/exceptions. See [startup repair](START_CRASH_20261013.md).

The earlier F98 delivery was built from clean, pushed `f98a8cb5b`. All 2,975
shipping files compiled and linked. The same-production-source private integration
passes 60 checks across Start/GPU/Traffic and Road Rules login/save/cold restart;
the exact normal executable then passes 23 Start/GPU checks. All have zero
assertions and exceptions. Inspected native frames show the magenta texture
regression repaired. Road Rules retain both saved score types and the reset epoch.
See the [delivery receipt](runtime_owners_20261015.json) and
[Road Rules fix](../road_rules_persistence_20261014.md).

**The playable `build/game` folder now contains the Freeburn match hotfix from
dev `c2400d4f3`.** It repairs the zero-capacity PC movie graphics arena assertion
and the cache-event ordering that crashed OnlineGameOptions on car-info replies.
Fresh combined source review and the hosted shipping build pass. Matching symbols
and runtime DLLs are installed, with the previous build backed up and configuration
and saves preserved. Match creation has not yet been replayed on this executable.
See the [exact hotfix receipt](freeburn_match_hotfix_20261019.json). The earlier
[dev delivery](playable_dev_20261019.json) remains recorded for attribution.

## Active work

The [dev synchronization checkpoint](DEV_SYNC_20261019.md) reconciles the
overlapping collision recovery and current audio, hardware and online changes.
Its full build and combined source review pass. Startup and 25 collision control
readbacks pass; remaining native checks and the selected GameState repair remain
separate from normal delivery. The global END-key fallback was removed from the
active harness after the user reported interference; input helpers are stopped.
The main recovery batch is merged and pushed to gameplay `dev` at `7107bbb8c`.
The paired workflow fixes and reports are on `main`; the normal folder now has
the October 19 dev build above. New source follow-ons remain on recovery branches until their
source review and current-tree build checks pass. They do not wait for all
1,355 behavior dispositions before merging.

The five-file [GameState constructor follow-on](gamestate_lifecycle_20261019.json)
is pushed at `5e9928a06` on top of the reviewed World/movie integration. It restores
OnlineCarSelect and offline Flyby initialization, the X360 achievement-owner
initialization and the scorer's concrete pointer type. Its passing source review
is preserved; the current integration below now also passes compile/link.

The later [ModeManager/DLC batch](mode_dlc_source_20261019.json) at `bae1a8910`
also passes combined source review. It selects the full ModeManager constructor,
recovers the DLC monitor worker and the unmounted X360 SDK Futex storage fix. The
[Prepare selection](gamestate_prepare_source_20261019.json) restores
the original 28-stage GameState Prepare and retires the duplicate PC adapter.
The [current integration](gui_queue_source_20261019.json) at `3e0cbea66` changes
28 source paths over dev `37735c71d`. Source review and the hosted shipping build
pass: 2,976 TUs compile or validate from cache, and the executable links. Native
startup and streaming checks remain open. Its persistent output lifetime remains host-specific, and DLC discovery still
lacks a verified PC provider. The flag initialization is corrected in the later
runtime checkpoint below. These recovery checkpoints change no final entry dispositions and are
separate from the normal dev delivery above.

The [runtime follow-on](runtime_routing_source_20261019.json) at `4bbefd59b`
restores the original GameState constructor flag and selects full main-route
PreWorld with paired stage-8 PostWorld. Fresh review found the original flag write
through a stack-restored `this`; the earlier no-writer claim was wrong. This
four-path checkpoint is committed and pushed, with integrated review, build and
native checks still pending. The lower loading spine and complete GUI bridge
remain open. The normal folder contains the separate dev hotfix `c2400d4f3` above.

The GUI output now retires after its sound/network snapshot, preventing old
streaming replies from being reused while stepping. GUI65's fake unpause is
removed; real completion requires Traffic, RaceCar, WorldGraphics and GUI replies.
Its loading-screen presentation stand-in remains. The original one-shot request
can still be lost while stepping; no retry or synthetic reply was introduced.
The recovered DLC monitor bodies are preserved in one unmounted TU until their
genuine XContent backend and worker lifetime are ready. Its selected constructor
and typed lock owner remain; the unmounted X360 thread implementation is separate
from the runtime's forked vendor EAThread provider.

[Branch cleanup](branch_cleanup_20261019.json) removed 23 retired campaign
branches locally and on GitHub. Their exact tips remain recorded and reachable
from dev/main. Retire merged, unused branches as work lands; keep active or
unmerged work and reuse current branches for later checkpoints.

The user needs responsive browsing and YouTube during this campaign. Heavy
local workers and game tests are currently stopped. The locked build wrapper defaults
to one compiler, Idle priority and two logical CPUs, with the private integration
builder using the same limits. Keep one expensive local job at a time; source
reasoning/review may run in parallel. Do not run game tests alongside compilation
or multiple game instances together while the PC is in use. Any resumed game
test must use only the instance-scoped input events.

Full candidate builds can instead use the manual **Check Candidate Build**
workflow with an exact 40-hex `b5_commit`. It runs the canonical shipping build
on GitHub-hosted Windows 2022, checks toolchain/source/output attribution and
keeps a one-day artifact with matching runtime DLLs. Its current-dev run passed;
build success does not establish gameplay parity. Refresh the playable folder
after meaningful dev merges, preserving a previous build. Reuse current integration
branches rather than creating checkpoints.

| Work | State and next gate |
| --- | --- |
| Remaining 130-site source batch | Combined source review passes; integrated at `d6da13056`, normal build links, Start/GPU regressions pass. Per-entry native/backend work remains. |
| Triangle collision and occlusion | Reviewed 42-path integration and dependency/startup repairs are built and pushed at `058f17072`; startup/GPU regressions pass. Clipping passes 8 checks and frustum predicates pass 6. Renderer activation/backend/capacity/lifetime and collision menu effects remain open. |
| Resource memory map and statistics | Descriptor repair, 45-lane validation and DrawDataSize owner are integrated. Heap reporting passed source review and 18 production-allocator checks. Typed allocator consumers and resource HUD effects remain. |
| CPU profiler allocator | Reviewed, integrated and pushed. Whole-production checks 12/12; shipping build and 22 Start/GPU integration checks pass. CPU menu/HUD witness remains. |
| DLC owner and asynchronous file operations | Full Prepare, callbacks and PC directory overrides compile across 17 TUs. The missing yields and monitor flag clear are repaired and pass source review. The real XContent backend and worker lifetime remain unresolved. Monitor bodies are preserved in an unmounted TU; full DLC Prepare remains unselected. |
| Coarse scene queries and shared renderer state | Sampler/query/Stack follow-on is delivered in AC3. The canonical packed sampler producer and Font flags repair pass source review, a 16-check native fixture and inspected game frames. Query-provider checks pass 47/47, with a real failed-draw witness unavailable. Renderer activation and original query polarity remain open. |
| Original allocator construction | Reviewed native storage and LinearMalloc/RW lifecycle repairs are delivered. Original resource, 24-allocator and 27-pool sequences remain unactivated. Full constructor activation and GPU/DMA behavior remain open. |
| Original GameState path | Original caller, all28 Prepare cases, Flyby providers and earlier snapshot repair are delivered. Selected consumers, World status, movie arena, constructor/ModeManager, Prepare and GUI handoff follow-ons pass source review. The 28-source-path integration at `3e0cbea66` passes hosted compile/link; native startup/streaming remains open. DLC monitor and X360 thread implementation stay unmounted. The [25-row source matrix](gamestate_source_matrix_20261019.json) records 12 existing paths, 5 recovered renderer paths and 8 unresolved rows, all native-unverified. The later4bb runtime checkpoint above remains unverified; full lifecycle activation is still open. |
| Original Pool create path | All four protocol/layout/worker-assert findings are repaired and integrated at `f98a8cb5b`; source review and 41 current-canonical production checks pass. NativePC routing remains selected; original startup remains inactive. |
| ImmediateMode and Traffic readers | Member-instantiation ownership, Vector3 boost-bar API and Anarchy-distance initializer are integrated at `f98a8cb5b`. All52 recorded Traffic scalar candidates are false aliases; indirect/dynamic uses remain unresolved. Graphics query callers at `b49d37a5c` pass fresh source review; their host selection remains disabled while the original allocator provider is recovered. |
| Earlier integrated pages | Targeted consumer, lifetime, backend and native proofs remain. |

The historical [source-scope union](remaining_source_checkpoint_20261012.json)
records 1,351 examined sites. It includes existing code and incomplete chains and
is retained for provenance only. It does not mean 1,351 recovered controls.

Current receipts: [supporting repairs](supporting_systems_repairs_20261013.json),
[link dependencies](link_dependencies_20261013.json),
[resource Prepare](resource_prepare_source_20261013.json), and
[scene queries](scene_query_source_20261013.json). Source recovery continues on
isolated branches while review and integration continue. The earlier5ad build
passed automated checks but failed actual frame inspection, so its normal
artifacts were restored while the regression was isolated. The repaired AC3 and
subsequent F98 normal builds pass checks and bounded visual inspection; the failed
candidate, comparison runs and backup remain retained. See
[delivery gate](FOLLOWON_DELIVERY_20261014.md).

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
alias queries avoid that unrelated row. The normal build also initializes
the real DLC manager/table without activating DLC enumeration/monitoring.

The four Traffic Stats readouts now have final verified dispositions. Corrected
normal delivery retains56 actual reads across14 phases, including four phases
with nonempty purgatory and cleanup0/400/0/0. Other Traffic controls remain pending.
The next [integration of selected consumers](SELECTED_CONSUMERS_20261015.md) combines
the eight-file GameState and three-file graphics checkpoints at `5b4d44e90`.
The repaired 14-file checkpoint at `66613d8d3` compiles and links, but native
Start/GPU checks freeze in the junkyard: the public world-streaming status copy
is missing. The candidate was not delivered. Recovery has resumed; this earlier failed candidate remains held. The normal
executable remains the inspected `f98a8cb5b` build.
Original lifecycle activation and the 23 unresolved Traffic reader sites remain open.

Correction to earlier warning descriptions: the C4661 messages came from
whole-class explicit instantiation requests whose bodies live in other TUs, plus
an unattested overload request. They did not establish eight missing bodies.
The ImmediateMode repair is delivered and its eight warnings are gone. The broad
normal rebuild still records 74 warnings in existing code outside that family,
including three Sound queue instantiation warnings. See the
[runtime-owner checkpoint](RUNTIME_OWNERS_20261015.md).

## Pipeline

Keep two source workers recovering exclusive subsystem slices while Root
integrates/tests/publishes and one Sol reviewer handles a combined batch.
Use Luna Max for suitable recovery work and Sol for the more complex chains.
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
