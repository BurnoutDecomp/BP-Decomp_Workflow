# Selected GameState and graphics consumers — paused

Work stopped at the user's request. All agents and owned build/test processes
are stopped. The normal executable remains the visually checked F98 build
(`df3677771ddf`); the failed candidate was never delivered. Final totals remain
35 verified, seven original no-ops and 1,313 pending sites.

## Saved checkpoint

The pushed isolated branch `codex/debug-menu-selected-consumer-integration` is
clean at `66613d8d31cee93059221e7ba68246f0566040f4`: eight GameState consumer
files, three reviewed graphics caller files and three dispatcher declaration
repairs. All 2,975 shipping TUs compile and link. The final incremental attempt
rebuilt 39 files and recorded no warnings or failures; earlier link failures and
objects remain retained.

Native Start and GPU tests both FAIL: the game freezes in the junkyard after a
streaming pause, never reaching driving. They record zero assertions/exceptions.
The prepared landmark/Step/Play case was not launched after that failure.

An independent reviewer traced the missing dependency: the real WorldEntity
PostPhysics update writes residency, but `BridgeEntityModulesToOutput_PostPhysics`
does not copy that status into the public World UpdateOutputBuffer. The public
member starts zero; the newly connected consumer reads it and requests a
permanent stall. ARTIST `0x827AEEB0` has the missing transfer at `0x827AF174`.
No repair or bypass was applied before stopping. The combined review was
interrupted; its full final report must not be assumed complete.

## Resume here

Recover the attested status transfer, review its full bridge/locking/lifetime
contract, then rerun the failed native gates before any normal delivery.
The original full GameState lifecycle and native occlusion remain inactive.

The 25-entry Game State page worker was interrupted with no tracked source edits.
The allocator worker completed its frozen prerequisite packet: the original
GlobalGraphics provider already exists in the isolated `55790e71` recovery lane,
and still needs reviewed startup integration. No duplicate provider or capacity
increase was added. Its packet is
`scratch/DEBUG_MENU_1011/graphics_allocator_provider_20261015/REPORT.md`.

The [machine-readable checkpoint](selected_consumers_20261015.json) records exact
source, build and failed-run identities. Raw evidence remains in
`scratch/DEBUG_MENU_1011/selected_consumers_integration_20261015/`.
