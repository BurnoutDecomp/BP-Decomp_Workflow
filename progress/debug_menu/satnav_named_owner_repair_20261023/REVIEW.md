# Independent SatNav named-owner recovery review

VERDICT: pass

No source-fidelity or declaration-access defect was found in this narrow proposal. The named owner chain, statement order and alpha operation sequence are supported by the inspected base sources, ARTIST instructions and DecFIGS declarations. Approval applies to the three exact proposed postimages on the pinned base. This packet establishes no compile, fixture or runtime behavior result.

## Exact base and patch

The proposal is bound to B5 commit b9e6a93e43948aae1e2e187ce5957d84db2d2e37, tree a8bc5a8ce4ad9d9505fb8a06f079caff82a926ca. Read-only Git resolution plus independently computed Git blob IDs confirms all three complete preimages and all six dependency files match that base. All six frozen ARTIST/DecFIGS evidence files also match their actual original source files by SHA-256.

All five unified-diff hunks were checked against complete pre/postimages. In-memory reconstruction reproduces the exact postimage text for all three files. No patch was applied to any working tree. The manager header changes only by its friend declaration and comment; the component header removes obsolete layout commentary and the two offset constants. No unrelated C++ body changes appear.

## Named ownership and access

The pinned GuiModule header includes the complete manager type at line 45, already grants friend struct SatNavDebugComponent at 321, and embeds CustomRendererManager mCustomRendererManager at 473. The manager includes the real SatNavRenderer header and embeds SatNavRenderer mSatNavRenderer (postimage line 176).

SatNavRenderer already grants the same friendship at its line 64. Its UpdateRendererTransform method (160) and mMapQuadColour word (172) are private members. Adding friend struct SatNavDebugComponent to CustomRendererManager at postimage line 142 supplies the only missing access declaration. All declarations belong to BrnGui; no accessor shim, alternate object, field redefinition, public exposure or layout accommodation is introduced.

DecFIGS corroborates by-value ownership through GuiModule::mCustomRenderManager and CustomRendererManager::mSatNavRendererInstance, and identifies the renderer's mMapQuadColour field. Those older spellings do not override the pinned host source's existing names. The component's alpha is uint32_t and its position-update declaration is void; the apparent int return in pseudocode is not used as declaration authority.

The new reference in component postimage line 276 names the live embedded renderer. Both UpdateRendererTransform at 277 and the mMapQuadColour store at 284 use that same reference. The unchanged host transform helper reads the live MapTransform viewport and writes the renderer's transform fields; it does not rebind the component's module owner. Using one reference across that call preserves the same target identity.

## ARTIST behavior and alpha arithmetic

TriggerSatNavPositionUpdate at ARTIST 0x8250DA58 establishes this order:

| ARTIST instructions | Proposed source counterpart |
| --- | --- |
| 0x8250DA74..DA9C: load four rect floats and store their vector to unk_82FB36A0 | Lines 265-270 publish the same four named fields through SetSatNavRect. Its frozen body is only smv4SatNavViewRect = lv4Rect. |
| 0x8250DAA0..DAC8: unsigned compare against 100, then original alpha assertion | Line 272 retains the same unsigned alpha assertion after the rect store. |
| 0x8250DACC..DAD8: call UpdateRendererTransform on module +0x4D2E0 | Lines 276-277 use the named embedded SatNavRenderer. |
| 0x8250DADC..DB24: load/mask alpha, convert/multiply/truncate, then store the packed color to module +0x4D2E8 | Lines 280-284 retain that operation sequence and store the named renderer color. |

The original transform-helper export at 0x8245F4D8 reads the same global viewport. Its numeric console-to-host transform implementation is unchanged by this proposal and is not recertified here.

For alpha, clrlwi at 0x8250DAE8 retains only the low input byte. fcfid then frsp converts that 0..255 value to single precision exactly. lfs loads flt_820552E0, fmuls at DB10 performs a single-precision multiply, and fctidz at DB14 truncates toward zero into a signed 64-bit integer representation. The big-endian stfd followed by lbz at stack +7 extracts the result's low byte. insrwi r10,r11,8,0 inserts that byte into the packed word's most significant byte; the initial lower 24 bits are 0xFFFFFF.

The proposed expression first masks with 0xFFu, converts to f32 and multiplies by 2.55f into an f32 local. The next conversion to s64 expresses truncation toward zero; conversion from s64 to u8 supplies the low byte. The final unsigned shift by 24 and OR with 0x00FFFFFFu express the packed store. The pinned types.hpp defines f32 as float, s64 as int64_t and u8 as uint8_t.

The masked input bounds the finite product to approximately 0..650.25, so the signed conversion is in range even if an out-of-range original alpha is allowed to continue past the assertion. The u8 conversion remains a low-byte extraction; there is no invented saturation or clamp. The explicit float literal also preserves the single-precision multiply that the old unsuffixed 2.55 expression failed to state.

Evidence limit: the frozen pseudocode identifies the multiplier as 2.55 and the assembly fixes its load address and single-precision use, but the packet contains no independent raw data-word capture for flt_820552E0. This pass supports 2.55f as represented by that export; it does not claim separately verified constant bits or a compiled numerical result.

The frozen renderer readers interpret the high byte of mMapQuadColour as alpha and its other bytes as RGB. This agrees with the new packed-white word and requires no renderer change.

## Obsolete offsets and preserved RenderHUD

An independent git grep over the pinned base's tracked src tree reproduces BASE_OFFSET_SEARCH.txt exactly: two offset uses in this component body and the two header declarations, four hits total. No other tracked source use exists at that base. The proposal removes all four and neither constant token remains in any changed postimage; the unchanged remainder of that tree therefore has no remaining use.

RenderHUD is exact and unchanged, including 0xFFFF0000u. Its 671-byte UTF-8 function extent, from the declaration through the closing brace and excluding the following linefeed, hashes to 5efeae1fcdb95d6af37beb994aa4da1f44901550f541277ee9b11b4c8b10c13b in both images. No new RenderHUD or whole renderer behavior approval is inferred from preserving those bytes.

## Complete source SHA-256

| File | Preimage SHA-256 | Postimage SHA-256 |
| --- | --- | --- |
| BrnGuiSatNavDebugComponent.cpp | b40b11913e4c8b214aab61ea9648a21721a665a2d7d8b3a50c3231ac89d8ab8a | 0742d9e8b4bf388ec32d9b5ad902c742557b22a8ca0b2419d149a3e76b1aa96d |
| BrnGuiSatNavDebugComponent.h | 4c4ddcc488a023673ce4356a85be70746d6534c28d85267a80c9f5746931deef | 83080e269c92741c18488b5d2637544935bfcfd3f258d07d83825d8c69dab549 |
| BrnCustomRendererManager.h | 484550ea6855a293d7e98fa6553edea503d4dad5cf6ccb8dbc4cec6e20b8ef3a | 221b0e4a17039fdb9ea5ff5f8659e19de8dc186e7bbd9533e001ad29e2b8b930 |

Postimage sizes are 15,664, 5,471 and 16,996 bytes respectively. Full paths, exact Git blob IDs, dependency/evidence hashes and verification details are in REVIEWED_INPUTS.json.

All 23 packet payload entries verify, with no unsealed payload file. INTEGRITY.sha256 hashes to afd391641527560c7b9eaaee3f519fb6ab344440c7124c24efec01420e6cd3ae; its exact sidecar verifies and hashes to 0dc892b5ac14ef102051d8a82f24ad88cc290be509c36abe7df82cffafb3ffc8.

Only this new sibling independent review folder was written. No compiler, fixture, game/native process, CI, IDA, production/index mutation, commit or subagent was used. Root owns any later integration, validation or publication. INTEGRITY.json binds this report and input manifest; SHA256SUMS.txt additionally seals INTEGRITY.json without self-reference.
