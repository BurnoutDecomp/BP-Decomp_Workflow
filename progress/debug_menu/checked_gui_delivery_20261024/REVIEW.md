# Checked GUI playable-package delivery review

VERDICT: pass

This passes the updated exact installer and the bounded publication/reconciliation plan below. The original rollback finding was corrected before any installation. The normal package and dev refs remain at their old baselines at this review's snapshot. This report authorizes no broader feature, debug-control, original preparation-pipeline or long-session claim.

## Reviewed scripts and finding resolution

| Input | SHA-256 | Disposition |
| --- | --- | --- |
| checked_gui_delivery_20261024/INSTALL.py | `4fe32bc03206e3b0207baaf0c44c20cd8d67dd3584736e4d755f0fbcb4744a69` | pass, corrected revision |
| promote_checked_gui_delivery_20261024.py | `667495dd7fa6068ada474bab014d3ecc64ade30800db40109198f325d0fddd4b` | pass, bounded post-install publication |
| checkpoint_renderer_gui_consumers_20261023.py | `0363fdc2dc7888935251423ffb1f4bbac74e5c0d51c08a007af9af8f596d069d` | imported helper inspected; its main is guarded |
| INSTALL.before_rollback_fix.py | `ec7b82d77c084767aeb625d3abf7f0a1a25cf62f1d505850ebdaee736c598b92` | original finding retained; not approved for execution |

F1, resolved: the original installer performed `os.replace` before recording the filename in changed. An interruption after replacement and before append could leave that payload outside the BaseException rollback list; the final fingerprint assertion would detect it but would not restore it. The updated installer journals the target before replacement (`INSTALL.py:64-65`). Rollback then compares every journaled target with its verified before image and restores changed fingerprints from backup (`:72-75`). If replacement failed without changing a locked target, the unchanged target does not need another copy. This closes the identified bookkeeping window. Both exact script versions are archived; no installer or failure-injection run was performed by this review.

The local `BINDINGS.json` beside this report contains all source/build pins, payload hashes, before-image fingerprints, script hashes and evidence paths. Exact reviewed inputs are retained under `inputs/`, and committed source-review/repair evidence under `workflow/`. The approval applies to these hashes, not to later script edits.

## Candidate, hosted build and byte attribution

- Candidate B5: `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee`.
- Candidate tree: `297ed7f50bc079f6f4c53360f626b295446dc8c2`.
- Hosted workflow: `c154d46d2280f653246147405e550e02fea1edc2`; its gitlink names that exact B5 commit.
- Hosted run: 40086048484, attempt 1.
- Executable: `4ebe1a82b1ee5bd30dbfdaa0262f2d59e1b6d581a5d35fc8de4d20aa4ccb907d`, 11355648 bytes.

The hosted input receipt is validated, exits0, records clean hosted source/workflow status and pins the same source/workflow. Its SHA matches verified_eleven_groups.json. The build log SHA also matches and directly reports 3002 shipping TUs: 4 compiled, 2998 cached, 0 failed, no compiler warnings/errors. All eleven named selected groups report pass in the input receipt, including the online-save-route and menu-music-wire groups. Expected negative-control failures remain distinct from candidate failures.

All 112 distinct source/build input pins were independently compared with the candidate B5 or exact workflow Git blobs. Each matches the recorded bytes/hash either directly or as the Windows CRLF checkout of the same Git content; there are no mismatches. No local compile, test or CI rerun was used.

All 12 hosted payloads independently match input-receipt.json sizes/SHA-256, the native staging receipt and the actual private staged files: exe, map, cgsmap, provenance JSON, seven FFmpeg DLLs and xaudio2_9redist.dll. The executable provenance identifies the same source/workflow and executable hash. This binds the installation inputs to the exact native-used package, not merely to a source branch or a successful fixture.

The candidate is a descendant of delivered B5 b3300e0e8e61dd7dea105a901a4fdb94464f3864, with exactly 32 changed files. The preparation branch 02c63ea7ed5dfb3b43dbaeb959a2d23f3861db6b is not an ancestor. All seven typed-game/queue/allocator preparation paths remain byte-identical to b330. GUI 172's CrashNavMapEvent source is also byte-identical to its held preimage; the proposed172 wrapper is excluded. The renderer's existing allocator-list Prepare definition is present but its complete method is unchanged from b330, SHA-256 `45dfe6ef49f87811d9a7e44ee7e892d14242c0b227f7f1a5dea93338be3267d8`; the new-module Construct seed is absent. Presence of that older definition must not be mistaken for activation of the isolated preparation work.

## Native evidence and its limits

The prelaunch runner, binding, staging and actual Case hashes match. The binding pins the exact native executable and all 12 staged payloads. The actual six harness-source hashes still match their staging pins. The prelaunch original_case_sha256 field refers to the prior GREEN reflection-fix Case wrapper, whose hash matches; the separately bound 621eeb12... baseline_boot_drive.original.ps1 is a different, also matching input. Those two hashes were not conflated.

The original terminal receipt retains the direct creation handle for owned PID 24152 / slot 62061, the expected private executable path and its start time. It reports completed/success, no first-assert stop or foreign game, and complete owned cleanup/input reset. The wrapper terminal receipt's hash binds that original terminal record. The completion receipt reports no remaining owned games and normal24 unchanged. The game was still alive at the 50.4-second harness limit and was stopped by the harness; this is not a natural self-exit claim.

The native log independently contains zero assert records and zero exception records. Its 142 motion samples include 104 samples after the teleport seat (indices 38..141). Direct coordinate calculation gives 236.5722 m path and 234.6558 m net displacement, agreeing with the reported 236.6 m / 234.7 m. Fifty-two samples record positive throttle; one GAMEWRECKED message is present. This is controlled movement after a named teleport, not an organic driving/race witness.

I independently viewed and rehashed both requested original BMPs:

| Frame | SHA-256 | Observed pixels |
| --- | --- | --- |
| bb_004500.bmp | `e797d12cc9648fa6cfbbdc5cb583e58c25360fe593cefbdbc221d0200322c2a7` | Road, industrial buildings, sky, roadside detail, player car and diagnostic overlays visibly rendered |
| bb_006900.bmp | `1228a4835d5ba8a1524c626d4ce71f104b65fae0df68cf32c2d9dbab47945ff4` | Tilted impact view with a damaged car, nearby wall/railings and rendered scene detail; not black |

Together with the named title/accept, junkyard-exit and final DRIVING records, these support the requested bounded startup/junkyard/scene/movement acceptance. The run used SkipIntro, teleport, throttle, muted audio and passive frame/log witnesses. It does not certify crash recovery, individual occlusion/debug controls, audible playback, complete online races or the whole game. New debug dispositions remain 0.

The workflow retains the earlier native RED and independent scoped reflection source fix; they were not rewritten into a pass. The later bound candidate evidence is separate. Existing Road Rage count/countdown, natural route save/overwrite and one-player host Leaving receipts remain in committed history. Their acceptance stays bounded to their original evidence; they were not rerun or expanded here. Cold saved-route loading still fails, and joined-peer departure, complete online races, Replay frame wiring and long-session audio remain unverified. GUI 143/337 module-input return delivery remains unclosed. Whole-registry debug SAVE retains its documented unnamed-DLC-slot crash and is excluded from recipes.

## Normal baseline and installer review

The current normal executable still hashes to `f31ed8609b339238251659b944735e88e4aa45abc7d2e440332ffd10fe76549e`; its provenance names source b3300e0e8e61dd7dea105a901a4fdb94464f3864. All 24 protected normal paths still match the prelaunch size, SHA-256 and exact Windows last-write timestamp. These comprise 12 payloads plus config.ini, BrnGame.log, BrnGame.emergency.log and nine Profile.sav files. The nine-profile roster also matches. An independent current CIM query returned zero matching game processes.

The exact corrected INSTALL.py has these concrete safeguards:

- Lines 24-35 require a fresh pass bound to the current installer/report hashes, verified hosted/native candidate identity, successful bounded native judgment, no remaining owned game and the exact 4ebe executable hash.
- Lines 37-44 recheck all 24 normal bytes/last-write timestamps and profile membership before writing; line 48 requires the exact old f31 executable. Lines 45-47 reject an observed running Burnout/BrnGame process.
- Lines 49-56 validate all 12 hosted input names/bytes/hashes, back up all 12 current normal payloads with copy2, verify every backup's full fingerprint and write a pending receipt before replacing anything. Unchanged DLLs are still backed up.
- Lines 59-65 use same-directory named temporary files, verify their candidate hashes, journal each target before os.replace, and place Burnout_PC.exe last. With the observed before images, four payloads differ; the eight runtime DLLs are unchanged and may be skipped after backup.
- Lines 66-76 verify all 12 final payloads, the 12 non-payload settings/log/profile fingerprints and the roster. A caught replacement/validation failure restores changed journaled targets and verifies every original payload against the complete before map before rethrowing.
- The final receipt records actual changed payloads, all before/candidate hashes, backup location, preserved settings/profile/log fingerprints, the existing behavior limits and dev_promotion=pending. No repository/index/ref operation exists in the installer, and it has no write path to the unknown source CON or parent WIP.

The review did not execute this script or simulate a filesystem failure. At the snapshot, receipt.json, pending.json, backup and FRESH_REVIEW.json do not yet exist in the delivery folder. Root must supply the fresh review binding and execute the exact reviewed revision; installation is not claimed by this pass.

## Bounded publication and shared-checkout reconciliation

The concrete promotion script and imported helper were read without importing/executing them. The helper's main is guarded; its used git/add/hash/JSON functions have the expected direct argument behavior. The promotion target base is 2b750a5208e215e3f0360f16b753788ffb8cbf3a on the private debug-consumers workflow branch. That base is a descendant of hosted workflow c154, retains the exact candidate gitlink and has identical hosted build-input files.

The current remote dev refs, physical heads and private refs match the script's explicit preconditions:

| Repository | Old remote dev / physical HEAD | Reviewed private target/base |
| --- | --- | --- |
| B5 | `b3300e0e8e61dd7dea105a901a4fdb94464f3864` | `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee` |
| Workflow | `cc54c12ebfaaadfc9b6cec42393b19355f05b595` | `2b750a5208e215e3f0360f16b753788ffb8cbf3a` |

Promotion lines 25-36 check those exact old refs/heads and ancestry, source tracked cleanliness with only `?? CON` allowed, an empty parent staging area and a successful installed delivery receipt bound to the actual normal executable. Lines 37-51 fingerprint unknown parent files plus progress/status.json, retain the volatility HEAD/status, require an unchanged volatility gitlink and make verified copies of existing tracked before images that the transition changes. The observed eight protected parent files do not collide with target tracked paths; progress/status.json is not changed by the transition. The 33 existing-file backup destinations are within the named publication folder and have maximum path length 202.

The metadata commit is built through an explicit temporary GIT_INDEX_FILE rooted at the reviewed private base. Only the receipt/review copies, publication hashes and owned README section are added; the normal parent staging area and unknown WIP are not folded into it. The candidate gitlink is checked again on the resulting commit. Published prose retains the cold-load/online/debug/preparation limits.

Lines 100-104 use non-force pushes. The source dev push is followed by the workflow's atomic private-branch/dev push, with the private local ref update using its expected old BASE. The two repositories are not a single atomic transaction; the receipt records successful steps separately. Lines 105-111 fast-forward both shared checkouts with submodule recursion disabled, recheck protected fingerprints, keep source status exactly `?? CON`, retain volatility HEAD/status and verify the final remote refs. This reconciles owned tracked changes while leaving the observed unrelated progress/status, volatility and untracked work present. No source CON write/delete or broad reset/clean/staging operation is proposed.

This approval is a read-only assessment of that bounded plan, not a claim that pushes or reconciliation have happened. Root remains responsible for executing it after the actual install receipt and handling any recorded partial publication state.

## Integrity and scope

All six earlier sealed review folders still match their complete seals, including the original source FAIL reports. This review wrote only its new report/binding/archive folder. It did not install, copy payloads into the normal game folder, build, compile, run tests/CI/game/input, import either action script, change Git refs/index/source, alter earlier evidence or publish anything. Read-only Git queries, process enumeration, hashes, static script inspection and the two requested image inspections were used.

No unclosed feature or debug-site status is promoted by this delivery verdict.
