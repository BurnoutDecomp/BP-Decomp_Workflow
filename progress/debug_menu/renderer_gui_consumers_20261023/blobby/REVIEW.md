# Fresh-eyes review: blobby-shadow renderer recovery

Review basis: proposal `scratch/DEBUG_MENU_1011/brn_blobby_shadow_renderer_recovery_20261023/`; source commit `aa6b7ec4f9af54230bc2e04622b1d9c75c26700b` (`Restore the original overlay showing notification wire`). This review is source-only. No build, compile, game, native, fixture, CI, or runtime validation was performed.

## Verdict

**VERDICT: pass** for the bounded source recovery of `BrnBlobbyShadowManager::Render` and its renderer call site, subject to the review note below. This approves the submitted source delta for a bounded private recovery commit; it grants no runtime, gameplay, producer, or verified-site credit.

## Source and original-evidence checks

The proposal's four source preimages are byte-identical to the corresponding blobs at `aa6b7ec4f9af54230bc2e04622b1d9c75c26700b`:

- `BrnBlobbyShadowManager.h`: `cb7cdbdd27fa04401c0e4b8085eeaff9788f8d34`
- `BrnBlobbyShadowManager.cpp`: `d29bc7057550b0fb913a19f2734510f1d299696b`
- `BrnRendererModule.h`: `8e03b58c8f50808b5d81c9d7cdd2b59c476e6889`
- `BrnRendererModule.cpp`: `80be5d8e69b9ac750ad801b6f319ba377fa3a55f`

The cited `BrnGameModule.cpp` source input differs between proposal base c36 and aa6 only by an unrelated `GetTakedownEventOutputQueue()->Clear()` in the sub-step output cleanup; it does not change the blobby texture acquisition/`PrepareAgain` path cited by the report. The patch changes only the four files listed above.

ARTIST `0x824071B0` confirms function-local first-alpha opacity initialization before the internal-buffer count test; the empty-buffer early return; texture assertion/bind; depth/rasterizer/blend state sequence; height fade clamp; truncating alpha; `1 + 0.4*fade` spread; scaled outer extents and unscaled axle extents; spread-scaled right vector; eight strip vertices; UV rows `0`, `0.1875`, `0.8125`, `1`; and low-byte alpha/white packing. The proposal's explicit `RGBA8{r,g,b,a}` assignment agrees with the X360 big-endian stored byte order and the existing `RGBA8` declaration.

ARTIST `0x8240BFA8` confirms the call is guarded by renderer bytes `+0xC417` (`mbRenderCarsTransparent`) and `+0xC418` (`mbRenderBlobbyShadows`), receives the copied 4x4 dispatch-input matrix, Im3d at `+0x10E0`, texture at `+0x37F0`, alpha at `+0x37F4`, and frame white level in `f2`, and occurs before `BeginForceStencilWrite`. DecFIGS `0x3795C8`'s mangled name establishes the by-value `rw::math::vpu::Matrix44`, typed Im3d/Texture pointers, and two float parameters. The new declaration matches that shape.

At the exact aa6 source, the referenced PC path is implemented: textured `Im3d`/`ImRenderer<BasicColouredTexturedVertex>` submission packs the CPU vertex to the GPU stream and uses `D3DDevice_BeginVertices`/`EndVertices`; Xenos topology 6 maps to `D3DPT_TRIANGLESTRIP`; the immediate submission reaches `GeometryBindingsPC::DrawPrimitiveUP`. The proposal uses these existing APIs and factory slots, without introducing a renderer shim or guessed producer.

The new manager gate is independent of mesh-list counts, matching ARTIST. With an empty shadow buffer, the first-alpha static is initialized and the manager returns before beginning Im3d or changing renderer state; the caller's cleanup condition also remains false. With records, cleanup is scheduled after the manager draw.

## Review note and limits

The existing `lbTransparentWork` is a combined predicate for world list 15 **or** car list 20. Therefore, the comment in the proposed renderer hunk saying it “Preserve[s] the existing PC empty-list elision” overstates the existing behavior: when list 15 is nonempty, list 20 may still be dispatched under `mbRenderCarsTransparent` even if list 20 is empty. This behavior is already present in the exact preimage and the patch does not change it; it does not block the recovered manager call, which is correctly independent of list counts. The comment should be narrowed or separately corrected before treating per-list empty elision as established.

A source grep at aa6 finds `AddShadow` only at its definition, the embed-check helper, and commented traffic placeholders. The proposal recovers the consumer but not a live producer, so it cannot establish that records reach the renderer or that shadows appear. No compile or runtime claim is made.
