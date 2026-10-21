# Debug-menu behavior campaign

Match every entry to ARTIST, including authentic no-ops and broken leftovers.
Recovery, integration, review and behavior checks remain active.

## Playable build

Launch `build/game/Burnout_PC.exe`. The tested **b82350534** package is installed
there and merged/pushed to dev. All twelve matching executable/DLL/symbol files
are present; config, saves and their modification times are unchanged. The
previous package is backed up. [Delivery and evidence](playable_delivery_20261021.json).

Native checks now pass:

- Returning-save junkyard, default car/livery acceptance and exit to the world.
- Measured throttle response: 5.4 metres and 19.8 mph in the final confirmation.
- Owned one-player online Freeburn; visible Create Event options and HelpBar.
- Rounds change/restore, original preset route map, Summary and Done.
- Actual GUI257 submission, successful server update, and matching scalar/route
  readback. The returned lobby visibly shows Next Up Race and one round.
- Zero asserts/exceptions, clean native exit. Both native attempts and their
  attributable frames are retained. Hosted build: 2,980 TUs, 519 focused checks
  and 11 intentional failure controls.

Peer joining, a complete race, custom route editing and further mode/preset
variants remain to test. This delivery does not certify every debug control.
[Earlier crash and recovery evidence](playable_candidate_progress_20261021.json).

## Campaign counts

There are **1,355 static registration sites: 35 verified, seven original no-ops,
and 1,313 pending**. Sites are not individual visible rows or individual tests.
The number fully implemented but awaiting verification is still unknown.
This online repair does not change those final debug-site dispositions.

## Continuing source work

The separate broad GUI/action/movie recovery is committed on a private branch.
The native Unicode keyboard provider and original selected-user producer are
pushed at **cbf85fc1e**: all 2,991 TUs compile, with 591 selected checks and four
omission controls. Linking now lacks only two SKU/language methods. Eight
reviewed keyboard request/conversion call sites are pushed at **9816012fd**;
their compilation and native behavior are pending. Normal PC boot selection
also needs integration. These private checkpoints are not in the playable package.

Traffic's original fifteen-hull `Running Worst Case` branch is recovered at
**898e3d1be** and passes its hosted compile/link. A grouped follow-up targets
74 body-backed sites, with per-entry effect and restoration witnesses; it has
not run yet. [Current source and check receipts](traffic_keyboard_followup_20261021.json).
[Earlier GUI checkpoint](gui_keyboard_lifecycle_source_20261021.json).
[Held source details](gui_runtime_core_20261019.json).

The action translator covers 188 unique IDs across 189 labels. That is source
coverage, not 188 verified debug controls. Coherent checkpoints are committed
and pushed frequently; reviewed work merges in batches.

## Other reported issues

[Road Rules persistence](../road_rules_persistence_20261014.md) was repaired and
checked through saving, login and cold restart. The earlier magenta-rendering
and Start/vehicle-INI regressions have separate evidence in
[the runtime receipt](runtime_owners_20261015.json) and
[startup report](START_CRASH_20261013.md).

The harness's global END fallback was removed. Compilation/fixtures use hosted
CI. Native windows use isolated profiles, mute, low priority and scoped inputs.

[Earlier checkpoint history](HISTORY_BEFORE_INTRO_REPAIR_20261020.md)
