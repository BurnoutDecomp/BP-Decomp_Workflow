# Reviewed runtime-owner integration

Primary source is clean and pushed at **`f98a8cb5b`**. The final 41-path source
delta combines GameState caller/Prepare/Flyby recovery, Pool create/layout/assert
repairs, ImmediateMode member ownership/Vector3 API and Traffic's original
Anarchy-distance initializer. The normal executable is delivered from this
source, SHA256 `df3677771ddf7bdb15c5bd76b640595ffe3877fcfa6da0ddb480c3b17621332c`.

The private build mounts all 2,975 shipping TUs and links successfully. Its
follow-on rebuild reports no warnings. Fresh source review and 41 Pool protocol,
layout and concurrency checks pass. The original first link failure is retained:
one online Flyby owner was unmounted, and a VehicleList class/struct declaration
mismatch emitted a different symbol. Both repairs pass independent review.

The normal shipping build compiles 2,308 affected TUs, reuses 667 and links all
2,975. It retains 74 existing warnings, including three Sound queue instantiation
warnings; the eight ImmediateMode warnings are gone. The exact normal executable
passes 23 Start/GPU checks with zero assertions/exceptions. Its inspected frames
show the world and car without magenta corruption. User profile/config/log hashes
and modification times remain unchanged.

Private Start/GPU/Traffic/login/cold-restart integration passes 60 bounded checks,
with zero assertions/exceptions and inspected GPU/Traffic frames without magenta
corruption. Both actual saved Road Rules score types, the nonzero reset epoch and
prior progression survive completed saves and cold restart.

Traffic's first evaluator result failed on two interleaved particle diagnostics.
The exact producer-format parser repair passes independent review. Re-evaluation
of the same retained run passes 11/11; all 1,428 Traffic and 509 Physical/Route
probe objects remain unchanged, including raw line positions. Unknown and malformed
diagnostics still fail. The original failed result/log remain unchanged; no new
game execution is inferred from re-evaluation.

The canonical source list now mounts the real online Flyby TU. NativePC Pool/GDM
adapters and budgets are preserved. Full original GameState Prepare/PreWorld,
MemoryModule startup and original pool lifecycle remain unactivated. The bounded
tests do not certify an online event intro, all Traffic controls, allocator GPU/DMA
behavior or individual entries in this source cohort.

No new final entry verdict follows from this integration. Totals remain
**35 verified, 7 original no-ops and 1,313 pending / 1,355 static sites**.
Selected GameState debug consumers and graphics query callers continue in
separate source branches. See [the integration receipt](runtime_owners_20261015.json).
