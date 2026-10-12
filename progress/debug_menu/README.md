# Debug-menu behavior campaign

Match every entry to ARTIST, including original no-ops and broken leftovers.
Do not revive removed features. The user authorizes commits and pushes in both
repositories after meaningful progress. Stage only owned files; leave the general
status mirror and submodule pointers to their existing reconciliation workflow.

`entries.json` inventories 1,354 original static registration sites in 91 functions
and all 64 named debug activation functions. Loops/delegated serialisers generate
additional rows; 15 captions are symbolic and two wrapper exports are missing.
PC additions require their own consumer audits. This is not a final visible-row count.

`verdicts.json` holds final behavior dispositions: `pending`, `verified`,
`original-noop` or `original-broken`. Final states need notes and evidence.
`batches.json` separately records recovered/source-reviewed site sets. Existing code,
registration, saved settings or a clean boot alone do not establish behavior.

## Current progress

Source recovery/audit packets cover **654 of 1,354 static sites**: the earlier
310-site scope, VehicleManager/Deformation 131, Physics Props 16,
Environment/Graphics 148, Power Parking 18, Reset Player 8 and Progression 23.
These packets include unfinished consumer/backend work. They are source progress,
not a claim that 654 controls work in game. **700 sites remain outside the packets.**

The earlier 310 sites and combined 147-site vehicle/props source scope are
reviewed. Three physics discrepancies were repaired; the independent supplement
and 35 focused CPU checks pass. Native and hardware-seed limits remain open.
The 148-site Environment/Graphics and
26-site existing-body audits and 23-site Progression recovery await review.
Progression passes its four-TU compile gate. All four changed Graphics C++ TUs
compile after the enum typing fix. Handling has another 28 committed
registrations with partial consumer recovery; known render/HUD gaps keep those
outside the 654-site count.

Final dispositions are **25 verified and three original no-ops**, including the
original empty Reset Sensors action. **1,326 static sites** and the expanded
dynamic rows still need final dispositions. These stages overlap; do not add them.

The 150-site Traffic/AI checkpoint passes 737 grouped checks. Its native Traffic
case passes 7/7 automatic checks; Physical/Route passes 8/9, including 507 saved
value reads. Visual and conditional consumer proof remains open. Registry,
boot and clean logs do not certify every control.

## Published batches

| Batch | Scope | Evidence |
| --- | --- | --- |
| 1 | Five Tailgate tunables | [Tailgate](TAILGATE_20261011.md) |
| 2 | Track-position overlay and shared 3D buffer/sphere | [Reset history](RESET_HISTORY_20261011.md) |
| 3 | Forced lobby spawn; original Apply Ram/Magnitude no-ops | [Spawn and dormant controls](FORCE_SPAWN_RAM_20261011.md) |
| 4 | Six race-car HUD/statistics entries and shared text/2D rendering | [Race-car HUD](RACECAR_HUD_20261011.md) |
| 5 | Initial Sound source recovery and Challenge latch; Challenge runtime pending | [Initial recovery](SOUND_CHALLENGE_20261011.md) |
| 6 | Entire Sound page, Marked Man tuning and Takedown diagnostics | [Large batch](SOUND_BATCH_20261011.md) |
| 7 | Original audio clock units; statistics/held-reset/graph follow-up | [Clock and history](SOUND_CLOCK_20261011.md) |
| 8 | Traffic, Physical traffic and Route Map source recovery; native verification in progress | [Traffic/AI batch](TRAFFIC_BATCH_20261011.md) |

Earlier presentation/navigation work is in `b5-decomp/docs/DEBUG_MENU_REPORT.md`;
import its behavior verdicts only after checking the evidence.

## Continue

The user's latest instruction is a continuous recovery pipeline: **keep agents
recovering new systems while completed batches are reviewed and tested**. Do not
make the recovery workers wait for a validation round. Large page/subsystem batches
of roughly 130 sites are preferred; unverified recovery may accumulate for later
checks. Commit and push coherent consumer/page increments frequently to separate recovery
branches, including unverified work; do not wait for a whole page or its tests.
Keep the reviewed integration branch separate until its required checks pass.
Publish meaningful progress to both repos with its actual validation state.

With the current four-agent limit, root integrates/publishes, two Luna Max workers
recover in exclusive b5 checkouts, and one Sol slot handles difficult shared
systems or the combined review. No Astra. Only one combined reviewer per batch.
Freeze each handed-off source set while its worker moves to a distinct next slice.
Keep source-ready, reviewed, compiled and native-verified states separate.

Active page lanes now cover ShadowMap/Effects/SceneManager **138** new sites and
RaceCar/GameState/Progression/PowerParking/ResetPlayer **116** new sites. Original
source-only preparation helpers are separately checkpointed, with unresolved
resource-core/startup links. Handling consumers are ready for frozen integration/review. The original LOD
registration/PC duplicate follow-up is compiled and CPU-tested; native proof remains open.

Sound clock calibration is repaired and witnessed; the original coefficients
and balancer units remain intact. Remaining work:

- Resolve remaining Sound no-reader/leftover findings and targeted behavior gaps;
  hold/spin did not visibly affect the captured player car, and revenge/last-
  takedown data was not populated. Do not invent effects to satisfy a caption.
- Continue race-car, AI, renderer/environment, game data, state, GUI, replays and
  physics pages. Enumerate symbolic/loop-generated rows and native additions.

Use ARTIST assembly for behavior, DecFIGS for declarations and old source for
style. Assign exclusive files to specialists, collect complete page maps, and
use one combined source reviewer. Group related CPU tests and native scenarios
after integration; shared render/audio primitives do not certify every caller.
Publish recovered code, reproducible tests and evidence narrowly to both repos;
state pending review/build/runtime work plainly rather than inflating completion.
The goal is complete only when every original and native entry has a supported
disposition. The active user goal remains open.

The user authorized model routing and parallel workers on 2026-10-11: no Astra.
Luna handles bounded page/consumer recovery; Sol handles shared systems and
combined reviews. Root owns integration, shared build/run locks and publication.

Regenerate: `python tools/re/debug_menu_inventory.py`.
Parser checks: `python -m unittest discover -s tools/re -p test_debug_menu_inventory.py`.
