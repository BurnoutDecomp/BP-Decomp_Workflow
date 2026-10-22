# Debug-menu behavior campaign

Match every entry to ARTIST, including authentic no-ops and broken leftovers.
Recovery, integration, review and behavior checks remain active.

## Playable build

Launch `build/game/Burnout_PC.exe`. The installed **8fec93bd** build combines
the GUI/action/movie and profile repair with current-dev Traffic and the shared
DLC reader. It passed hosted compile/link and all selected GUI/profile checks.
The exact executable passed real Start/sign-in, junkyard/world/HUD,68.7m of
driving, local online Freeburn/Create Event, editing/moving/placing checkpoint1
in a seven-checkpoint preset and returning with Back. No asserts/exceptions.
The predecessor separately added a new checkpoint. All twelve matching build
files are installed; config, nine profiles and their modification times were
preserved at delivery, with a backup of the old build. [Delivery and limits](gui_dev_playable_delivery_20261022/DELIVERY.json).

The earlier **b82350534** delivery checks passed:

- Returning-save junkyard, default car/livery acceptance and exit to the world.
- Measured throttle response: 5.4 metres and 19.8 mph in the final confirmation.
- Owned one-player online Freeburn; visible Create Event options and HelpBar.
- Rounds change/restore, original preset route map, Summary and Done.
- Actual GUI257 submission, successful server update, and matching scalar/route
  readback. The returned lobby visibly shows Next Up Race and one round.
- Zero asserts/exceptions, clean native exit. Both native attempts and their
  attributable frames are retained. Hosted build: 2,980 TUs, 519 focused checks
  and 11 intentional failure controls.

Peer joining, a complete race, custom-route Done/save persistence and further
mode/preset variants remain to test. This delivery does not certify every debug control.
[Earlier crash and recovery evidence](playable_candidate_progress_20261021.json).

A later user session exposed **RWAC sound allocation corruption**. It remains unresolved in the installed package. The private diagnostic passed
hosted capacity checks and its original-source failure control; the short delivery checks did not establish long-session stability.
[Latest crash, Traffic run and cleanup](traffic_cleanup_crash_checkpoint_20261021.json).

## Campaign counts

The static inventory contains **1,355 unique original registration-site IDs**. Final dispositions are **46 verified, seven original no-ops and 1,302 pending**. That is 53/1,355 (3.9%) with a final behavior disposition. The number fully implemented but awaiting verification is still unknown.

Seven additional GUI visibility/gating sites passed retained-native review on exact91a. The original twelve-control aggregate remains FAIL; four inconclusive controls stay pending. A separately observed SatNav outline remains pending because its colour differs from the original assembly. [Per-site scope and limits](gui12_retained_native_subset_20261023/CHECKPOINT.json).

Recorded source-progress coverage is separate from behavior completion:

- **1,196 sites (88.3%)** are in recorded bounded source-review cohorts and repair supplements. This is reviewed-source-cohort coverage, not proof of a complete consumer chain or a current-head re-review.
- **26 additional sites** have existing registration/consumer bodies audited in the integration checkout; compile, fresh review and native evidence remain pending.
- **129 sites** are covered only by broader source/audit scope outside those batches: nine have explicit audit-only packet IDs, while 120 appear in the coverage set without a per-site packet reference.
- **Four sites** were outside that saved snapshot. All four now have source audits; one shared DLC reader needed repair. Its private hosted build passed, while native DLC behavior remains pending.

The source/audit checkpoint covers 1,351/1,355 sites (99.7%), including unresolved consumers. The 1,196 reviewed sites plus 26 existing-body audits give 1,222/1,355 (90.2%) with source/body evidence, not a completed-control count. Neither 10% nor 90% is a defensible actual implementation percentage; the actual count remains unknown. See the [source coverage checkpoint](source_coverage_checkpoint_20261021.json) for the count definitions and evidence limits.

## Continuing source work

**GUI/action/movie and online recovery:** **8fec93bd** is installed and
merged/pushed to dev. Its exact2,994-file hosted build and selected profile,
keyboard, licence, GUI lifecycle, HUD and delivery fixtures passed, including
original-code failure controls. Independent review checked the native pixels,
57 inputs, motion and cleanup. [Exact native evidence](gui_dev_playable_delivery_20261022/REVIEW.md).
This supporting-flow delivery adds no debug-site dispositions and does not
certify peer races, route save/reload, every UI hint, native DLC behavior or
long-session audio. A newer private Flowtype override recovery **0bfa585e**
is committed/pushed but is absent from this package and still needs its gates.

**Route snap capacity checkpoint:** The 289-bound one-file source commit **6b66e5984f6f21ea47d1fa62a2ec61c9511640c9** passed hosted build run [39654339193](https://github.com/BurnoutDecomp/BP-Decomp_Workflow/actions/runs/39654339193). Native placement/movement and Back passed; the matching normal package is installed and merged to dev. Done/save persistence and a complete multiplayer race remain unverified. This supporting-flow repair adds no verified debug-site dispositions.

**Traffic follow-up:** **d9de0ab1** is merged/pushed to dev. The original
fifteen-hull branch now has reviewed source plus actual4 ->15 ->4 decision,
drawing and restoration evidence, with matching visible PVS cells. This
is the existing #0086 disposition. A separate retained run04 review passes
exactly #0001 Turn traffic off, #0057 Draw active hulls and #0088 Render
special perfmons against exact B5 source d9de0ab1d395425eb39d0fdbb5e70f93235d601a
(hosted run 39736578561). Its flag reads, population samples, completed PVS
consumer receipt and reviewed pixels are phase-adjacent, not same-frame
correlation. The historical Traffic74 aggregate remains **FAIL**, all 74 CSV
`pre_run_status` rows remain `PENDING_NOT_RUN`, and `runtime_consumer_verified`
remains 0. Sites #0045/#0046/#0047/#0050 stay excluded/pending; this adds no
new #0086 or extra 15-hull-cycle credit. The source is included in installed
8fec93bd; a newer private Flowtype source commit 0bfa585e is not represented as
part of that package. [Three-control evidence](traffic_three_control_evidence_20261022/CHECKPOINT.md).
[Existing #0086 evidence](traffic_worst_case_evidence_20261022/CHECKPOINT.json).

The action translator covers 188 unique IDs across 189 labels. That is source coverage, not 188 verified debug controls. Coherent checkpoints are committed and pushed frequently; reviewed work merges in batches.

## Other reported issues

[Road Rules persistence](../road_rules_persistence_20261014.md) was repaired and
checked through saving, login and cold restart. The earlier magenta-rendering
and Start/vehicle-INI regressions have separate evidence in
[the runtime receipt](runtime_owners_20261015.json) and
[startup report](START_CRASH_20261013.md).

The harness's global END fallback was removed. Compilation/fixtures use hosted
CI. Native windows use isolated profiles, mute, low priority and scoped inputs.

[Earlier checkpoint history](HISTORY_BEFORE_INTRO_REPAIR_20261020.md)

Scratch cleanup removed 19,080 redundant old frames (105.1 GB), keeping five
samples per old run plus the active debug-menu and Road Rules evidence.
