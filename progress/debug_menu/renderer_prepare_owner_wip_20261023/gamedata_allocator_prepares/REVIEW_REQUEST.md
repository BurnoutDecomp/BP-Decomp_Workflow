# Fresh source-only review request

Review the complete four-path proposal in `SOURCE_MANIFEST.json`, `source/gamedata_allocator_prepares.patch`, `source/pre/` and `source/post/` against the frozen primary/DecFIGS evidence. Exact base is source57bbdefbbac12c0595d7eeed03de40729d2a14af. Do not use the active consumer source as an implicit preimage.

Scope is original stack-backed CreateBanks/CreatePools/CreateAllocators, canonical response accessor/shape correction and the ARTIST8/9 storage capacities. Existing two-argument Prepare, all three native helpers and Construct must remain identical under `NATIVE_BODY_BINDINGS.json`. Source API/ABI changes to response sizes and embedded arrays require explicit inspection; there is no mounting/activation in this packet.

Please inspect exact request counts/indexing, especially the already root-excluding GetNumBanks getter; parameter ownership/order, native request sizeof, all registry writes and reply drain cases, no result-code policy, successful input-carve retention, raw response76/Linear20 console payloads and native widened members, and the spare8/9 storage evidence. Do not infer readiness from recovered caller bodies or direct-call search coverage.

The original Resource Update and seven schema/list helpers remain absent. Current RW memory handlers are present empty bodies, a distinct no-op availability gap. Initialization/factory/capacity reconciliation is recorded in `READINESS_AND_OWNERSHIP.md`. No compiler, build, test, native launch, ledger update or review verdict was run by this lane. Root owns all such actions and source composition.

Return `VERDICT: pass` or `VERDICT: fail` for this source-only checkpoint, with any findings tied to source lines and primary evidence. A pass does not mean the original preparation chain is link-ready or playable.
