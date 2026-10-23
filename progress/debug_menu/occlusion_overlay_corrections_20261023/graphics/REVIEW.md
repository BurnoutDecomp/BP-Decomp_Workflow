# Independent review: occlusion getter/cursor delta

VERDICT: pass

The final packet corrects the previous access-evidence failure. It uses the DecFIGS-declared public getter for both occlusion and blobby matrix reads, removes the friend workaround, and preserves the previously reviewed continuation and blobby-render composition.

## Getter and matrix access

The bound DecFIGS source is `references/DecFIGS/dwarfdump/GameSource/Game/BrnDispatchThreadInputBuffer.h`, SHA-256 `11be9bdd1720b43f59fe355810fb6c38926a7f6c83a5b02c82bc98c039b3d999`: h:79 places `mOcclusionViewProjectionMatrix` under `private`, and h:160 declares public `const Matrix44& GetOcclusionViewProjectionMatrix() const` (h:163 is the setter). The new inline body returns that member by const reference and introduces no lock assertion or data member. The friend and global forward declaration are gone.

ARTIST `BrnRendererModule::Render` export `0x8240BFA8` is bound by SHA-256 `e2a24cd90d2818974a6eb622f9b213fd4c4be71766cc504769b484da0bb464e5`. It calls `LockForRead` at `0x8240C1C0`, computes the member address at `0x8240C1C8..C1D0`, loads the four 16-byte rows at `0x8240C1E4`, `0x8240C1F0`, `0x8240C1F4`, and `0x8240C1F8`, then unlocks at `0x8240C220`. On the PC source path, `Render` acquires the read lock at line 5261 before calling `RenderWorldPasses` at 6142 and releases it after that call; the new accessor itself remains a plain field-reference read. Both the manager matrix copy and the existing blobby `Render` call use the accessor under that lock.

## Composition and cursor

The dispatcher cursor correction is unchanged from the prior reviewed packet. ARTIST `DispatchAllMeshes` `0x827F2718` (SHA-256 `f5c20d3e87105d7dcc6f93873cbb94b3174d2d7ba072eb048c5efb4817ea1109`) returns the capped end cursor unless it reaches total, then `-1`; ARTIST Render uses that return for both the 64-item list-19 and list-11 loops. The bound `CgsDispatcherCommands.cpp` postimage hash remains `7114a03771a620998c57b82e7ba70fcc95c4f2d5f64ea9ef5af060e3eb6377eb`, matching the previously reviewed cursor implementation.

The car-transparent block still calls `mBlobbyShadowManager.Render` before list 20 with the same renderer, texture, alpha, and white-level arguments; only its matrix expression changes to the getter. The original failed occlusion packet and the intervening friend-based fail packet were not modified. The earlier noted zero-length nonterminal subrange edge is unchanged and does not apply to these callers, which supply 64 or `-1`.

## Source pins and limits

All six preimage files match the 9cbefd base by Git blob ID, and all six postimage SHA-256 values match `bindings.json`:

- `BrnRendererModule.cpp`: `bd9c8ce4d2d7909169b302b4dc7ab8c7393ef9b97afb0d0d61920160e09438d0`
- `BrnRendererModule.h`: `89311c6baedfa7f1e86d9eb6902f0c01e96f4d03708a60e37c733f2410274e1e`
- `BrnDispatchThreadInputBuffer.h`: `3388e1e522f7f21fa88d8ed6b5f4b75b09cf7cc2bbfde9ddaf6de6660fdea3a9`
- `CgsDispatcherCommands.cpp`: `7114a03771a620998c57b82e7ba70fcc95c4f2d5f64ea9ef5af060e3eb6377eb`
- `CgsOcclusionCullManager.cpp`: `24f6ac9bd30d20791258b2ae986661b1cb0c67bdc2b0227d1a8a197b0362a1b5`
- `CgsIm3d.h`: `1a7cafb107bd9a800be3e9b7eca3cc2988f694564b07a8ec35c2f6aa15656ddc`

No build or runtime validation was performed. D3D9 query availability and conditional-render polarity, visual behavior, and live performance-monitor output remain unverified; this pass grants no runtime or site credit.
