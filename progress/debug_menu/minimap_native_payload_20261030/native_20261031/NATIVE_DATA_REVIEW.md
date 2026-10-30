# Native post-run review

NATIVE_EVENT_DATA_VERDICT: PASS, bounded to the observed diagnostic runs.
PROFILE_NORMAL_SAFETY_AND_CLEANUP_VERDICT: PASS.
FRAME_ARTIFACT_INTEGRITY_VERDICT: PASS.
FROZEN_FRAME_TIMING_VERDICT: FAIL.
VISUAL_REPAIR_VERDICT: UNVERIFIED.
CLEAN_CANDIDATE_BUILD_VERDICT: PASS; clean native launch PENDING.

The fixed diagnostic build preserved every instrumented semantic field in 2,500 paired native sender/receiver records, while all 2,106 old-build pairs had tail corruption. This proves the bounded native data-preservation result despite the independent screenshot experiment failing. It does not convert the original pair result to PASS or establish that the recorded minimap display jump is repaired.

## Binding and unchanged acceptance

Reviewed runner manifest: `8eea2e64476a49c6d5014fe76a33657d156fa37ede0ca9887fefb271359e94cd`. Current freeze.collect() still exactly matches it, including unchanged checker/parser, source/build identities and normal files. PAIR_RUNS.json binds these exact directories under `D:/Reverse/BP-Decomp_Workflow/scratch/minimap_regression_20261030/native_pair/native_pair_runs`:

- Old: `old_62186_9b85afb564384da898fbe49d7f68bbc1`, slot 62186, owned PID 13188, diagnostic EXE `c93a63364a6f2eaf528027b59433ad7d1998af39f7fa3645b26f5648ae836bfb`.
- Fixed: `fixed_62187_5a2524d598e24460a4b61884a79e8279`, slot 62187, owned PID 37464, diagnostic EXE `a3c1dd5dbb6e7bc04c7c01e89811bab988f7ad11f94d73e9a08925d03fbaed52`.

I verified all 15 staged payload hashes on each side against the manifest and bound GAME_RUN_STARTED.json/STAGING.json source/executable identities. B5 bases remain e3d773c6 and 3f4f9c06. No diagnostic binary becomes a shipping artifact.

The original PAIR_RESULT.json remains `invalid_or_incomplete`, reason `dense interval outside bound`, visual_fix_proven=false. Its SHA-256 remains `dab38f0a7c6af522af351560eeb432b489c484e3005827925d085828c0f05055`. Calling the unmodified Postcheck.check independently on each retained run reproduces that failure. I did not edit or rerun its result-writing main, widen a threshold or replace this result.

## Native event preservation

I loaded the frozen v4 parser and parsed each complete raw log independently, with cap 20000 and original line endings. Both logs have contiguous sender/receiver sequences, complete FIFO pairing, no ambiguous/unmatched records, errors=[], and counts below the cap.

| Evidence | Old | Fixed |
| --- | ---: | ---: |
| Sender / receiver / paired records | 2106 / 2106 / 2106 | 2500 / 2500 / 2500 |
| Tail mismatches | 2106 | 0 |
| Pairs after StreamingFinished | 1726 | 2123 |
| Mismatches after StreamingFinished | 1726 | 0 |
| Raw log bytes | 3443061 | 3312035 |
| Post-stream motion samples | 158 | 159 |
| Bounded motion path, metres | 408.254 | 471.696 |
| Steering while moving / heading change | observed | observed |
| Assert / exception markers | none | none |

Old `flow/BrnGame.log` SHA-256: `c0296851da75a260ce78addb61ed81845788df1a114ca9c1ee53891a619885e3`; fixed: `b7ec0e03aca480c75ab2edf2ab144bcdf8ea46f45358a61bdbfd1f3d51f72fa3`.

The old trigger is independently matched to sender/receiver 874, raw log lines 9387/9388, after StreamingFinished line 5961. Its expected tail is `0000000000000000,00,01`; received is `411000004049ABEA,00,00`. Old native flags also contain noncanonical bytes such as FF/FF, EF, F6 and others in the pre-assignment snapshot, confirming actual queue-tail corruption rather than only a synthetic counterexample. Fixed raw log pairs from lines 1472/1474 through 19426/19427 preserve their exact prefix and tail; StreamingFinished is line 5384.

The scope is the formatter's named scalar/pointer/flag object representations, not C++ padding or rendered pixels. Native producer tails throughout both runs were route=null, rotate=00, trajectory=01; fixed preserved that tuple in all 2,500 records. Native toggling of those flags and a nonnull route texture were not exercised. The earlier queue test covers additional synthetic values. Position/orientation/speed and full-width map/mask pointers are checked within each run; pointer addresses are never compared between runs. Source/ABI fidelity remains supported by the original source review.

## Actual profile, normal files and ownership

I reran the actual CurrentSaveProgress function against each full raw log. Both pass with signed-in/nonnew, shared gameplay/progression profile, observed car `XEURRB1`, runtime rank 5/catalog 85, medals 202/events 120 and spawn ID `D424EDF0A1220000`. Both OnProfileLoaded witnesses are at raw log line 1246. The old one-profile witness is line 1147; fixed is line 1146. This is actual load evidence, not the prior normal log's earlier car epoch.

Both independent fixture files still have one filesystem link and the frozen save hash `18afe4cf21088ad174d853fc7f89ac4ed1e0ecceabfb42d3ed985fb0976d6e85`. PRIVATE_PROFILE_BINDING.json records the same single-link private copy at launch. The private stage save copies have been removed by the recorded fixture cleanup, as expected.

Both RUN_EXIT receipts record harness exit 0, locked_assets 5622, and unchanged normal save/config/all 15 payload hashes. I compared the actual maps against the manifest and rehashed current normal inputs through freeze.collect(). Normal EXE remains e0635b4d; normal config and profile remain their frozen hashes. No restore of the live normal save was performed by this runner.

Both flow-terminal receipts bind the exact terminal-status.json hash, owned image/PID/start identity and phase-stop event. Owned cleanup, input reset, helper cleanup and private profile restoration are complete; no foreign game was reported. The fixed receipt normalizes a trailing zero in one UTC fractional timestamp when embedding it; its referenced raw status hash and the UTC instant agree. A current process inventory found zero processes using either owned game image. These are successful controlled phase-stop/owned cleanup results; game_exit is null and game_exited_on_own=false, so they are not natural game-exit-code evidence.

## Frames and timing

All 48 retained BMPs pass their CAPTURES.json hashes, actual 1280x720 BMP dimensions, exact file/ACK binding, owner/PID/slot/request sequence and monotonic presentation identity checks. The log contains exactly one matching ACK after each recorded cursor. Frame integrity does not repair the timing failure.

| Frozen timing evidence | Old | Fixed |
| --- | ---: | ---: |
| Actual request-gap range, seconds | 0.627127â€“0.736511 | 0.644009â€“0.768772 |
| Allowed interval, seconds | 0.125â€“0.5 | 0.125â€“0.5 |
| First request after trigger, seconds | 0.043041 | 0.014989 |
| Phase stop after streaming, seconds | 38.456657 | 38.550594 |

Both first-request associations pass their original0â€“0.5second bound; the interval failure is independently confirmed on both sides. Original capture cadence targeted 0.25 seconds. No retrospective cadence relaxation is justified.

I visually inspected retained frame 13 on each side. Old `bb_006422.bmp` shows crash camera with no minimap, while fixed `bb_006568.bmp` shows the driving HUD/minimap. Thus matching input scripts and approximate trigger offsets did not produce matching visual states. Sparse post-trigger images also lack pre-trigger coverage and an event-used-by-renderer/presentation correlation. These frames cannot establish disappearance of the original brief map-region/orientation jump. The original full-visual-verification FAIL and pending visual closure stand.

## Clean candidate build

At `D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/minimap_regression_20261030/build_clean`, I verified all 15 artifact sizes/hashes, exact provenance equality with BUILD_RECEIPT.json, B5 `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b`, workflow `38a0ec8384e9fb96a2b6df2497fc0a2f3f5eb00f`, and both dirty flags=false. The EXE SHA-256 is `39b62961b59261ac8e1b9894d5a69c8ab365bf7ea39e89793d654fcf93ca47da`. Receipt hash: `bfa1c512b4b9585a7eb8564017e2739f11cb55fbcaac129a007d03eda3b606c1`.

The full shipping build linked successfully: three owning/stamp TUs recompiled, 3016 were up to date, zero failed, no warnings/errors. The temporary SatNav witness marker is absent from the EXE. This is a clean source build without the temporary event witness, not an assertion that every pre-existing engine diagnostic was removed. Its receipt says native_verification=pending. Neither diagnostic-run evidence nor a full link proves that this exact clean EXE has completed a native launch; that validation remains pending.

No source edit, game launch, publication, frame deletion or checker mutation was performed by this reviewer. Prior review outputs and the original pair failure are preserved. Review facts are limited to the retained artifacts and identities listed here.
