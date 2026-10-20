# Debug-menu behavior campaign

Match every entry to ARTIST, including authentic no-ops and broken leftovers.
Recovery, integration, review and behavior checks are still active.

## Counts

There are **1,355 static registration sites: 35 verified, seven original no-ops,
and 1,313 pending**. Sites are not individual visible rows or individual tests.
The number fully implemented but awaiting verification is still unknown.
Source coverage and fixture checks are not final debug-entry dispositions.

## Playable package and current crash

The normal build/game folder contains the restored playable **9c15dfff8**
package, with matching DLLs/symbols and preserved config/saves.
It still has the reported online Create Match crash.

The newer db73 candidate failed in marketing-screen input dispatch.
The input-buffer lifecycle and GUI lock repair now passes hosted checks.
The user's exact 740 test reaches title readiness and InGame stage 5 with zero
asserts, then crashes in the fresh-profile licence introduction.
The cause is the PC event handoff: stale cache 64 precedes the current profile 350.
A focused event-order repair is under review; startup/intro and Create Match
are **not verified**. See [the crash, repair and rollback evidence](startup_regression_20261020.json).

The separate [animation initialization repair](freeburn_animation_init_20261020.json)
is committed on dev and passes its focused positive/omission checks. A successful
native Create Match run is still required before calling that issue fixed.

## Source and validation lanes

- Gameplay dev is db73ba838; its latest normal-folder candidate was rolled back.
- The private startup/compile-check candidate is c68fc7279. Its shipping build
  passes all 2,979 selected TUs, including both newly repaired embed checks,
  plus 447 focused checks and 10 intentional failure controls. This does not
  establish gameplay. [Compile-check repair](embed_compile_checks_20261020.json).
- The broader debug source is pushed at **90211a8f2**. Its newest 11-path batch
  restores WorstCase HUD events, typed movie preparation and resource handshakes.
  Combined source review passes after one vector correction; this newest tree
  has not compiled. Native GUI phases/registration remain held.
- The preceding a2 tree compiled all 2,991 selected TUs and passed 916 focused
  checks/13 controls, but linking still lacks the real SKU/language and keyboard
  providers. [Runtime/source details](gui_runtime_core_20261019.json).
- [HUD/profile owners](gui_render_profile_source_20261020.json) and
  [activation/keyboard source](gui_activation_keyboard_source_20261020.json)
  now have passing scoped source reviews.

The action translator covers 188 unique IDs across 189 labels. That is source
coverage, not 188 verified debug controls or a complete native GUI pipeline.

## Other reported issues

[Road Rules persistence](../road_rules_persistence_20261014.md) was repaired and
checked across saving, login and cold restart. The earlier magenta-rendering
regression and Start/vehicle-INI crash have separate native delivery evidence in
[the prior runtime receipt](runtime_owners_20261015.json) and
[startup report](START_CRASH_20261013.md).
The harness's global END fallback was removed. Builds and fixture execution use
hosted CI; local game windows are now authorized again and remain isolated.

Coherent checkpoints are committed/pushed frequently. Reviewed work merges in
batches, without waiting for all 1,355 final dispositions; a hosted build alone
does not justify replacing the user's playable package.

[Earlier checkpoint history](HISTORY_BEFORE_INTRO_REPAIR_20261020.md)
retains the previous detailed reports and links.
