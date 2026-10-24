# Survey output semantics — exact95 correction proposal

The rejected native capture has a concrete missing platform effect: exact95 discards the original `BeginConditionalSurvey` flag1. ARTIST encodes that flag as a hardware instruction to discard query-box pixels after visibility testing. The native draw instead reaches the ordinary color/depth/stencil outputs. Its selected position-only pixel shader emits opaque black, matching the visible polygon contamination. This is a source-backed cause candidate; the proposed correction has not been compiled, reviewed or run.

Source base: **95e513ae15ebfd322fd639664f835b171718e736**. Workflow: **992e2896286ed83aa0098729e1b00497476b4c41**. Three source paths, two already-mounted TUs; no mount change. Exact pre/post hashes and Git blobs are in `SOURCE_MANIFEST.json`. The earlier resource packet and FileSystem packet remain frozen and separate.

## Original contract

`OcclusionCullManager::RenderOccludeeBoundingBox` at827EE010 calls BeginConditionalSurvey with the actual query ID and Flags=1, draws the box, then EndConditionalSurvey with Flags=0. It does not select a special query-only color/depth state object.

ARTIST82949EAC–82949F14 computes the register value:

```
((Identifier & 63) << 1) | 1 | ((Flags & 1) << 7)
```

It writes that value to GPU register0x2293 and starts the corresponding visibility query. The official Xenia [register table](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/gpu/register_table.inc) names0x2293 `PA_SC_VIZ_QUERY`; its [register declaration](https://github.com/xenia-project/xenia/blob/95a5c3ee250f80c3b9d139658649d9ffb6db3eec/src/xenia/gpu/registers.h) names bit0 query-enable, bits1–6 query ID, and bit7 `kill_pix_post_hi_z`. This external source identifies the register bits; ARTIST proves that this game actually sets them. The original82949F68 End function closes the query and returns to the outer survey's control value, or disables the mode when the survey stack empties.

The PC shim at exact95 XenonD3D9Shims.cpp11275 ignores `luFlags`. Its provider issues real D3D9 query Begin/End but has no equivalent write suppression. The position-only BeginRendering binds programs/descriptor and resets shadow caches; it does not suppress framebuffer writes. `25.fx` and the selected native program image implement opaque black output. Thus “ZOnly” in the class name does not establish a no-color-write contract by itself.

## The actual execution chain

| Step | Exact95 owner | Timing |
|---|---|---|
| Batch | BrnRendererModule.cpp4976–4984 | BeginQueries → query walk → EndQueries → conditional mesh walk → EndConditionalRender. |
| Query walk | CgsDispatcherCommands.cpp1427–1457 | Directly calls InterpretOcclusionQuery for each sorted mesh packet. No new command is queued for later execution. |
| Bounds/transform | InterpretOcclusionQuery597–654 and manager RenderOccludeeBoundingBox | Actual world scratch matrix and packed box become box-to-clip. Small/instanced/near-plane cases retain their original trivial-accept behavior. |
| Query Begin | XenonD3D9Shims.cpp11275 → provider175–218 | `Issue(D3DISSUE_BEGIN)` executes immediately on the same native device. |
| Shader constants | D3DDevice_DrawIndexedVertices6842–6856 | Flushes the staged actual transform rows before entering WorldDraw_IndexedUP. |
| GPU draw | WorldDraw_IndexedUP4491,5062–5067 | Real retained WorldGeometry_Submit or real GeometryBindingsPC::DrawIndexedPrimitiveUP executes synchronously. WorldGeometry_Submit calls IDirect3DDevice9::DrawIndexedPrimitive directly after binding buffers. |
| Query End | provider221–243 | `Issue(D3DISSUE_END)` follows that completed submission attempt. The token/serial requires exactly one successful, nonempty draw. |
| Decision | provider GetData/ShouldDraw | Reads the matching ended survey and preserves the existing native nonzero-samples policy. It does not reinterpret the result because the picture failed. |

The “deferred interpreter” concerns CPU-produced dispatch packets and staged shader rows. The actual95 query Issue and native GPU draw calls are ordered inside one synchronous interpretation. Source evidence does not support moving Begin/End to compensate for a deferred draw. `SOURCE_CONTINUITY.json` proves the proposal preserves Issue/GetData, submission-token/generation/serial lifecycle, conditional decisions and original draw expression.

The existing62065 capture is bound in `NATIVE_FAILURE_BINDING.json`: false→true→false controls, real resources and ready1, complete list11 batches, query ID/serial/result correspondence, zero asserts/exceptions, but black polygon regions while enabled. Initial captured sample counts are zero. Those results are not changed or explained away. State contamination can affect later depth tests; any remaining zero results after restoring the original write contract still require evidence.

## Proposed native mapping

The actual survey flags are carried into the existing survey-stack frame, including unavailable-query frames, and exposed by a read-only flags accessor. The live game caller passes its real Flags=1. The existing two-input native provider API use remains source-compatible through default Flags=0. End flags are still0 at the only game call site; broader XDK survey modes are not claimed recovered.

A bounded PC scope wraps the **actual GPU submission** in WorldDraw_IndexedUP. With active flag bit0, it saves actual device state, zeroes all four color write masks, disables depth writes, zeros the stencil write mask, and disables post-shader alpha rejection/coverage. It retains depth/stencil tests, depth comparison, culling, shaders, transformed geometry, query Issue/GetData and the actual GPU draw. Microsoft documents that [ZWRITEENABLE=false preserves depth comparisons](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3drenderstatetype); its state definitions also identify the independent color masks and stencil write mask. Mapping the Xenos post-test discard to these native controls is a PC platform implementation, gated by review.

Alpha coverage goes through its existing real owner: the scope saves `sbA2cRequested`, clears the request and calls `AlphaCoverage_Reconcile`, then restores the saved request and reconciles after restoring alpha-test state. It does not introduce an independent vendor-hook state or force a query result. The selected pixel program remains unchanged.

The scope restores every modified state before returning from the native submission, so the existing shadow caches again describe the device they described before the box. This is essential for the next mesh draw and the sky. No suppression state is held across an ordinary scene draw. Flag0/no-survey draws take an immediate no-op branch. There is no new renderer readiness, fail-open, result override, geometry-skip or draw-skipping policy.

With `BRN_OCCLUSION_DIAG=1`, at most96 new lines read actual state at `before`, `draw` and `restored`, keyed to the existing submission serial. Draw must show cw=0,0,0,0 / zw=0 / sw=0 / at=0 / coverage request/applied0, while ze/zf/cull retain their saved values. Restored must show the saved ten-state tuple plus coverage request/applied and `restored=1`. Additional readbacks stop with the diagnostic budget; release behavior keeps only the seven required save/restore states. Failed state API calls assert; they are not silently reported as successful suppression.

## Review and delivery limits

- This is a three-path source proposal, unreviewed/uncompiled/unactivated. It does not establish visual or occlusion acceptance. Root owns all gates and any bounded native follow-up.
- The state capture/restoration adds CPU render-state calls per queried box. Performance is unmeasured. No batching or timing rewrite is included.
- Native D3D9 per-sample counting is the existing PC policy; Xenos predicate polarity is not newly asserted. Visible/hidden object behavior still needs genuine runtime witnesses after the image is correct.
- Native output suppression must hold even when a host query is unavailable; original proxy pixels still must not alter the scene. This is why flags live in the survey frame independently of a successful query token.
- The existing resource payload conversion, budgets, sky initialization, startup ownership, registered objects, threads, original console code, and all1355-registration counts are unchanged by this packet.
- The old mechanical fixture's expected indexStride2 is a separate expectation error: the selected index lock's16-bit format code is1. It is not the black-polygon cause and this packet does not change the lock or checker.

`POSTMORTEM.md` and `REVIEW_REQUEST.md` define the static review boundary. Original ARTIST exports, exact95 consumers, existing rejected evidence receipts and pinned external register declarations are frozen alongside the proposal.
