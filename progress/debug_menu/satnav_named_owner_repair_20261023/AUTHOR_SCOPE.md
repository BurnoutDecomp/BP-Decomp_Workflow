# SatNav named-owner source recovery proposal

## Decision

This packet proposes a source-only replacement for the guest-layout access in `SatNavDebugComponent::TriggerSatNavPositionUpdate`. It uses `GuiModule::mCustomRendererManager.mSatNavRenderer`, rebuilds that renderer's transform, and writes its named `mMapQuadColour` field. A declaration-level friend grants the debug component access to the manager's private embedded renderer. The two obsolete `KU_OFF_SATNAV_*` constants are removed after a tracked-source search found their only uses in the old body and their declarations.

The proposal also makes the alpha calculation match ARTIST's single-precision multiply and truncate-toward-zero conversion. It preserves the rect store, assertion, transform call, alpha packing, and call/store order. `RenderHUD` remains byte-for-byte unchanged, including the previously reviewed `0xFFFF0000u` outline color.

No code was applied to `b5-decomp`. This packet earns no behavior or compilation credit. No compiler, fixture, native/game run, IDA, CI, production/index mutation, or commit was used.

## Source anchors

- Proposal base B5 commit: `b9e6a93e43948aae1e2e187ce5957d84db2d2e37` (tree `a8bc5a8ce4ad9d9505fb8a06f079caff82a926ca`).
- Physical B5 checkout at capture: `91a0ed564f9c9e3dec915bfb416c0467650084ef` (tree `152be7fd5db9c3c367c7b739e01075744dba8fb5`); its worktree was clean at capture. The proposal deliberately uses the supplied base commit, which is not the physical HEAD.
- The parent workflow checkout had 9 dirty/untracked paths at capture. No shared source or existing scratch packet was modified.
- The previous `gui_owners_satnav_integration_20261020` review explicitly retained the SatNav guest-offset debt. The later `gui_validation_cast_and_satnav_colour_repairs_20261023` postimage still contains those accesses and addresses a separate RenderHUD color correction. Neither packet is used as source authority here.

## ARTIST behavior and alpha packing

The frozen `evidence/artist/0x8250DA58.json` binds the original function at `0x8250DA58`. It copies the four rect floats from component offsets `0x18..0x24` to the live `MapTransform` vector, checks `miSatNavAlpha <= 100`, then calls `SatNavRenderer::UpdateRendererTransform` using the native renderer address. The same function loads the alpha word, masks to its low byte, converts that value to single precision, loads `flt_820552E0` (pseudocode value `2.55`), uses `fmuls`, converts with `fctidz` (toward zero), extracts the low result byte, and inserts it into the packed color's top byte before the store. The pseudocode also spells the packed result as `(scaledAlpha << 24) | 0xFFFFFF`.

The proposed `f32` multiply plus `static_cast<s64>` preserves the single-precision operation and truncation direction, followed by `u8` low-byte extraction. The packed word remains `(alpha << 24) | 0x00FFFFFFu`. The renderer's existing body interprets that word's high byte as alpha and the remaining RGB bytes as white; the exact B5 renderer source is frozen under `dependencies/`.

The ARTIST export labels the multiplier `flt_820552E0` and its pseudocode resolves it to `2.55`; the frozen export does not include a separate raw data-word dump. The proposal therefore uses the represented single-precision literal `2.55f` and does not claim an independently captured constant word.

## Named ownership and declaration shape

The exact B5 base source provides `GuiModule::mCustomRendererManager` and already declares `SatNavDebugComponent` a friend of `GuiModule`. `CustomRendererManager::mSatNavRenderer` is private, so the proposal adds only `friend struct SatNavDebugComponent` to that manager. `SatNavRenderer` already grants the same friend access to its private `UpdateRendererTransform` and `mMapQuadColour`.

The DecFIGS dumps corroborate the by-value ownership and declaration shape. They use older spellings (`mCustomRenderManager` and `mSatNavRendererInstance`) for those members; the proposal follows the pinned B5 source's actual names. DecFIGS also supplies the component member shape and the renderer's packed-color field. ARTIST remains the behavioral authority.

## Files

- `preimage/` and `postimage/` contain complete files for the three proposed source paths.
- `source.patch` is the complete unified diff.
- `dependencies/` contains exact source blobs from the pinned B5 base for the owner chain, renderer readers, and live rect API.
- `evidence/artist/` contains the original function and transform-helper exports; `evidence/decfigs/` contains the corresponding DWARF dumps.
- `SOURCE_BINDINGS.json` records each exact B5 Git blob, SHA-256, captured physical checkout, and evidence source path.
- `INTEGRITY.sha256` seals the packet payload files; `INTEGRITY.sha256.sha256` seals that manifest.

## Validation boundary

The only validation performed was source/evidence inspection and packet integrity verification. No compile or fixture result is claimed; any C++ build or fixture work must run in the hosted environment. Root owns any later review, hosted validation, publication, and reconciliation.
