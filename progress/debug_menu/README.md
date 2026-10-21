# Debug-menu behavior campaign

Match every entry to ARTIST, including authentic no-ops and broken leftovers.
Recovery, integration, review and behavior checks remain active.

## Playable build

Launch `build/game/Burnout_PC.exe`. The **6b66e598** checkpoint-editor fix is installed
there and merged/pushed to dev. It restores the original 289-position cursor
buffer. Native checks added, moved and placed a checkpoint, observed distance/time
recalculation, and returned to Create Event without an assert or exception.
All twelve matching build files are present; config, saves and modification times
were preserved. [Checkpoint fix and delivery](checkpoint_editor_hotfix_20261021.json).

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

The static inventory contains **1,355 unique original registration-site IDs**. Final dispositions are **35 verified, seven original no-ops and 1,313 pending**. That is 42/1,355 (3.1%) with a final behavior disposition. The number fully implemented but awaiting verification is still unknown.

Recorded source-progress coverage is separate from behavior completion:

- **1,196 sites (88.3%)** are in recorded bounded source-review cohorts and repair supplements. This is reviewed-source-cohort coverage, not proof of a complete consumer chain or a current-head re-review.
- **26 additional sites** have existing registration/consumer bodies audited in the integration checkout; compile, fresh review and native evidence remain pending.
- **129 sites** are covered only by broader source/audit scope outside those batches: nine have explicit audit-only packet IDs, while 120 appear in the coverage set without a per-site packet reference.
- **Four sites** are outside the saved source/audit scope.

The source/audit checkpoint covers 1,351/1,355 sites (99.7%), including unresolved consumers. The 1,196 reviewed sites plus 26 existing-body audits give 1,222/1,355 (90.2%) with source/body evidence, not a completed-control count. Neither 10% nor 90% is a defensible actual implementation percentage; the actual count remains unknown. See the [source coverage checkpoint](source_coverage_checkpoint_20261021.json) for the count definitions and evidence limits.

## Continuing source work

**Private GUI/action/movie and online recovery:** The private B5 checkpoint is **f38246844c7723db3f53cb29875621ff083328e3**, based on the normal installed source **b823505348af025a784fc3ac171cfd0e7f0c1f99**. Selected GUI components have source-review passes, and the combined online round/results/return source review passes for 15 paths (sealed review SHA-256 `9454453018a001ceb40e899138aa07aef1dd926090fad4663116d0376847c32d`). Hosted compile/link and native multiplayer behavior remain pending. The private source is not installed in the normal package and adds no final debug-site dispositions. The licence extractor, keyboard contract and fourteen missing private GUI owner mounts have their own source-review evidence; hosted execution remains pending. [Source, policy and current checks](gui_dev_language_checkpoint_20261021.json).

**Route snap capacity checkpoint:** The 289-bound one-file source commit **6b66e5984f6f21ea47d1fa62a2ec61c9511640c9** passed hosted build run [39654339193](https://github.com/BurnoutDecomp/BP-Decomp_Workflow/actions/runs/39654339193). Native placement/movement and Back passed; the matching normal package is installed and merged to dev. Done/save persistence and a complete multiplayer race remain unverified. This supporting-flow repair adds no verified debug-site dispositions.

**Traffic follow-up:** Source commit **898e3d1be433571993e2e6f9d1be86d27d2d9585** restores the original fifteen-hull `Running Worst Case` branch. Hosted build/link and payload checks pass. The grouped native case retained fifteen phase frames and had zero game asserts/exceptions, but failed on script defects and still needs manual consumer review; no new debug entries are counted as verified. [Earlier source receipts](traffic_keyboard_followup_20261021.json).

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
