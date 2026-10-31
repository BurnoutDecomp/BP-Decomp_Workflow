VERDICT: fail

# Scene28 combined source/native review

Seven controls have bounded visible consumer evidence. Twenty-one remain insufficient or context-limited. The original native case result remains `FAIL`; this review does not change canonical verdicts or award machine site credit.

## Evidence integrity

- Candidate executable SHA-256: `39b62961b59261ac8e1b9894d5a69c8ab365bf7ea39e89793d654fcf93ca47da`; source B5 commit: `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b`.
- Source checks passed: 20 pinned B5 blobs, 11 path-attestation blobs, and 17 pinned ARTIST evidence artifacts; all hashes match their pins.
- The retained archive SHA-256 `c241c6e15355b0691c525bd1c08a707f2b598b7c305c3a057f708560cf708a8f` matches `ARCHIVE.json`. All 87 original 1280x720 BMPs match `CAPTURE_AUDIT.json` and the archived frame bytes; no hash or dimension mismatch.
- I checked 2580 alias/value/path log triplets across 86 phases, 84 target P/N/restore receipts, and 30 natural-baseline receipts. All match their full paths and typed values. All 28 target restore receipts and terminal restore pass.
- `driver-result.value_line` points to the first `alias: /path` echo; `ack_after` is the typed value line, followed by the repeated alias/path echo. I cross-checked the actual log triplets directly.
- Scene float baselines match the pinned constructor values and have no matching Debug.ini applied/rejected rows. E43/E44/E45 restore to exact bits `3DCCCCCD`, `3E19999A`, `461C4000` respectively.
- E18 and E19 differ from their source-default metadata: SCOPE says TRUE, but the captured natural baseline and same-run restore are FALSE. Their restore is judged against the captured FALSE baseline, not an assumed default.
- Independently rehashed all 15 normal build/game payload files and `config.ini`; all still match the pre-run values. The run receipt says no normal profile/config change or user-data write. The private staged profile was cleaned after collection, so its archived single-link/hash receipt cannot be rehashed now; no live profile was accessed during this review.

## Original case and stop-field reconciliation

- Original result: `verdict=FAIL`, `as_expected=false`, run exit `1`. Keep this FAIL unchanged.
- Root's collection receipt records: Case queried the wrong stop-event field; actual phase_collection_stop_requested=true.
- The actual phase-done request set `Local\BurnoutPC_HarnessPhaseDone_56108_62190_639290644275978168` for the owned process. `flow-terminal.json` records `phase_collection_stop_requested=true`, flow exit `0`, zero asserts, owned cleanup and input reset complete. Collection closed; the original case verdict remains FAIL.

## Per-control outcomes

P/N/R values are the actual typed readbacks. Full qualified IDs, exact readback paths, log line numbers, frame hashes and source/ARTIST addresses are in `REVIEW.json`. `SM` = SceneManager, `SH` = ShadowMap, `D` = Director. No insufficient entry is declared a no-op.

### SceneManager

| ID | Alias | P / N / same-run restore | Result | Evidence and limit |
|---|---|---|---|---|
| SM#0001 | SC01 | `TRUE / FALSE / FALSE` | **insufficient** | The field toggles and restores, but the positive BMP shows no attributable live collision-volume geometry. No volume producer is established; this is not a no-op disposition. |
| SM#0002 | SC02 | `TRUE / FALSE / FALSE` | **accepted** | A horizontal test edge is visible only in the positive BMP and is absent in the negative and captured-baseline restore BMPs. ARTIST RenderWorld calls DrawTriangleTest under this flag. Acceptance is limited to this visible edge; the full swept-sphere/contact set is not claimed. |
| SM#0003 | SC03 | `TRUE / FALSE / FALSE` | **accepted** | With SC02 held true, the positive BMP adds cyan padding geometry; the negative BMP removes it and restore returns SC02 to its captured baseline. Acceptance is limited to the visible padding draw. |
| SM#0004 | SC04 | `0.500 / -0.500 / 0.000` | **insufficient** | With the triangle test enabled in P/N, the visible edge has the same span in both images. The TriX values are attributed and typed, but no x-dependent consumer change is visible. |
| SM#0005 | SC05 | `0.500 / -0.500 / 0.000` | **insufficient** | With the triangle test enabled in P/N, no distinct y-dependent geometry change is visible. Typed field movement alone is insufficient. |
| SM#0006 | SC06 | `0.500 / -0.500 / 0.000` | **accepted** | With SC02 true in P/N, the visible test edge changes span between +0.5 and -0.5; restore removes the test draw by restoring SC02 to baseline. Acceptance is limited to this TriZ-dependent edge response. |
| SM#0007 | SC07 | `1.500 / 0.500 / 1.000` | **insufficient** | With SC02 true in P/N, the visible edge has the same span for scales 1.5 and 0.5. No scale-dependent consumer change is visible. |
| SM#0008 | SC08 | `0.800 / 0.050 / 0.300` | **accepted** | With SC02 and SC03 held true, the positive 0.8 value produces a visible cyan padding wire-sphere; the 0.05 negative and captured-baseline restore show no comparable large sphere. This accepts the visible radius effect only; the small-value view does not establish a no-op. |
| SM#0009 | SC09 | `TRUE / FALSE / FALSE` | **accepted** | The positive BMP contains a large translucent blue cached-triangle overlay; negative and restore do not. The pinned ARTIST reader walks used cache slots and draws valid triangle batches, so this run supplies a visible cache producer/consumer witness. |
| SM#0010 | SC10 | `TRUE / FALSE / FALSE` | **accepted** | The positive BMP shows cache wireframe geometry; negative and restore remove it. The pinned ARTIST reader walks populated sphere records and calls DrawHollowSphere, supplying a visible cache-sphere witness. |

### ShadowMap

| ID | Alias | P / N / same-run restore | Result | Evidence and limit |
|---|---|---|---|---|
| SH#0002 | SH02 | `TRUE / FALSE / TRUE` | **insufficient** | P/N values are read back, but no shadow-map pass/receiver delta is attributable. The required update-set, key-light and renderer gates remain unproved. |
| SH#0003 | SH03 | `TRUE / FALSE / TRUE` | **insufficient** | No changed world-caster shadow is visible, and the separate world-render/caster/receiver gates are not established. |
| SH#0004 | SH04 | `TRUE / FALSE / TRUE` | **insufficient** | A car is in view, but no changed car-caster shadow is visible and the shadow pass/caster/receiver chain is not established. |
| SH#0006 | SH06 | `TRUE / FALSE / TRUE` | **insufficient** | No changed prop-caster shadow is visible; a live prop caster/receiver through the shadow pass is not established. |
| SH#0008 | SH08 | `TRUE / FALSE / TRUE` | **insufficient** | No near/distant cascade difference is visible. The CSM value readback does not prove three-cascade output. |

### Director

| ID | Alias | P / N / same-run restore | Result | Evidence and limit |
|---|---|---|---|---|
| D#0008 | E08 | `TRUE / FALSE / FALSE` | **insufficient** | No follow-camera pivot box/line is visible, and an allocated active GameplayExternal consumer is not demonstrated. |
| D#0014 | E14 | `TRUE / FALSE / FALSE` | **insufficient** | Only the field is toggled. No real jump attempt is captured; the pinned 3f source reaches a PC BehaviourCollection::Prepare trap/assert if the eligible filming closure is entered. No no-op or current-dev jump-fix credit. |
| D#0015 | E15 | `TRUE / FALSE / TRUE` | **insufficient** | No named stunt-moment attempt or moment-selection window is witnessed; the readbacks are field-only. |
| D#0016 | E16 | `TRUE / FALSE / TRUE` | **insufficient** | No named hard-stop attempt is witnessed. The visible news overlay is unrelated to this flag. |
| D#0018 | E18 | `TRUE / FALSE / FALSE` | **insufficient** | The visible Paradise City News Flash is a standard update overlay present across P/N/R, not a behaviour-printer message. Natural baseline and restore are FALSE despite source_default TRUE. |
| D#0019 | E19 | `TRUE / FALSE / FALSE` | **accepted** | With E19 TRUE the positive BMP shows the moment-selector candidate/status diagnostic list; the FALSE negative and same-run FALSE restore show no such output. X360 ActualDebugRender calls DebugPrinter output. Acceptance is for the output gate only; the messages say conditions are not met and prove no successful moment. |
| D#0022 | E22 | `TRUE / FALSE / TRUE` | **insufficient** | No debug-camera names appear and the normal-camera selector cycling condition is not witnessed. E21 is a validated temporary context only. |
| D#0023 | E23 | `TRUE / FALSE / FALSE` | **insufficient** | The positive BMP has a lone green line, but no moving DRIVING positions, two-position journal or verified world-map producer is present. The line cannot be attributed as recovered world-map behavior. |
| D#0026 | E26 | `TRUE / FALSE / FALSE` | **insufficient** | No crash-info text is visible and no active ArbStateCrashing update window is established; a damaged-looking car alone is not a crash-state witness. |
| D#0043 | E43 | `0.500 / 0.050 / 0.100` | **insufficient** | Typed P/N and exact captured baseline bits are verified, but the required small-near state bit producer is unknown and no active near-clip effect is visible. |
| D#0044 | E44 | `2.000 / 0.150 / 0.150` | **insufficient** | P/N/restore values are typed and restored, but the standard external-camera/no-custom-near consumer and a stable clipping delta are not established. |
| D#0045 | E45 | `500.000 / 10000.000 / 10000.000` | **insufficient** | P/N/restore values are typed and restored, but the view has no controlled distant landmark and no far-clip change is visible. |
| D#0054 | E54 | `TRUE / FALSE / TRUE` | **insufficient** | P/N/restore values are read back, but the capture has zero vehicle velocity and no ordinary Boost input; no boost camera effect is witnessed. |

## Bounded acceptance set

- Accepted: `SC02`, `SC03`, `SC06`, `SC08`, `SC09`, `SC10`, `E19`.
- Insufficient: all remaining 21 controls; keep them pending for their scene/producer or consumer evidence.
- E14 remains pending: this run has no real jump attempt, and the pinned 3f source reaches the PC `BehaviourCollection::Prepare` trap/assert when the eligible filming closure is entered. The run used the older 3f executable; no current-dev jump-fix credit is inferred.
- E23 remains pending despite the isolated green line in its positive frame: moving positions, journal entries and the world-map producer are not established.
- E19 acceptance is limited to moment-selector diagnostic output. Its messages report unmet conditions; this does not prove a successful moment.

## Review metadata

- Machine `site_credit`: `0` (unchanged). Proposed review acceptance is not a canonical verdict update.
- `VERDICT: fail` because the cohort has 21 insufficient controls and the original case FAIL is retained.
