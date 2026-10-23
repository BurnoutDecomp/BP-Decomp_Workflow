# Blobby shadow manager renderer recovery proposal

## Scope and status

This packet proposes a source-only recovery for debug registrations 12 (mbRenderBlobbyShadows) and 21 (mfBlobbyShadowAlpha) from exact private base c36dd33292689bfb8b436ab73190f73a36200e98. It adds the missing manager renderer and its call from the existing PC world-pass helper. It grants no build, fixture, native, or gameplay parity credit. No production source, worktree state, index, or ref was changed; the only writes are this new scratch packet.

The proposal is bounded by ARTIST BrnBlobbyShadowManager::Render @ 0x824071B0, the BrnRendererModule::Render @ 0x8240BFA8 call at 0x8240D2F4-0x8240D334, and the existing PC CgsGraphics::Im3d / D3D9 immediate-vertex path. DecFIGS is used only for declaration shape. Exact JSON exports are copied under original/; their SHA-256s and source-input pins are in bindings.json.

## Debug ownership and original call

BrnRendererModuleDebugComponent.cpp directly registers mbRenderBlobbyShadows as a bool (Render blobby shadows, line 48) and mfBlobbyShadowAlpha as an f32 at lines 59-61 with range [0,1] and step 0.05. The registrations have no per-site callback; the generic variable manager writes through the stored pointers.

ARTIST Render @ 0x8240BFA8 gates the block on renderer byte this+0xC417 (mbRenderCarsTransparent) at 0x8240D2F4-0x8240D304; the next gate reads this+0xC418 (mbRenderBlobbyShadows) at 0x8240D308-0x8240D318. Call setup at 0x8240D31C-0x8240D334 passes the view-projection matrix, Im3d renderer (this+0x10E0), blobby texture (this+0x37F0), alpha (this+0x37F4), and frame white level. It runs before BeginForceStencilWrite at 0x8240D348, outside the stencil-write window.

DecFIGS export 0x3795C8 carries mangled signature Render(rw::math::vpu::Matrix44, CgsGraphics::Im3d*, renderengine::Texture*, float, float). The declaration uses that by-value matrix and typed pointers. ARTIST assembly, rather than decompiler parameter guesses, confirms call registers and the caller's stack matrix.

## Recovered behavior

The manager selects maBuffers[mu8Internal], initializes a function-local static lfMaxOpacity = firstCallAlpha * 255, then returns for a nonpositive record count. With records, it begins Im3d, sets the supplied view-projection transform, asserts and binds the blobby texture, then applies depth slot 2 (ZON_ZLEQ_ZWRITEOFF), rasterizer slot 2 (SCISSOR_CULL_MODE_NONE), and blend slot 1 (TRANSPARENT_MODULATE_NO_ALPHA_TEST_DEST_RGBA).

For each 64-byte record, ARTIST clamps height * reciprocal(1.25) to [0,1]; the height lane contains one broadcast value. Alpha is truncated from cachedOpacity - cachedOpacity * fade. Spread is 1 + 0.4 * fade. Front/rear outer anchors use the front/rear extents multiplied by spread; axle anchors use their unscaled extents; the right half-width vector is multiplied by spread. Eight vertices form one primitive-6 triangle strip per record in front outer, front axle, back axle, rear outer pairs, with UV rows 0, 0.1875, 0.8125, and 1.

The vertex code writes explicit RGBA8{r,g,b,a} fields: three truncated whiteLevel*255 bytes and the per-record truncated alpha byte. It does not infer channel order from a packed integer convention. The static opacity is original behavior: the ARTIST guard initializes it from the first alpha argument and never refreshes it, so later debug edits do not replace the cached opacity. The proposal preserves this.

## Real PC sink and integration

The selected PC path already has real implementations: Im3d::BeginRendering binds program 0 and the vertex descriptor; SetTransform, raw SetTexture, and typed state setters exist; ImRenderer<BasicColouredTexturedVertex>::Render packs the 32-byte CPU vertex to the existing 24-byte position/RGBA8/UV stream and calls D3DDevice_BeginVertices; the Xenon D3D9 shim maps Xenos topology 6 to triangle strip and D3DDevice_EndVertices submits through GeometryBindingsPC::DrawPrimitiveUP. No renderer primitive or texture API is invented.

The matrix comes from DispatchThreadInputBuffer::mOcclusionViewProjectionMatrix (member declaration at line 222; ARTIST copies it before the call). The existing Render white-level local is passed into RenderWorldPasses, matching ARTIST f26. GamePrepare asserts the acquired lpBlobbyShadow texture and passes it to PrepareAgain; that method stores the pointer in mpBlobbyShadowTexture.

The PC lbTransparentWork optimization depends on transparent mesh-list counts. ARTIST calls the shadow manager under both original switches even if lists 15 and 20 are empty. The proposal keeps the world-transparent list gate, separates the car-transparent monitor/call window from that count-only wrapper, and calls the manager under its original switches plus PC availability guards (mbIm3dRendererConstructedPC and nonnull dispatch input). The call stays before stencil and list-20 work. Cleanup adds a default-state reset only when the manager's internal count was nonzero; with an empty buffer, the manager still initializes the static opacity and returns without changing device state.

## Remaining behavior gap

Exact c36 source has no live BrnBlobbyShadowBuffer::AddShadow caller: git grep AddShadow finds its definition, an embed-check helper, and commented traffic placeholders only. The buffers are initialized, reset, swapped, and published through renderer/world IO, but no active producer currently writes a shadow record. This proposal closes the missing debug-flag/alpha-to-renderer consumer and the existing PC draw sink; it does not claim that current source can produce blobby-shadow pixels until a producer is separately recovered. No producer is guessed or added here.

All changed files and pinned source dependencies were compared byte-for-byte between c36 and 8b; the hashes and Git blob IDs are in bindings.json. The source basis is the exact c36 private commit, not the older physical B5 checkout. The existing graphify map is dated 2026-10-09 and stale against these commits; no graph edge was treated as behavioral evidence.

## Verification boundary

No C++ was compiled, and no fixture, native, game, CI, or IDA operation ran. The source-level postmortem is in POSTMORTEM.md. Review and hosted validation remain with the root task.
