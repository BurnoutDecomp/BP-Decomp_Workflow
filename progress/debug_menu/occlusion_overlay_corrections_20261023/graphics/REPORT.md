# Occlusion cursor and matrix-getter correction

## Status

This immutable source-only proposal is based on private b5-decomp `9cbefd173085312ebaee5bab4875b8492fc292cb`, which contains the independently reviewed blobby-shadow Render recovery and five GUI event posts. It preserves the previous corrected cursor behavior and replaces the unneeded friend workaround with the public getter attested by DecFIGS. It supersedes the earlier friend-based packet at `scratch/DEBUG_MENU_1011/graphics_occlusion_cursor_delta_20261023/`; that packet is left unchanged.

No production source, inventory, behavior disposition, Git state, build, tests, CI, native runtime, game, Stage, or input was touched. This packet has no compile, runtime, or debug-menu verification credit.

## Recovered accessor shape

DecFIGS `BrnDispatchThreadInputBuffer.h` declares a public `const Matrix44& GetOcclusionViewProjectionMatrix() const` at h:160 and the private matrix member at h:79. The source-facing inline body is the exact field-reference return. ARTIST Render `0x8240BFA8` locks the dispatch input at `0x8240C1C0`, computes `input + 0x99C0` at `0x8240C1C8..C1D0`, loads all four 16-byte rows at `0x8240C1E4`, `0x8240C1F0`, `0x8240C1F4`, and `0x8240C1F8`, then unlocks at `0x8240C220`. That is the inlined getter's field read. The getter itself adds no lock assert because the original Render consumer holds the read lock around the access.

Both the already-reviewed blobby `Render` call from the 9cb base and the new occlusion setup now call this getter. The new `BrnRendererModule` friend declaration and global forward declaration from the previous delta are removed. No member offset or layout changes.

## Cursor correction retained

`DispatchList::DispatchAllMeshes` returns its computed bounded end cursor when more records remain, and `-1` only when the cursor reaches total. ARTIST `DispatchAllMeshes` (`0x827F2718`) returns the capped `v473` unless it equals total. ARTIST Render uses that return to advance the 64-record loops for car opaque list 19 (`0x8240CF10..0x8240CF64`) and world opaque list 11 (`0x8240D068..0x8240D0C4`). No wrapper increment is used.

## Evidence and review boundary

The six files in `source_preimage/` match the 9cb base. `source_postimage/` contains the cursor correction, getter recovery, and original occlusion proposal; the reviewed blobby call remains in place. `diff.patch`, `bindings.json`, and `INTEGRITY.sha256` bind the exact source and DecFIGS/ARTIST evidence. The original occlusion FAIL packet remains immutable and carries no new credit.
