# Fresh-eyes review: graphics occlusion recovery

VERDICT: fail

## Blocking finding

The new opaque-list loop does not continue after its first 64-record batch. In the postimage, `BrnRendererModule.cpp` lines 4723–4747 return the draw walk's result from `DispatchOcclusionBatch` and use it as the next `liFirst`. But the unchanged `DispatchList::DispatchAllMeshes` body in `CgsDispatcherCommands.cpp` returns `-1` unconditionally at line 1417, including when `liCount` limits the walk to 64 while more records remain. Therefore, for any opaque list with more than 64 records, the loop exits after drawing only its first batch; later records get neither query nor draw.

ARTIST `BrnRendererModule::Render` (`0x8240BFA8`) uses the draw walk's return as a continuation index: the car-opaque path repeats the query/draw pair while the result is not `-1` (`0x8240CF10`–`0x8240CF64`), and the world-opaque path has the same pattern (`0x8240D06C`–`0x8240D0C4`). ARTIST `DispatchList::DispatchAllMeshes` (`0x827F2718`) returns the next record index unless it reaches the list count; the supplied PC body does not. The patch needs that original continuation behavior in the dispatcher or an equivalent wrapper that advances both query and draw walks over the same bounded range. Transparent lists use a single full-list walk, so this specific return mismatch affects the batched opaque paths.

## Evidence that matched

The remaining recovered chain matches the pinned ARTIST exports: renderer construction passes query-list capacity `0x2000` to `OcclusionCullManager::Construct` (`0x8240BF48` / `0x8240BF64`); `Render` publishes the manager and index threshold (`0x8240C0E4` / `0x8240C0F8`), copies the dispatch camera matrix into the manager, and writes the near-clip scalar into its z lane (`0x8240C1FC`–`0x8240C210`, `0x8240C138`–`0x8240C178`). The four pass gates and list IDs match the source packet. In the mesh walker, ARTIST binds mesh buffers, begins the conditional bracket, draws either instanced or indexed geometry, then ends the bracket (`0x827F59E8`, `0x827F5A30`, `0x827F5A4C`/`0x827F5A7C`, `0x827F5A8C`); the added calls follow that order.

The renderer adds the exact 512 KiB query-matrix reservation for `0x2000 * 64` bytes and preserves the debug-manager booleans across deferred construction. The attachment makes no new inventory rows or bodies for #0022, #0032, #0040, #0043, or #0045–0047. DecFIGS `0x13A40` supports the constructor collaborator/parameter shape; ARTIST remains the behavioral authority. The packet's 44 integrity entries all validate, and all 15 included ARTIST/DecFIGS export copies hash-match the workspace exports.

## Limits

This review covers the supplied `9af6a868…` pre/post snapshots and static evidence only. No Git comparison, build, test, CI, native run, game/stage run, or input execution was performed. No runtime or site credit is granted. The D3D9 conditional-query provider remains a host-specific seam; ARTIST does not establish Xenos conditional polarity, and the CPU monitor registration for `miDispatchOcclusionQueries` remains unresolved. Deferred construction also latches a failed program setup off for the renderer lifetime; that fail-closed path and device-reset/recreate behavior were not exercised.
