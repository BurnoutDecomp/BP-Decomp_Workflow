# Conditional occlusion query polarity investigation

**Status:** read-only evidence review, 2026-10-23. No source change, compile, native run, or runtime claim.

## Finding

The current host predicate `sampleCount != 0` means “draw this mesh” and is consistent with the strongest evidence found. Do not invert it. Microsoft's Direct3D 9 documentation defines `D3DQUERYTYPE_OCCLUSION` as the number of samples passing Z testing; zero means fully occluded/not visible, while a nonzero value means visible. Xenia's Xenos VIZ implementation describes VIZ as conditional rendering/predication that skips draws that are not visible and represents completed query state as `visible`. This corroborates a positive-visible mapping. ARTIST routes through opaque XDK routines, so its call/packet code alone does not literally show the boolean compare; there is no runtime verification in this investigation.

## Original ARTIST chain and encoding

- `CgsGraphics::OcclusionCullManager::RenderOccludeeBoundingBox` (`0x827EE010`, export SHA-256 `F202303D5F05DA6614A65430F7240633D4860F059DFE7DE8A5A537D374BE9BE0`) records `miNextQueryIndex` as the current occludee's query ID. For a box that is trivial/near-plane-crossing it stores `0xFFFF` instead. The visible query arm calls `D3DDevice_BeginConditionalSurvey(device, miNextQueryIndex, 1)`, draws the occludee box, then calls `D3DDevice_EndConditionalSurvey(device, 0)`; the ID and occludee indices then advance.
- `CgsGraphics::OcclusionCullManager::BeginMeshConditionalRender` (`0x827E8F18`, SHA-256 `E92E57AC336426BBF252A452D11F2F22A15A3717460E029CA025CE18C5724E8B`) loads the matching `maQueryIds[miOccludeeIndex]`, sign-extends it as `s16`, and forwards that same ID to `D3DDevice_BeginConditionalRendering` unless it is `-1` (`0xFFFF`). The end function closes the region unless the sentinel is present.
- XDK `D3DDevice_BeginConditionalSurvey` (`0x82949E90`, SHA-256 `BF279088A20C2EF384920FB5A4D3D56D293BF7EDCC5EC75275172730873191D7`) masks `Identifier` to its low six bits (`Identifier & 0x3F`). It also folds `Flags` bit 0 into the VIZ setup word (`(Flags << 6) & 0x40`, then shifts the combined value left once); it stores `(Flags << 6) | Identifier` in the nested-survey stack. `D3DDevice_EndConditionalSurvey` (`0x82949F68`, SHA-256 `296801AFBEA98F610FC0ED35418BCE57DE583AF85D3B2169A68393BDB02A2130`) takes the low six-bit ID from that stack and emits the end marker when `Flags & 1` is zero. The game call site uses begin flag 1 and end flag 0, as noted above.
- XDK `D3DDevice_BeginConditionalRendering` (`0x8294A038`, SHA-256 `EBFE79F02118874AC02117F4BFAB9AEF39581E90CA04CAFC81CFC85346B105DF`) stores the identifier in its conditional-render stack; the body itself does not perform a CPU query-result comparison. The matching end is `0x8294A1F8` (SHA-256 `0AF5D0C3F37E4AD672EA23A4BCE67DD1DD5DC9F082BB2644FEDF3CD44CD28C8A`).

## Host implementation evidence

- `b5-decomp/src/pc/gcm/renderengine/OcclusionQueryProviderPC.cpp` (SHA-256 `35C4C5883125E69C6BAA2F9F5205F64CE14D83C1B2CCC4C4DF8C851CD7809280`) resolves a host query result and returns `lrSlot.muSampleCount != 0`; unavailable, stale, or failed results fail open. That is the correct D3D9 visibility interpretation.
- Microsoft, [D3DQUERYTYPE enumeration](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dquerytype), says the occlusion query reports samples passing Z testing and that zero is fully occluded. [Queries (Direct3D 9)](https://learn.microsoft.com/en-us/windows/win32/direct3d9/queries) demonstrates rendering when the query result is nonzero and recommends treating unavailable results as visible.
- Xenia-canary's [VIZ query implementation](https://github.com/xenia-canary/xenia-canary/blob/canary_experimental/src/xenia/gpu/command_processor.cc#L2315-L2334) describes VIZ as the Xbox 360 conditional-rendering/predication query feature and says it can skip draws that are not visible. Its [query lifecycle](https://github.com/xenia-canary/xenia-canary/blob/canary_experimental/src/xenia/gpu/command_processor.cc#L3736-L3867) tracks a Boolean `visible` result and accumulates visible segments. This is an emulator implementation/reference, not a replacement for ARTIST as the behavioral spine.

## Boundaries

This pins the host D3D9 query's visible/nonvisible mapping and finds no supported polarity inversion. It does not decode every XDK flag or prove the Xenos hardware's internal predicate equation from ARTIST machine code; the XDK implementation is opaque at the API boundary. No change to `OcclusionQueryProviderPC` is proposed. No gameplay, native, build, or verified-site credit is claimed.
