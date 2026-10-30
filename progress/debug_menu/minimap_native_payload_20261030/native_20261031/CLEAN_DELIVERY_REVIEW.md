# Clean native and delivery review

CLEAN_NATIVE_STARTUP_PROFILE_DRIVING_VERDICT: PASS.
MATCHING_INSTALL_SCOPE_VERDICT: PASS.
FINAL_INSTALL_GUARD_VERDICT: PASS, inputs frozen and verified; installation not performed by this reviewer.
PRIOR_DIAGNOSTIC_CAPTURE_TIMING_VERDICT: FAIL, unchanged.
FULL_MINIMAP_VISUAL_REPAIR_VERDICT: UNVERIFIED, unchanged.

No material defect was found in this bounded follow-up. The exact clean artifact has now completed the private startup/current-save/driving regression. The concrete installer is restricted to that tested artifact and its matching sidecars, with exact backups and drift checks. This does not certify complete debug-menu parity, the original brief minimap visual failure, or a post-install normal-profile launch.

## Exact clean native result

Reviewed clean manifest: `397a485bffd532bce9de7544aad56452bfa9db1fae68eb2c1550107f1b7abf6b`. I verified all 12 clean runner file hashes, external input hashes and retained result bindings. PrepareClean.py:13–53 derives this separate run from the reviewed pair; Case.ps1 enables only five frame requests, with no SatNav event witness flag. The new capture schedule targets two seconds and stops after a bounded 20-second post-stream window. It is a separate coarse regression, not a replacement for the original failed dense capture experiment.

Actual run: `D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/minimap_regression_20261030/native_clean_62188/runs/fixed_62188_f055af4fd49241aa823a301322926a8c`, slot 62188, owned PID 22552. GAME_RUN_STARTED.json, STAGING.json, the staged EXE hash, its provenance sidecar, clean build receipt and CLEAN_NATIVE_VERIFICATION.json agree on:

- EXE `39b62961b59261ac8e1b9894d5a69c8ab365bf7ea39e89793d654fcf93ca47da`.
- B5 `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b`, workflow `38a0ec8384e9fb96a2b6df2497fc0a2f3f5eb00f`, both provenance dirty flags false.

The raw harness result has 12 passing checks, phase DRIVING, zero asserts and zero exceptions. I independently reran CurrentSaveProgress against the full raw log: actual nonnew signed-in profile, observed car XEURRB1, runtime rank 5/catalog 85, medals 202/events 120, spawn `D424EDF0A1220000`, copied save hash `18afe4cf21088ad174d853fc7f89ac4ed1e0ecceabfb42d3ed985fb0976d6e85`. I also reran Get-DriveSegment: 234.667099 m path, 233.566821 m net, samples 43–129, relocated baseline, no respawn in that segment; one gameplay wreck is reported. Wrecks are permitted by this inherited baseline and are not classified as exceptions.

Both normal pre/post payload maps and current normal hashes agree on all 15 payloads, config and ordinary save. The run used the private single-link save copy and recorded 5622 locked asset handles. Terminal-status hash, owner image/PID/start time and phase-stop event all bind; owned game/input/helper cleanup and private fixture restoration are complete. No process using the owned clean image remained at review. The controlled stop occurred 20.552825 seconds after streaming. This is owned harness cleanup evidence, not natural game-exit-code evidence.

I verified all five BMP hashes, actual dimensions, file/ACK bindings, owner/request sequence, monotonic presentation IDs and unique ACKs after their log cursors. The raw log hash is `05a9748244487f1a8a9f418589dd2bfbed9395cb6f93cfc6c7917cd0daa35ba8`; it contains no SatNav event-witness records. Actual request gaps are 2.425532, 1.879684, 1.825221 and 2.307547 seconds. I verified and viewed the retained `native_observations/clean_all5.png`: four driving/HUD/minimap observations, followed by a wreck-camera observation. Those sparse samples do not establish that a subsecond display jump is absent.

The result.json fields b5_head=e3d773c6c, b5_dirty=4 and parent_head=1897884e8 observe the separate shared checkout. They are not the actual artifact identity; the full EXE hash and clean build sidecar bind the tested 3f binary. The inherited Bug text about bank66/Flapt allocator capacity is a baseline label, not this test's purpose or a claim that this work fixed another allocator issue. Canonical delivery must retain that explanation and leave the raw result unchanged.

## Concrete installation scope and guard

Plan `delivery/NORMAL_INSTALL_PLAN.json` SHA-256: `477d46287982f56d7b6ef2a021119599493ed95e461f37214c44d32ebc4f00ec`.

Final execution manifest `delivery/MANIFEST.json` SHA-256: `18cfca242f813d56237c5eb4965664d6dd969b79a0e281bacab9772cefaa9902`. It now exists and pins the unchanged installer, test, plan, backup/archive receipts, plus exact copies of the clean native verification and prior native-data review. I verified every pinned hash and both evidence copies against their originals and the plan's evidence hashes. The installer requires this execution-manifest hash, not the plan hash, and checks all pinned files before mutation (Install.py:59–65).

I ran the actual read-only Install.validate against the concrete normal/candidate/backup/workspace paths. All 15 candidate and old normal payloads, their exact independent backups, the 21 protected saves/configs/logs and five shared WIP hashes match. Only three files differ, installed in this order: Burnout_PC.exe.provenance.json, Burnout_PC.map, then Burnout_PC.exe. The cgsmap and 11 other dependencies are already identical. The installed EXE will therefore be the exact clean native-tested binary; it is not either diagnostic EXE.

I independently confirmed that Install.py differs from the Source45 installer only in its description and unique temporary filename suffix, and that Test-Install.py is byte-identical. I ran all seven actual unit tests in transient fixtures inside this review directory: valid inventory, protected/candidate/backup/WIP drift, EXE-last ordering and the Windows exclusive-handle/hash path all pass.

The code rechecks processes, obtains an exclusive normal EXE handle, validates twice around uniquely staged/hash-verified siblings, releases the handle for the final EXE replacement, and postverifies payloads plus protected/WIP hashes (Install.py:67–89). It writes no save/config/log/asset content. The multi-file update is ordered rather than globally transactional: a failure preserves a partial-operation receipt and exact backups, with no automatic rollback or silent retry. This is explicit existing behavior, not an all-files-atomic guarantee. Live drift/capacity/process checks still apply when Root invokes the frozen installer.

No NORMAL_INSTALL_EXECUTION.json or NORMAL_INSTALL_FAILURE.json existed at review; the normal EXE was still the old E063 payload. This review does not report installation or a post-install launch as completed.

## Retained pair evidence

I verified the complete archive SHA-256 `f6917fb0f8540fb65eee7534ab1c19ee434eadc04a7b29360367024e8784fdcc` at `D:/Reverse/BP-Decomp_Evidence/debug_menu/minimap_native_pair_20261031/originals.zip`, its 91,630,272-byte size, exact 98-member roster, and every uncompressed member's size/SHA-256 against NATIVE_PAIR_ARCHIVE.json. It includes all 48 original pair BMPs and the bound logs/manifests/reviews. No extraction or deletion was needed.

The prior source/native-data PASS, original diagnostic capture timing FAIL and full visual repair UNVERIFIED remain separate and unchanged. This follow-up does not audit the unrelated historical-frame cleanup campaign. No source edit, game launch, normal installation, publication, checker change or cleanup action was performed by this reviewer.
