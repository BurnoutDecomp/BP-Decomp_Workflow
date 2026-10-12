# Resource debug windows

Root source branch `codex/debug-menu-resource-windows` is pushed at `72497ef14`,
based on the separate GUI/Replay candidate `ab80240c`. The owned Resource paths
are now integrated in primary `2d16df915`; the unrelated GUI/Replay branch was
not merged. Resource20 joins the 1,092-site primary source/audit packet union.
It has no native or final-entry verdict.

Current production repairs are frozen at `964e30c7`: all six findings have source
candidates, seven affected production TUs compile, and no new faithfulness
findings are reported. Test-only `72497ef14` adds 35 whole-method draw/math
witnesses for Window chrome/alpha and Texture thumbnails. The same checks run
against the previous `2c65134ab` source and fail 14. They do not cover serialized
texture pointers, full Resource lifecycle or native UI behavior. The same fresh
reviewer passes all six repairs; report SHA256 is
1119913f9cb8c43d26476b02e219a34b14db8e95a4cee04ddb1d3973d9a473da.
The exposed Model/Renderable/Material texture-usage chain is now recovered at
`2f15d6683`; four affected TUs compile with zero new faithfulness. The normal
2,967-TU build links through `41afefeab`, including the existing Renderable TU.
The original empty Material state operation and its null-query quirk are
preserved. This closes the named link dependency, not native Texture Window
behavior or the remaining lifecycle/backend/consumer gaps. The supporting
source chain passes the separate startup-fix combined source review at
`41afefeab` (SHA256
`762699a24d06de6a0b52bad9fc74e32c22272b60a8353289ef1d884541f168c9`).
That source verdict adds no native Texture Window approval.

## Earlier implementation checkpoints

The first checkpoint restores all five original embedded window types, the
four-window pointer table, texture-entry allocation, and Histogram/TypeList
reset bodies. It replaces the incorrect standalone TypeList accounting shape
with its original Window base and named type/category records. Real descriptor
constructors initialize size/alignment to `{0,1}`; the previous explicit zero
alignment and invented scratch fields were incorrect. The original seventh
category slot is retained. Window construction leaves its data untouched until
the original Prepare path sets it.

Six affected production TUs compile with zero new faithfulness findings.
The8799da15 increment restores all20 registrations, pool-option generation,
texture/page and bundle callbacks, and the original texture reset. Its four
production TUs also compile with zero new faithfulness. The original reset
leaves texture byte sizes and the total-texture field untouched; it initializes
the attested pointers, indices, model/instance sentinels and selection state.
The1237d59d increment restores option-table refresh, invalid-pool removal,
all four typed window reset dispatches, window add/remove order, mode updates,
and the stats/share-test update dispatch. Three affected production TUs compile
with zero new faithfulness.

The0e6dcdc1 checkpoint restores the stats dump and its real buffered logger.
Original Open truncates and closes the file; Flush reopens it with OPEN_EXISTING,
seeks to the end and writes the pending buffer. Append preserves an exactly full
buffer until overflow or an explicit flush; the old source dropped excess text.
Three production TUs compile. The complete production logger and StrStream pass
36 checks using real temporary Win32 files. A focused negative control retains
the recovered lifecycle but substitutes only the old char sink;7 checks fail.
This proves that backend regression, not the original in-game action.

The0fafee10 increment adds Heap window Reset/AddHeap/Update/CalculateColour.
It preserves both original heap records, segment-size thresholds, input clamps,
scroll wrapping, scalar trig/rounding and packed colours. Three affected TUs
compile with zero new faithfulness;24 whole-body state/math checks pass, including
the64-bit-to-low-word scrolling counterexample. Render and RenderHeap are still
absent. The postmortem records remaining hardware-model boundaries; these checks
do not certify window rendering or gameplay.

Sol's394a15fb/4083e12b increments recover TypeList Update/RenderRaw/RenderByType/
RenderByCategory/DrawType, Histogram Update/Render/DrawBar and Heap Render/
RenderHeap/AddTextLine, plus the two declared Heap statistics bodies. Root
verified the10 raw Git source pins and frozen archive, then fast-forwarded the
isolated integration branch. All5 affected production TUs compile with zero new
faithfulness findings. The existing36+24 checks preceded these new render bodies;
they do not cover the newly recovered rendering. A fresh independent Resource
source review is still required because its author cannot review its own work.

Resource DebugComponent HUD/destruction, the Texture window audit,
shared-window source review, linking and native checks remain pending. The
planned scope is 20 static registration sites; none is promoted by this partial
construction checkpoint.

The manifest contains29 paths. The frozen Sol lane used10 explicitly leased
paths, including narrow Pool/PoolModule/Heap friendship and the two named Heap
statistics methods. Root kept the other19 paths. The original function/address map, compile records
and constructor postmortem are under
`scratch/DEBUG_MENU_1011/recovery_lanes/resource_windows_packet`.
ARTIST constructors `827E08D0`, `827DF8E8` and `821F05C8` arbitrate initialization;
DecFIGS supplies the declaration shapes. No raw-offset/vtable workaround or
duplicate window family is introduced.

## Fresh review and repair lane

Root2c65134ab adds the original share-test/loader-queue HUD and named GetEntry
helper;4 affected production TUs compile. A separate fresh20-site reviewer
failed the complete Resource candidate with6 findings: serialized InstanceList
reads, shared Window colour/position/scaling, thumbnail gap/inset, stat text size,
legal native type-mode termination, and Resource base-constructor stores.
Report SHA256:81143496d0a7bd2f0aab502d8df7bb618533af4501d914261ef783652e5bc0de.
Sol has frozen the repair handoff at964e30c7. Root verified its31 raw Git pins,
archive and six-path diff, fast-forwarded the private integration branch, and
compiled seven affected TUs with zero new faithfulness. The same fresh repair
reviewer passes all six source findings. The
31-path campaign now includes a narrowly allocated private Resource-only base
constructor selector; existing default lifecycle and other components stay unchanged.
These are code repairs, not merely unverified controls.
