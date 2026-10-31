# Scene28 v2 combined fresh review

VERDICT: fail

The v2 runner is **not ready for native execution**. All **28 target controls remain pending**, with **zero site and behavior credit**. The nine scripts parse and the preparation-only preflight passes, but the documented execution path still has blocking defects.

**[R9, P1] The exact package manifest rejects the mandatory runtime stage and requested review artifacts.** Preflight enumerates every local package file except SOURCE_PINS.json/ALL_FILE_HASHES.sha256 for source pins, and every file except the manifest for the all-file set. STAGING.json is required in the same directory for Execute but is absent from both submitted name sets. REVIEW.md/REVIEW.json are also required alongside this packet and are absent from those sets. An in-memory set comparison confirms exactly these three additions are rejected. No runtime stage was created during review. The preparation-only preflight passes, but every documented staged execution fails its prelaunch preflight before game launch. These requested review files also make preparation preflight fail after review. Fix: Define the immutable authored-file set separately from STAGING.json, REVIEW outputs and run evidence. Validate the stage with an explicit runtime contract and preserve hashes of all immutable authored files. Do not solve this by blind manifest regeneration that absorbs arbitrary runtime files. See [Preflight.ps1](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031_v2/Preflight.ps1:54).

**[R10, P2] The optional true-baseline SC02 anchor seed breaks the first SC01 phase.** When captured SC02=TRUE, scene_triangle_anchor_seed sets SC02=FALSE and leaves it there. Controls are ordered SC01 then SC02. SC01 builds Expected from captured baselines, so it expects SC02=TRUE but sets only SC01. An isolated in-memory execution of the actual Apply-Target/Get-PhaseCommands functions reports: scene_SC01_positive expects SC02=TRUE but anchor seed left FALSE. No native calls or file writes were used in this simulation. The advertised optional branch aborts at the first target and enters emergency restore. The false-baseline/default branch is unaffected by this specific mismatch. Fix: Place the false seed immediately before SC02 positive, or restore SC02 to its captured baseline before unrelated phases while preserving evidence of the seeded anchor. Validate both natural TRUE and FALSE branches in memory. See [Driver.ps1](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031_v2/Driver.ps1:240).

**[R11, P2] Private-profile physical path validation occurs after the fixture move/copy.** The wrapper preflight checks lexical sibling names/profile equality and hashes only. It never calls the supplied no-reparse/private-profile guards. The bound run_case moves an existing Profile.sav and copies the fixture at lines 263-273, then invokes Setup at line 297. Only Setup subsequently calls Assert-BrnPrivateProfile. A Memcard_62190/data ancestor junction can therefore pass the first lexical checks and redirect that first move/copy before the guard rejects it. The later check sees the newly copied fixture rather than establishing the original target was private. The submitted runner cannot enforce its no-live-user-profile boundary before its first profile mutation. No actual redirected stage or profile mutation occurred in this review. Fix: Run the physical no-reparse/approved-private-root and existing-profile identity checks in the pre-invocation stage gate before run_case can move/copy any profile. Keep the under-lock Setup recheck, and preserve the private restore-on-owned-exit contract. See [Preflight.ps1](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031_v2/Preflight.ps1:199).

The original eight findings were reassessed against actual final bytes:

| Finding | Disposition | Evidence |
| --- | --- | --- |
| R1 | resolved_static | Case.ps1:30-32 disables concurrency and removes the invalid zero limit; the pinned private helper takes the existing-game refusal path. |
| R2 | resolved_static | Plain declared aliases plus Boolean context values are checked in Preflight and Driver; Commands-For validates restore keys. |
| R3 | resolved_static | Family/alias/state phase names are distinct. The static namespace has 89 phase names and 190 paths. |
| R4 | resolved_static | Actual retry03 helper pair and _checks/_box_lock hashes match. flow_run creates the PID/slot/start-ticks event, checks retained ownership before accepting it and cleans only its creation-handle process. Case requires the matching witness-hash request and terminal receipt. |
| R5 | resolved_for_preparation_bytes | All submitted v2 file hashes matched before review output was written. New R9 covers the incompatible launch/output manifest namespace. |
| R6 | resolved_static_subject_to_live_proof | Scene defaults are exact constructor f32 values. The driver requires the matching natural F3 display and no matching applied/rejected Debug.ini row in the complete prefix-validated private log, otherwise skips before any setter. Restore strings use round-trip source-default text. Clipping values use exact same-run four-byte reads and bitwise restore checks. |
| R7 | resolved_static | Every metadata/request/readback f32 is invariant-parsed and explicitly rejects NaN/infinity before comparison. Scene defaults and all eight f32 probes have matching finite bit pins. |
| R8 | documented_behavior_blocker_retained | E14 explicitly names the published 3f PC trap in BehaviourCollection::Prepare and caller assert. It remains pending with no jump-moment behavior credit. |

The finite float and exact-baseline repairs are accepted as static preparation: Scene f32 restoration uses pinned constructor bits only when the complete prefix-validated log proves no matching typed override; otherwise no setter is permitted. E43/E44/E45 retain same-run four-byte reads and bitwise restore checks. These mechanisms have no native verdict in this packet.

The exact retry03 helper pair creates and polls the PID/slot/start-time completion event, checks retained image identity, and cleans its retained creation-handle process. Its actual `_checks.ps1`/`_box_lock.ps1` dependencies are pinned. The historical a6 helper pair is not treated as compatible.

Frame budgeting is statically valid: **88 planned maximum / 90 hard cap**, including the optional seed and terminal captures; 1280x720 and 3,686,454 bytes maximum each. No native run, game build or frame review was performed for Scene28. The original v1 reviewed inputs are unchanged.

| Alias / ID suffix | Disposition | Required native evidence |
| --- | --- | --- |
| SC01 / #0001 | pending_no_native_evidence | Require visible live collision volumes; no pixels without data is not a no-op. |
| SC02 / #0002 | pending_no_native_evidence | Use the natural frame if baseline is false; otherwise capture an explicit false anchor-seed phase before the first positive. Keep the camera pose stable and require visible swept-sphere/triangle/contact geometry. |
| SC03 / #0003 | pending_no_native_evidence | Force SC02=true for P/N and restore SC02 baseline. |
| SC04 / #0004 | pending_no_native_evidence | Force SC02=true; compare opposite x offsets. |
| SC05 / #0005 | pending_no_native_evidence | Force SC02=true; compare opposite y offsets. |
| SC06 / #0006 | pending_no_native_evidence | Force SC02=true; compare opposite z offsets. |
| SC07 / #0007 | pending_no_native_evidence | Force SC02=true; compare 0.5 and 1.5 scales. |
| SC08 / #0008 | pending_no_native_evidence | Force SC02 and SC03 true for P/N; restore both baselines. |
| SC09 / #0009 | pending_no_native_evidence | Require a used cache slot with a valid visible triangle batch; otherwise change scene, do not claim no-op. |
| SC10 / #0010 | pending_no_native_evidence | Require a used slot with a visible populated sphere record; otherwise change scene, do not claim no-op. |
| SH02 / #0002 | pending_no_native_evidence | Require upstream shadow-map and world rendering gates plus a visible shadow receiver. |
| SH03 / #0003 | pending_no_native_evidence | Force SH02=true; require upstream Render world and visible world caster/receiver. |
| SH04 / #0004 | pending_no_native_evidence | Force SH02=true; require upstream Render race cars and a visible car caster/receiver. |
| SH06 / #0006 | pending_no_native_evidence | Force SH02=true; require upstream Render props and visible prop caster/receiver. |
| SH08 / #0008 | pending_no_native_evidence | Force SH02=true; require visible near and distant caster/receiver witnesses. |
| E08 / #0008 | pending_no_native_evidence | GameplayExternal camera behaviour must be allocated and active; capture the camera-world ROI while following the player. |
| E14 / #0014 | pending_known_pc_trap_field_only | Require a named player-jump moment attempt under the same driving setup; raw writes alone prove only registration/readback. |
| E15 / #0015 | pending_no_native_evidence | Require a named stunt moment attempt under the same driving setup; raw writes alone prove only registration/readback. |
| E16 / #0016 | pending_no_native_evidence | Require a named hard-stop moment attempt under the same driving setup; raw writes alone prove only registration/readback. |
| E18 / #0018 | pending_no_native_evidence | Require at least one behavior-printer message in the phase; the V6 screenshots did not isolate this writer effect. |
| E19 / #0019 | pending_no_native_evidence | Require an active moment/crash debug message; pair this site with the moment trigger context, then restore TRUE. |
| E22 / #0022 | pending_no_native_evidence | The consumer is conditional on mbCycleNormalCamSelector; do not claim a visible effect unless the cycle state is witnessed. |
| E23 / #0023 | pending_no_native_evidence | Use a moving DRIVING scene with at least two position-journal entries and an available world map. |
| E26 / #0026 | pending_no_native_evidence | Require the crash state update window; if no crash state is active, raw value passes only and no visual-effect claim. |
| E43 / #0043 | pending_no_native_evidence | Require a camera with state bit 0x10000 set and no custom near distance; otherwise this value is not the active near reader. |
| E44 / #0044 | pending_no_native_evidence | Use the standard external camera with no custom near value and small-near state bit clear; include a stable close object for the clipping ROI. |
| E45 / #0045 | pending_no_native_evidence | Use the same stable distant world landmark and camera pose; V6 moving-road frames did not isolate this far-clip consumer. |
| E54 / #0054 | pending_no_native_evidence | Require non-zero speed and ordinary Boost input for a consumer witness; compare the same road/pose with the byte enabled and disabled. |

The shared renderer/world WIP and later upstream/jump checkpoint were outside this review; all source conclusions use published 3f Git blobs. Per-site source/ARTIST references, the prior-repair matrix, checks and exact findings are recorded in [REVIEW.json](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031_v2/REVIEW.json).
