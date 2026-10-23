# Independent retained-native review: 62050

Exactly seven candidate sites reviewed: **one pass, six insufficient, zero fail**. These are proposed per-site dispositions; no inventory was changed. This is not an aggregate visual/gameplay pass.

The original raw case remains **PASS** (all 12 checks); the original wrapper remains **INCOMPLETE_EVIDENCE_RETAINED**, exit **1**, with an incomplete archive caused by `unexpected frame file: frames.csv`. Neither original status is rewritten or treated as the other.

## Per-site dispositions

| Site | Disposition | Evidence and limit |
|---|---|---|
| GuiCustRendererDebugComponent::OnActivate#0002 — override | **insufficient** | The controlled hidden branch removes the map texture while labels/icons/boost remain. The intended forcing-visible phase instead lacks the map and the remaining gameplay HUD; neither returns in later selected images. Positive visibility/restoration is not established, and the cause of the additional HUD loss is unestablished. |
| SatNavDebugComponent::OnActivate#0006 — outline | **pass** | Actual blue outline is absent before, visible after TRUE, absent after FALSE and at final state. Exact aliases and original packed-colour/source contract agree. Pass is limited to outline visibility, original blue colour and local outline-off restoration; it grants no map/alpha/HUD credit. |
| SatNavDebugComponent::OnActivate#0007 — top-left X | **insufficient** | Alias changes/restores and outline left edge moves/restores; actual map texture is absent throughout the pair. No map-geometry disposition. |
| SatNavDebugComponent::OnActivate#0008 — top-left Y | **insufficient** | Alias changes/restores and outline top edge moves/restores; no map texture. |
| SatNavDebugComponent::OnActivate#0009 — bottom-right X | **insufficient** | Alias changes/restores and outline right edge moves/restores; no map texture. |
| SatNavDebugComponent::OnActivate#0010 — bottom-right Y | **insufficient** | Alias changes/restores and outline bottom edge moves/restores; no map texture. |
| SatNavDebugComponent::OnActivate#0011 — alpha | **insufficient** | 0/100/40/90 readbacks complete, but no map texture appears in any of the four images. The unchanged outline is a separate renderer witness and cannot establish map alpha or restoration. |

Manual Sat Nav Render #0003 and master Enable Custom Renderer #0005 are context-only and receive no new disposition. The final nine aliases return to their authored display values, but the final image does **not** restore the initial map or gameplay HUD. File/profile restoration and visual consumer restoration remain distinct.

## Direct inspection of all 22 phase images

I viewed each actual BMP directly with the image viewer, then independently verified its SHA-256, mtime and 1280x720/32-bit top-down BMP shape. Each selected frame precedes its helper note by 0.227195..1.673216 seconds, satisfying the 100 ms margin and 3-second maximum. Integer-timestamp recomputation agrees with the serialized candidate ages within one microsecond. Values and images are phase-adjacent, not proven same-frame. The remaining frames in the 154-frame run were not used to infer unseen transitions.

The table records direct observations. Blue bounds are inclusive pixels, independently corroborated by read-only byte inspection of the outlined region. They describe the **outline**, not map boundaries.

| Phase | Actual frame | Direct observation |
|---|---|---|
| baseline | bb_006480.bmp | Map road texture, icons/labels and boost HUD visible; outline absent. |
| override_off_ignores_false | bb_006720.bmp | Map texture and normal HUD remain visible despite manual FALSE. |
| override_on_forces_hidden | bb_007080.bmp | Map road texture absent; map icons/labels and boost HUD remain visible. |
| override_off_leaves_hidden | bb_007440.bmp | Map texture still absent; icons/labels/boost remain. |
| override_off_ignores_true | bb_007680.bmp | Manual TRUE does not return map texture while override is off; icons/labels/boost remain. |
| override_on_forces_visible | bb_008040.bmp | Map, icons/labels and boost HUD all absent. |
| outline_visible | bb_008280.bmp | Blue rectangle `(994,477)..(1193,625)`; map/HUD absent. |
| left_x_changed | bb_008640.bmp | Outline left edge moves to 920; other bounds unchanged; map/HUD absent. |
| left_x_restored | bb_008880.bmp | Outline returns to `(994,477)..(1193,625)`; map/HUD absent. |
| top_y_changed | bb_009240.bmp | Outline top moves to 445; other bounds unchanged; map/HUD absent. |
| top_y_restored | bb_009480.bmp | Original outline bounds return; map/HUD absent. |
| right_x_changed | bb_009720.bmp | Outline right moves to 1230; other bounds unchanged; map/HUD absent. |
| right_x_restored | bb_010080.bmp | Original outline bounds return; map/HUD absent. |
| bottom_y_changed | bb_010320.bmp | Outline bottom moves to 657; other bounds unchanged; map/HUD absent. |
| bottom_y_restored | bb_010680.bmp | Original outline bounds return; map/HUD absent. |
| alpha_0 | bb_010920.bmp | Original blue outline bounds; map/HUD absent. |
| alpha_100 | bb_011160.bmp | Original blue outline bounds; map/HUD absent. |
| alpha_40 | bb_011400.bmp | Original blue outline bounds; map/HUD absent. |
| alpha_90 | bb_011760.bmp | Original blue outline bounds; map/HUD absent. |
| outline_hidden | bb_012120.bmp | Outline absent again; map/HUD remain absent. |
| override_final_off | bb_012360.bmp | Outline, map and normal HUD absent. |
| final-restored | bb_012720.bmp | Outline remains absent; initial map/normal HUD have not returned. |

## Raw state, scripts and source binding

All 38 actual definition/value/closing-definition triples match their expected strings directly in the retained raw log, including all nine initial and final values. No assert or exception line occurs in that raw log. The helper log contains the nine initial successful baseline waits before the first F2 operation, all 20 operations in order, all 22 notes and RESULT DONE. Each of the 22 archived scripts matches both its generated manifest hash and the source-reviewed blueprint; the step-file hash matches. No candidate helper, reporter or other tool was executed for this review.

For the passed outline site, raw blocks are `b003 FALSE` at lines 17730..17732, `r005 TRUE` at 27203..27205, `r018 FALSE` at 43525..43527 and `f003 FALSE` at 46360..46362. The actual physical scripts target the registered `Gui/Sat Nav/SatNav: Show Sat Nav Rect outline` variable. Exact 8b source registers that bool and RenderHUD gates its draw on it, uses the live viewport and passes `0xFFFF0000` to DrawFrame. The independently approved packed-colour contract maps that original word to RGBA bytes `00 00 FF FF`, opaque blue; these actual native images show that blue. This new 8b observation does not retroactively change retained 91a's white-outline evidence or the old 62049 FAIL.

The executable/source identity is source `8b2940d40e76fd6a88a37615f6163a99c2d5e3b8`, hosted **39944677851**, workflow `15af0f3165aa0529dc35dec63212b12905644d75`, exe SHA-256 `95c120dc8b2f20123ec28d86873ba5e5bb5a4c2d3fdb7d922d51d927ea9e1cbd`. The execution copy's 82 frozen payloads still match proposal manifest `af72019996957a005d43910ad1ca68757a17a8279390e96fa2ce91b69d4f2838`; runtime Case.ps1 equals the approved Case.proposed.ps1. The local physical B5 HEAD in the case result is separately attributed and does not replace executable provenance.

## Raw case, wrapper and protection receipts

Original result.json records PASS, 12 successful checks, 0 asserts and flow exit 0. Flow terminal receipts report exact owned/helper cleanup, input reset and private-profile restoration. The watchdog records ordinary wrapper exit 1 after **194.375 s**, maximum working set **188,571,648 bytes**, no termination attempt and no guard trip. Its 240-second/512 MiB limits were not reached.

The original probe receipt and evidence-archive.json explicitly remain incomplete: zero evidence rows hashed, rejection of generated `frames/frames.csv`, `bounded_structural_smoke_complete=false`, `behavior_credit=false`. The CSV remains retained at 22,366 bytes with SHA-256 `757aaa6f01117d63dd11de8c10c162d68c03f6a293a161de0b1538c5464900e3`. This independent review hashes its own selected inputs; that does not repair or relabel the original archive. Raw XMA decoder warnings remain in stderr; no audio fidelity/stability claim is made.

The run's protected-after receipt has no bad paths and records hash-checked script cleanup. Root's retained before/after recheck records 24 normal and four private paths unchanged. Their bytes/hash/mtime records agree with the run's captured baselines; the 12 private payloads also match the source-reviewed pins and captured fingerprints. Those are protection receipts for this run, not proof of gameplay HUD restoration or a requirement that future user files stay equal to this historical snapshot.

Critical original hashes:

- result.json: `3abb6b1c8dfc2000ef772b0665d558e681ae8f1fd6682d56e08f5a664b5de9c4`
- probe_receipt.json: `971fbfb4e3a67030de57528edf318ac4eb8e50c037b53e19f7a96766f97aab69`
- watchdog receipt: `56b3aac9629514bcc4aaad6f8213b03ed78ab7ca2bf77226942ab889aa51c45d`
- raw-private-BrnGame.log: `2647508e41297c9a79fa45e7cddb7f2b3aa520659809025bce47b27371bd7710`

Only this new sealed sibling review was written. No game/harness/C++/fixture/CI/IDA or reviewed tool ran; no source, index, Git, original run/receipt/analysis or inventory was modified. There is no full-HUD/map restoration, map geometry/alpha, peer-race or unrelated-control credit. `SITE_DISPOSITIONS.json` provides the seven explicit records; `REVIEWED_INPUTS.json` binds all selected image observations and reviewed hashes. Root owns any publication decision.
