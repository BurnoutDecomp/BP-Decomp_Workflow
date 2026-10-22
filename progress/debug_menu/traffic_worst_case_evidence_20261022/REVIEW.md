# Traffic Running Worst Case #0086 candidate evidence review

VERDICT: pass

`BrnTraffic::DebugComponent::OnActivate#0086` has adequate original-source, completed consumer/effect and restoration evidence for **this exact private candidate and this one enable/disable cycle**. No material evidence is missing for that bounded disposition. This verdict does not pass the whole case or any other site.

Source: `d9de0ab1d395425eb39d0fdbb5e70f93235d601a`. Executable SHA256: `932a7f98668990c34a64a9885f0bba8dafaf1eabd1ba1b2447ed41258cf3f604`. The retained source images equal its three exact Git objects, the run target/provenance binds that source and executable, and the actual staged executable matches. Normal checked-out source identity is separate from the executable's candidate identity.

## Original chain and actual consumption

ARTIST OnActivate82762530 registers Performance/Running Worst Case to the owner module byte+0x729F0. Its RecalculateActiveHulls8274C870 reads that same byte, requires a decision frame, and selects the original15-u16 table on the true branch. The candidate preserves that chain at DebugComponent.cpp397 and EntityModule.cpp3550,3572-3583, then sorts/differences/rebuilds before publishing at3821-3844. The ordinary false branch uses the race-car hull sets.

RenderHUD82760AB0 gates DrawActiveHulls8275B2E8 using the original active-hull draw flag. The candidate reads current direct PVS dimensions, maps IDs by modulo/division, calls the original2D DrawBox/DrawLine paths and only then commits a diagnostic pair. The witness03 guard requires matching module/PVS identity, current epoch/phase, ready resource, toggle, full ordered active IDs and actual box/map counts. SET and DRAW decision fields are separate observations. Supporting PVS, owner/debug declarations, resource and2D-renderer/DebugManager source blobs remain identical to the frozen original closure. No numeric hull labels are part of the original overlay.

The log contains exactly six PVS records, and every receipt raw line matches its original source line:

| State | SET/DRAW source lines | Epoch / set-call / draw-seq | Completed active IDs |
| --- | --- | --- | --- |
| baseline | 13866 / 13867 | 144 / 144 / 1 | 101,102,122,123 |
| on | 34052 / 34053 | 145 / 517 / 2 | 98-102,119-123,140-144 |
| off | 36714 / 36715 | 146 / 572 / 3 | 101,102,122,123 |

All pairs have readiness/PVS/draw-toggle=true, matching phase/epoch/consumption sequence and exact full draw maps/counts. The producer samples are decision_frame1/frames_since_decision0. Baseline DRAW independently records0/5, which is allowed and was not forced equal. On adds the11 non-baseline IDs; off removes those same11. Completed original drawing consumption therefore shows4->15->4 and restoration of the same ordinary map.

## Actual pixel inspection

I inspected all three unmodified BMPs with `view_image`, independently of Root's written observations. The upper-left grid occupies(80,80)..(250,250), with21 columns and15 rows. I observe:

- `hud.bmp`: cyan2x2 block at zero-based columns17-18, rows4-5. Original mapping gives IDs101,102,122,123.
- `params.bmp`: cyan5x3 block at columns14-18, rows4-6. This is the15-cell on set98-102,119-123,140-144.
- `param-fuzzy.bmp`: cyan2x2 block restored to columns17-18, rows4-5.

The block locations and extents match the source geometry and direct21x15/315-cell DRAW data. The images do not print numeric IDs; the ID interpretation comes from the original mapping and exact consumer records. Each retained image is byte-identical to its named original backbuffer and matches phase-frames.json:

| Phase | Original frame | SHA256 |
| --- | --- | --- |
| hud | bb_005760.bmp | `a414a0f5f8392ff03acf09698f505b6f9b852b0fb0265190928dc07abde5dda3` |
| params | bb_009720.bmp | `c46a62889e7111b0e8d3bc7b8061885ed17b14c8f92e126b4e2824327dd91b31` |
| param-fuzzy | bb_010200.bmp | `e302aa05b16817aed99c54584b206a6103b70f12700aa8aab12d321671153a20` |

These are phase-associated visual observations. No shared engine/render frame ID ties a screenshot to a particular SET/DRAW record, and I do not certify same-frame pixel attribution.

## Limits and unchanged failed case

The same-console-batch Active hulls reads remain4 when TRUE is written and15 when FALSE is written. Their original path/value lines match the readback file; they precede the completed decision/draw evidence and are not used as effect witnesses. A gate that demands those early counts immediately equal15 and4 remains unsatisfied; it has not been weakened or rerated.

The original case result remains FAIL. Its missing manual #0086 review,13/15 captures (off/cleanup absent after the96-frame cap), and absent complete74-site manual review remain recorded. This separate bounded review does not alter that result or manufacture aggregate74-site credit. The retained terminal/log show0 assertions/exceptions and complete owned cleanup; that supports attribution and run integrity, not unrelated gameplay claims.

All six packet manifest rows and20 pinned external inputs match exact hashes/sizes. Packet manifest SHA256: `b63f13511b683e1cf816123295a0eb176da710441d43fb08fae3bb6d448f3997`. `SOURCE_BINDINGS.json` retains all additional inspected source/export/image/run hashes and the actual observations. Broader locations, repeated cycles, long-session behavior, normal/public delivery and exact same-frame association would need separate evidence.

No new compiler/build, fixture/helper/case, game/UI, hosted workflow, IDA or installer was executed. No tracked source, ledger, prior packet, run artifact or normal file was edited, and no commit/push occurred. Only this new review directory was written.
