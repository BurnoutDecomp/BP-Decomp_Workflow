# Selected GameState consumers and World status

The [current integration](gui_queue_source_20261019.json) at `3e0cbea66`
passes source review and hosted compile/link across the 2,976-TU shipping list.
It changes 28 source paths over dev `37735c71d` and remains separately pushed
while native startup/streaming checks are open. These are source paths, not a
count of verified debug entries. GUI output is retired after its retained
sound/network snapshot, and the GUI65 fake unpause is removed. The monitor body
and X360 thread implementation remain unmounted; their missing backend does not
become an empty successful provider. Current native behavior remains unverified.

The normal folder separately has the October 19 [current-dev refresh](playable_dev_20261019.json).
Earlier evidence is preserved in the [selected/movie](selected_status_20261019.json),
[constructor](gamestate_lifecycle_20261019.json), [ModeManager/DLC](mode_dlc_source_20261019.json)
and [Prepare](gamestate_prepare_source_20261019.json) receipts, including the failed
provenance review and its correction.

## What changed

The original World post-physics bridge now copies all five producer status
values into the public output. Its destination write lock, source read lock,
const accessor and value lifetime are preserved. The separate boot-video path
uses write accessors under its existing write lock. These repairs are originally
pushed as `12ca37be7` and `4d202a016`.

The eight earlier selected input, Step/Play, streaming and landmark changes are
staged on the current dev base in these separate branches.
The full ModeManager constructor and first-pass GameState Prepare are now selected
in the current source candidate. Full GameState PreWorldUpdate remains separate.
Prepare retains the earlier host-only base-module flag and stable output-buffer
allocation; the ARTIST allocation/flag path is still under audit.
The GUI65 unpause stand-in is removed in the later follow-on; its loading-screen
presentation stand-in remains. Genuine four-reply completion and the corrected
GUI output lifetime still need native witnesses. The original one-shot192 request
can be lost when stepping skips GUI; that source-supported edge is preserved.

The [25-row source matrix](gamestate_source_matrix_20261019.json) records nine
existing typed paths, five recovered renderer paths and eleven unresolved rows.
All 25 are native-unverified. These source classes are not implementation-complete
or final gameplay verdicts. The original road-name matcher deliberately compares
66 IDs and uses the 67th name as fallback; its unused last ID is not a missing
source-recovery item.

## Preserved failed candidate

The October 15 branch `codex/debug-menu-selected-consumer-integration` remains at
`66613d8d3`: eight GameState files plus six graphics/dispatcher paths. Its 2,975-TU
build links, but both native Start and GPU cases freeze after a streaming pause.
No landmark/Step/Play case ran after that failure. It was never delivered.
The missing public World-status transfer was identified from that investigation;
the original failed logs and verdicts remain intact.

## Next gates

Current-tree linking passes after the thread include, owner-tag and inactive
monitor staging repairs. Native behavior checks remain deferred while the PC
is in use. The separate
[current-dev playable refresh](playable_dev_20261019.json) passes its full hosted
build and is installed for user playtesting; it does not include this recovery candidate.
The World transfer fixture previously passed 47 source-boundary checks;
the page fixture passed 13 checks. Neither establishes a current integrated run.
Validate residency-to-stall/unpause, real input edges, all four module replies,
GUI loading events, step/action lifetime and landmark pixels before delivery.

The original lifecycle and native occlusion still need their complete providers.
The existing GlobalGraphics allocator recovery at `55790e71` must be reused;
its ownership/capacity/startup work is not solved by this checkpoint.

See the [current source receipt](selected_status_20261019.json) and
[historical failed-run receipt](selected_consumers_20261015.json). Raw evidence
is retained under `scratch/DEBUG_MENU_1011/selected_status_integration_20261019/`
and `scratch/DEBUG_MENU_1011/selected_consumers_integration_20261015/`.
