# Allocator recovery checkpoint

Original allocator construction is recovered on the source branch through
`0bdeb3617`; it remains unactivated. The combined source review through Root's
`b4611add1` passes with explicit native limits. Native budgets
stay unchanged. This is supporting-system progress, with no entry promotion.
Root's controller repair and production fixtures are pushed at `b4611add1` on
`codex/debug-menu-allocator-startup-validation`.

The source pass explicitly qualifies ARTIST's Linear failure-tail access beyond
its established five-lane objects. Native code preserves the owned fields and
omits that surplus read/store; the PS3 six-lane shape is not imported.

The recovered code restores the original global/child setup and typed wrappers,
placement initialization with actual native object storage, five-lane heap
ownership and rollback, and transactional Linear allocation. Native existing
objects use a separate `AdoptMemory` API with no hidden header skip.

Whole production RW/EA/CoreAllocator/descriptor owners pass **14/14 checks** for
arena guards, placement extents, ownership, rollback, absolute alignment and
atomic failure. The preceding implementation fails seven of nine shared cases.
Six production TUs compile with zero new faithfulness findings after the renderer
and controller complete-type includes are repaired. Root also restores the
controller's original placement call, attested at ARTIST `0x823C6A78`.

Evidence and raw test output:
`scratch/DEBUG_MENU_1011/allocator_startup_validation_20261013/`.
Full author evidence: `recovery_lanes/vehicle-deformation-131/scratch/alloc1013/`.

Later `5dffffc9f` separately recovers queued bank creation and its canonical
counter. It is unreviewed and unactivated: the native root adapter backs lanes
0/1 while the original map requests 0/2. Completion counts error replies in the
original code, so completion alone cannot certify a working bank tree.

Evidence correction: the earlier startup diagnosis called the internal debug
pointer `0x82FFA88C`. The correct address is **`0x82FFA894`**; `0x823A7CC8` contains
`816BA894`. `0x82FFA88C` belongs to graphics. Original frozen reports are retained;
the typed public-wrapper repair and prior native results are unaffected.
