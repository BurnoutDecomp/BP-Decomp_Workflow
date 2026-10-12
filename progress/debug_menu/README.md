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

Source recovery/audit packets cover **787 of 1,354 static sites**; **567 remain
outside those packets**. The exact, non-overlapping IDs are in `batches.json`.
RaceCar57 adds 42 newly audited sites and records 15 previously carried sites;
ShadowMap adds 34. These packets include unresolved readers and backend work.
They measure source coverage, not working controls.

One Sol reviewer is checking the combined **319-site batch**: the 199-site
Environment/Graphics, Progression and Handling repairs, plus SceneManager29,
ShadowMap34 and RaceCar57. Changed groups compile. The prior199 review failed
eight findings; its repair candidates pass 54 environment/grip and 143 renderer
checks, with negative controls. The current review has found additional draw
and numeric discrepancies; repairs are pushed separately while it continues.
See [the current checkpoint](SOURCE_BATCH_319_20261012.md).

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

The Luna lanes are recovering Director/Replay consumers and original occlusion
query construction. Effects75 is frozen separately, awaiting integration and
review; it is excluded from 787. The original GameState update chain is committed
on its own branch, with full PreWorldUpdate and native caller work still pending.
Root repairs, integrates and runs grouped checks while those lanes continue.

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
