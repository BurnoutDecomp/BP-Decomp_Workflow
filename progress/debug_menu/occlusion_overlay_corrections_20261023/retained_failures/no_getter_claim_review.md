# Independent review: corrected graphics occlusion cursor delta

VERDICT: fail

The dispatcher continuation correction is source-consistent for both capped opaque passes, and the blobby-shadow call remains composed. The matrix-access justification is materially inaccurate: the exact bound DecFIGS file declares the getter this proposal says does not exist. This packet is not accepted; revise the access path/evidence and resubmit only the corrected delta.

## Findings

1. **Access adaptation uses a false premise.** `references/DecFIGS/dwarfdump/GameSource/Game/BrnDispatchThreadInputBuffer.h` (SHA-256 `11be9bdd1720b43f59fe355810fb6c38926a7f6c83a5b02c82bc98c039b3d999`) declares public `const rw::math::vpu::Matrix44 & GetOcclusionViewProjectionMatrix() const` at h:160, followed by `SetOcclusionViewProjectionMatrix` at h:163. The packet instead claims DecFIGS has no getter and adds global friendship so the renderer can bypass the original-declared accessor. The current PC source header lacks this accessor body/declaration, and its member is private; recover the accessor faithfully and use it for both occlusion and blobby reads, or correct the evidence-backed access decision before approval. The friend itself does not change layout, but its rationale is false.

2. **Continuation arithmetic checked and correct for the proposal’s callers.** ARTIST `DispatchAllMeshes` export `0x827F2718` (hash in bindings) computes the bounded end from `first + count`, caps at total, and returns that end unless it equals total, when it returns `-1` (`0x827F27A0–0x827F27E4`, `0x827F5AA0–0x827F5AB8`). ARTIST Render export `0x8240BFA8` uses the return as the next first for list 19 (`0x8240CF10–0x8240CF64`) and list 11 (`0x8240D068–0x8240D0C4`). The new dispatcher calculates the same end and returns it for non-final ranges. The query and draw calls receive the same `liFirst`/64 range; the next batch starts at the returned end without an extra increment. For empty lists and negative/unbounded counts it terminates with `-1`.

   One narrower API edge remains: the pre-existing `luFirst >= luEnd` early return returns `-1` for a zero-length subrange before the total, whereas ARTIST’s tail would return that capped end cursor. None of the reviewed callers supplies a zero count (they use `-1` or 64), so this does not break the new list-19/list-11 loops.

3. **Composition and read lifetime.** The postimage keeps `mBlobbyShadowManager.Render` in the car-transparent block before list 20, with the same five arguments; the new dispatch calls do not remove or reorder it. The top-level PC `Render` holds the input-buffer read lock before calling `RenderWorldPasses`, so both the new matrix copy and the existing blobby matrix read are within that lock. Friendship adds no field or layout change. This source review gives no D3D9 query-provider polarity, runtime, or site credit.

## Binding and limits

All six supplied preimage/postimage hashes and the three bound ARTIST export hashes match `bindings.json`; the DecFIGS hash matches as listed above. No build, runtime, native/game, Stage, Run, or input validation was performed. The D3D9 query and conditional-render provider remains a platform seam, and no visual/gameplay parity is claimed.
