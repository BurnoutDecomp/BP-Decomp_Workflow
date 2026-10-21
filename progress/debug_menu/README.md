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

The broad GUI/action/movie recovery is pushed privately at **a10961ed5** and
now includes the tested playable dev work. Source review passes for the composed
code, real Start selection/binding, keyboard lifecycle/request seats and explicit
PC language adapter. The adapter keeps ARTIST's original supported-language filter.
Fresh hosted compile/link and native behavior are still separate gates.

The regression follow-up stopped in an outdated licence-test extractor before
production compilation. It is being adapted without dropping its assertions;
a build-only hosted check runs in parallel. This private source is not installed
in the playable package. [Source, policy and current checks](gui_dev_language_checkpoint_20261021.json).

Traffic's original fifteen-hull `Running Worst Case` branch at **898e3d1be**
passes hosted compile/link and payload verification. Its grouped 74-site native
follow-up is privately staged. Review found cleanup and false-pass risks in the
test harness; a combined repair must pass before execution.
[Earlier source receipts](traffic_keyboard_followup_20261021.json).

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
