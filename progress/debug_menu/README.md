# Debug-menu behavior campaign

Match every entry to ARTIST, including authentic no-ops and broken leftovers.
Recovery, integration, review and behavior checks are still active.

## Counts

There are **1,355 static registration sites: 35 verified, seven original no-ops,
and 1,313 pending**. Sites are not individual visible rows or individual tests.
The number fully implemented but awaiting verification is still unknown.
Source coverage and fixture checks are not final debug-entry dispositions.

## Playable package and current crash

The previous playable **9c15dfff8** package is restored in `build/game`, with
matching DLLs/symbols and unchanged config/saves. The newer201 package was
withdrawn: its existing-save junkyard stayed black. A fresh-profile state-chain
check had passed, but that was insufficient for a playable delivery.
[Black-screen and rollback evidence](black_junkyard_rollback_20261020.json).

The immediate priority is one build that passes visible junkyard, car selection,
measured driving, owned online Freeburn and Create Match. The old package still
has the reported Create Match issue. The traffic completion bridge is now
recovered in private candidate28734. Its returning-profile native test renders
the junkyard, selects the car/livery, drives and hosts visible Freeburn. The next
run reproduced a null-cache crash on entering Create Match options. Event-order
repair is active; no fixed online build is claimed yet.
[Native progress and exact failure](playable_candidate_progress_20261021.json).

The separate [animation initialization repair](freeburn_animation_init_20261020.json)
is committed on dev and passes its focused positive/omission checks. A successful
native Create Match run is still required before calling that issue fixed.

## Source and validation lanes

- Shared dev and the source checkout include **70511989c**; its two new commits add CMake files. The normal folder remains9c.
- Private checkpoint **6ca3a63af** adds twenty reviewed SelectRoutes methods.
  The full route screen has a corrected source proposal under combined review;
  compilation and native Create Match submission remain pending.
- The merged startup/compile-check source is 7d66267f5. Its shipping build
  passes all 2,979 selected TUs, including both newly repaired embed checks,
  plus 519 focused checks and 11 intentional failure controls. This does not
  establish all gameplay. Both repaired probes are now mounted on main/dev.
  [Compile-check repair](embed_compile_checks_20261020.json).
- The broader debug source is pushed at **c511b3466**. Its newest 11-path batch
  restores WorstCase HUD events, typed movie preparation and resource handshakes.
  Combined source review passes after one vector correction. All 2,991 selected
  TUs compile; linking still lacks the three platform providers below. Native
  GUI phases/registration remain held. The next two-path movie queue/PC idle
  repair is reviewed and compiled with the same link gaps.
  [Movie followup](movie_queue_source_20261020.json). [Batch receipt](gui_worstcase_movie_source_20261020.json).
- The preceding a2 tree compiled all 2,991 selected TUs and passed 916 focused
  checks/13 controls, but linking still lacks the real SKU/language and keyboard
  providers. [Runtime/source details](gui_runtime_core_20261019.json).
- [HUD/profile owners](gui_render_profile_source_20261020.json) and
  [activation/keyboard source](gui_activation_keyboard_source_20261020.json)
  now have passing scoped source reviews.

The isolated candidate28734 passes its hosted 2,979-TU build and 519 focused
checks/11 omission controls. Those checks do not cover the reproduced options
cache-order crash. The normal package remains protected until complete native
delivery. The older setup-only attempts are retained as diagnostic history.

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
