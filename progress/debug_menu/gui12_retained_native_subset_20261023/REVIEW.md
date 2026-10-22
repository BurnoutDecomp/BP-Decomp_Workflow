# Independent GUI12 retained native subset review

VERDICT: pass

This verdict applies only to the eight bounded visual sites below. The retained original aggregate remains **FAIL**, and its result, report, log and evidence are unchanged. Four withheld sites remain pending; the paired MiniMap readback row receives no separate behavior credit. Earlier source approval and newer private Replay/GUI source work are separate from this native review.

The reviewed executable is `6fa903ebd3200ec46104b47bda8eb0e81d835d0ce6e003da370c11deb14c203a`, bound to source `91a0ed564f9c9e3dec915bfb416c0467650084ef`, hosted run 39855395071. Retained native run: `gui_behavior_batch_62049_native_20261023/runs/native_20261022_224327_cc3d2d0d`. No new game, harness, C++ build, fixture, CI or IDA process was executed for this review.

## Per-site dispositions

I directly viewed every one of the 26 selected original 1280x720 phase images. These are my image observations, not acceptance of Root's pixel review. `SITE_DISPOSITIONS.json` provides exact site identities, frame paths/hashes, raw readback triplets, limits and observations for all 26 phases.

| Site | Disposition | Direct evidence and accepted scope |
| --- | --- | --- |
| GuiDebug#0001 — Render GUI Objects | pass | baseline 6120 -> hidden 6240 -> restored 6360: boost/flame/x2 and lower-right HUD disappear and locally return; b000/r000/r001 are TRUE/FALSE/TRUE. Only this initial local interval passes. |
| GuiDebug#0014 — Toggle MiniMap | pass | 6360 -> hidden 6720 -> restored 7080: map tile/icons disappear and return while header/miles text remain. r002/r003 are FALSE/TRUE. The read-only #0015 row only corroborates this callback. |
| GuiDebug#0016 — debug speed text | pass | 7320 displays SPEED 0 mph, RPM 1000, GEAR 1 at upper left; 7560 removes the three lines. r004/r005 are TRUE/FALSE. This is visibility of the displayed stationary values, not speed/RPM data accuracy. |
| GuiDebug#0017 — 4:3 frame | pass | 7800 has a green central 4:3 frame; 7560/8160 lack it. Retained F4 binding, helper steps 30/35 and original callback/source support this callback-only effect; no alias value is invented. |
| GuiCustRenderer#0001 — status visibility | pass | 9840 shows status heading/rows;9480/10080 lack them. r008/r009 are TRUE/FALSE. Top rows are clipped/overlapping; count accuracy and complete readability are not certified. |
| GuiCustRenderer#0003 — Sat Nav Render under override | pass | 10680/11280 show the forced map patch;10440/11520 do not. r010 holds override TRUE through the explicit r011 TRUE and r014 FALSE interval; r013 confirms master TRUE before the FALSE phase. Entry absence is a visual precondition, not a separately sampled FALSE alias. Only this map gating and return to entry visual absence pass; not restoration of the actual b006 TRUE baseline. |
| GuiCustRenderer#0005 — master under override | pass | 10680 -> 11040 -> 11280 shows forced map visible/absent/visible; r012/r013 are FALSE/TRUE with the override and SatNav interval enabled. Only this map component is certified. |
| SatNavDebug#0006 — rectangle outline | pass | 12120 has a white lower-right rectangle;11760/12360 do not. r016/r017 are TRUE/FALSE. Only the outline is certified; no visible normal map is needed for this independent debug frame, and no original colour/alignment claim is made. |

Source anchors were inspected in the frozen exact 91a copies: GuiDebug registration/mini-map 205 producer/RenderHUD; Freeburn HUD case 205; custom-renderer registration, status RenderHUD and override/master/SatNav gate; and SatNav outline RenderHUD. The five original registration/RenderHUD exports match their original ARTIST bytes. The SatNav outline source explicitly describes white as a PC approximation; the accepted result is current visibility, not original-binary colour parity.

## Withheld sites remain pending

- GUI#0018 safe-area toggle and #0019 percentage: the images show a red outline, with a clear smaller 70/larger 85 rectangle contrast, while the roster calls for blue. The packed-colour contract is unresolved. No positive disposition is granted.
- CustomRenderer#0002 override: the readback is TRUE then FALSE, but its isolated entry/exit images both lack a map. It supplies a controlled context for the separate SatNav/master tests, not a separate visible-effect approval.
- SatNav#0011 alpha 40/90: both images lack a map texture; alpha effect/restoration cannot be evaluated.
- GuiDebug#0015 MiniMap Visibility is a paired readback only, never a thirteenth behavior credit.

## Original failures and limits are retained

The raw log at lines 17087..17089 reads:

```text
b006: /Gui/Gui Custom Renderer/Sat Nav Render
TRUE
b006: /Gui/Gui Custom Renderer/Sat Nav Render
```

The case expected FALSE. All other 39 exact definition/value/end blocks match their original expectations. Final f006 at lines 49118..49120 reads FALSE, so the final state is not restoration of the actual initial b006 TRUE. This mismatch is neither hidden nor counted as aggregate PASS. The bounded SatNav decision above rests on its controlled on/off interval under override.

Ordinary gameplay HUD is visible at baseline and through the local MiniMap restoration, disappears by the speed-text phase, and stays absent in the final image. Its cause is unestablished. The final image removes the forced map patch, speed text and debug outlines; it is **not** restoration of the entire initial HUD. No takedown, driving, HUD completeness, status-count correctness, speed-data correctness, alpha, safe-area colour, newer-source active-wiring or full gameplay credit follows from this review.

Frames/readbacks are phase-adjacent, not proven same-frame. Every selected preceding-frame candidate has the pinned positive age 0.136..1.407 seconds; that supports the bounded phase comparisons and does not provide synchronization proof. Retained script hashes and helper steps tie the commands to these phases.

The original reporting path records the empty `--run-error` argument problem and undefined `terminal(args)` call. Its probe receipt still says `INCOMPLETE_EVIDENCE_RETAINED`, `evidence_archive_complete=false`, and 0 evidence files hashed by that original reporter. Those errors grant no archive/evidence-completion credit. This independent review uses the raw result/log/images and independently checked fingerprints; its own seal covers only its explicitly recorded inputs.

## Independent checks and integrity

- Original native result hash: `993aab5e54660b7b6a3fda423b49d773c5b8ddb8c34898b4429acabdc0d7a0d5`, verdict FAIL. Raw log SHA-256: `736f4da3d0434799e2911174fc7ce7ee9c5f5fb2f9adf5bc1d649a8e5c7ae7f0` (12,989,879 bytes). All 40 raw triplets were checked directly; 39 match, with b006 as the sole expectation mismatch. Raw asserts/exceptions are zero.
- There are 144 retained BMP frames. All 26 selected image hashes, original mtimes and 1280x720 dimensions match the pins; every selected image was viewed directly. All 26 retained generated-script hashes match. The helper log records all 24 operations, 26 notes and RESULT DONE.
- All 15 copied source files equal their exact 91a Git blobs. All five original exports match their original files. The packet integrity-file SHA-256 is `a05d1091866ecef88f4f113658122215fc4321584f40856090a5910c81d00fe0`; every listed frozen file matches.
- Independent current read-only checks match all 24 normal protected fingerprints, four private immutable fingerprints and 12 private payload hashes. These checks supplement the retained receipts and do not rerun the game.
- Only this new sibling review directory was written. Frozen evidence, source, production files, original aggregate, Git state and earlier source-review artifacts were not edited; no subagents or commits were used.

`REVIEWED_INPUTS.json` records complete hashes for every frozen packet file, all selected native frames, raw log, retained scripts, protected/private fingerprints and private payloads. Its SHA-256 is `f4f9408c3d3ce71b5508bbc7585018430436240eca22329b5a24e209d3088310`. `SITE_DISPOSITIONS.json` SHA-256 is `eb7618cf0ca20e9c4fd39a15729536f822ee1e6aa8ea7f9d06f8a140ece05a51`. `INTEGRITY.json` and `SHA256SUMS.txt` seal this report and both JSON files without a self-referential report hash.
