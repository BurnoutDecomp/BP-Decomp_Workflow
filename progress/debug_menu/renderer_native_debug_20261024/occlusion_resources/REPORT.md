# Native occlusion resource-owner recovery

This two-TU proposal targets **037deb9fecff882de2e2fb55de020e0f54348360**, workflow **451dcde251f121d624e21541f81b6fe7ced8f77f**. It changes the occlusion constructor's explicit PC resource representation and supplies the existing declared VertexBuffer::Lock API's missing native implementation. No checkout, Git state, build, tests, CI or game/input was changed. The FileSystem batch remains parked and unsealed.

Root's targeted alias run62064 read the real control FALSE then TRUE and stopped on the first allocation assertion, before any control-behavior credit. That receipt is prior evidence only; this proposal has not run.

## Actual failure owner

The assertion is in **OcclusionCullManager::Construct**, not Prepare. The actual037 caller is Renderer::EnsureOcclusionCullManagerPC, which passes **sWorldDispatchAllocator**. This real main-only arena already owns the dispatch/immediate headers and explicitly reserves the original512KiB matrix table. The different raw GlobalGraphics provider also has only a256KiB main arena, but changing that provider would not repair this actual passed-allocator request.

ARTIST827F1E00 builds a vertex descriptor with main40-byte header plus physical vertex bytes, and an index descriptor with main36-byte header plus48 physical bytes. The native WorldDispatch allocator has no lane2 backing; its canonical DoAllocate rejects such an unsupported request rather than returning a usable header. The first assertion's message says “vertex descriptor,” but the request is the VertexBuffer descriptor.

Original renderer Construct passes the genuine GlobalGraphics wrapper. Its original global owner has0x640000 main and0x1D00000 physical capacities, as the prior graphics recovery proves. That original allocation phase remains uncalled. This proposal changes neither original global capacities nor either current native arena/budget.

## Selected PC owners and lock

The shipping PC build selects ImmediateMode.cpp's VertexBuffer/IndexBuffer initializers. Both read only the supplied lane0 header pointer and allocate their real CPU payload from the **existing4MiB low-4GB arena**. They do not consume the Resource's lane2 pointer. Their headers encode those real payload addresses in the retained32-bit address field. The existing sky constructor already requests only the consumed header lane for this exact backend.

The occlusion PC branch now follows that actual contract: request the40/36-byte headers from the same passed WorldDispatch owner and use typed native wrappers for Initialize. The original full descriptors/calls remain unchanged on X360. Native Initialize still allocates the actual vertex and index payloads and can fail; no empty resource or fake success replaces it.

The raw D3D vertex-lock interface returns int. In this exact backend it returns the header's low-arena address, so the old caller's unsigned re-extension is numerically safe under the proved low-4GB contract; this run did not demonstrate pointer truncation. Header pointers themselves can be above4GB and must remain native width.

The proposal supplies the canonical already-declared **VertexBuffer::Lock** method on PC. It maps the initialized header's actual persistent CPU span, checks offset/size against the actual header, fills the real pointer-bearing LockInfo and returns failure for an invalid span. The caller uses that typed result instead of narrowing an int. The header/LockInfo pointers are never narrowed. Unlock remains the existing mapped-arena platform operation; no new GPU buffer/arena is substituted.

## Complete draw representation

Fixing allocation alone would reach another concrete consumer gap: WorldDraw_IndexedUP calls MapPrimitive, which rejects Xenos indexed QUADLIST13. The native non-indexed backend already expands each quad as0-1-2/0-2-3.

At native resource creation, the six existing box faces are now written as twelve triangles using that same split. The actual index buffer has36 indices,72 meaningful bytes rounded to80 by the existing initializer, and the native draw record uses triangle-list4/count36. The eight original vertices and the original24-entry quad member remain unchanged. All six faces are planar cube faces, so this preserves their coverage and winding. X360 retains its24-index/type13 representation byte-for-byte.

The real consumer chain is SetStreamSource/SetIndices -> actual header stash -> typed header address resolution -> WorldDraw_IndexedUP -> MapPrimitive4 -> DrawIndexedPrimitiveUP. The update does not touch the generic draw backend, fabricate a visibility result, skip a draw or change query capacity. Matrix/accept-bit allocations, query stages, debug flags and the deferred renderer caller remain unchanged.

## Lifetime and review limits

Headers, query metadata, matrices and accept bits retain the actual WorldDispatch lifetime. Native payloads retain the existing process-lifetime mapped arena; typed local wrappers do not escape Initialize. The manager still constructs once through the existing deferred owner. No startup, sky preparation, buffer reconstruction, thread start or original global allocation call is added.

BRN_RENDER_PREPARE_DIAG gains a real resource witness: manager/passed allocator, full header/data pointers, actual sizes/stride, query metadata/matrix/bit pointers and final index count. Those diagnostics have never run. They are inputs for Root's future attributable validation, not runtime proof.

Both CPPs are already mounted through the exact shipping build_game_exe.bat/compile_exe.py path. Complete source/primary/provider bindings and console-branch/removal audits are included. Fresh source review, hosted gates and Root-owned native testing remain required. The current user game is untouched; no IDB/helper/native launch was made for this occlusion packet. Counts remain50 verified /7 no-ops /1298 pending of1355, with no individual control credit.
