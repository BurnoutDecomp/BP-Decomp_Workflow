# Selected GameState consumers and World status

Work resumed on 19 October. The ten-file selected-consumer and World-status
checkpoint `ca5a6592f` passes combined source review. It is pushed separately
from dev; the F98 normal executable is unchanged. The one-file PC movie allocation
boundary also passes source review in the combined eleven-file `2aadf4362` tree.
Current-tree linking and native behavior remain unverified.

A five-file constructor/type follow-on is pushed separately at `5e9928a06`.
Its [receipt](gamestate_lifecycle_20261019.json) pins the original manager calls,
X360 achievement initialization and scorer alias; its source review is pending.
The combined candidate changes fourteen production paths over `7107bbb8c`.
It is not yet merged to dev, linked or tested in-game.

## What changed

The original World post-physics bridge now copies all five producer status
values into the public output. Its destination write lock, source read lock,
const accessor and value lifetime are preserved. The separate boot-video path
uses write accessors under its existing write lock. These repairs are originally
pushed as `12ca37be7` and `4d202a016`.

The eight earlier selected input, Step/Play, streaming and landmark changes are
staged on the current dev base in these separate branches.
The original full Construct/Prepare/PreWorldUpdate lifecycle is still inactive.
The retained PC GUI-65 unpause stand-in is not evidence of all four streaming
replies. Stepped GUI delivery/action retirement also remains a material boundary.

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

Current-tree linking and native behavior checks are deferred while the PC is in
use. The World transfer fixture previously passed 47 source-boundary checks;
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
