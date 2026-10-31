# Combined Scene / Shadow / Director runner repair packet

**Preparation status:** all eight reviewed runner findings are repaired in this v2 sibling. PowerShell AST syntax and the read-only preflight pass. This is not a native behavior verdict: no game was launched, no frames were captured or reviewed, and all 28 target rows remain pending with zero site credit.

The reviewed original at `scratch/DEBUG_MENU_1011/native_scene_batch_20261031/` was not edited. Its initial complete file hash set is preserved in `ORIGINAL_REVIEW_INPUT_HASHES.json` and is rechecked at delivery. The sole combined packet for this sibling is this file; v2 does not copy v1's `REVIEW.md` or `REVIEW.json`.

## Repair matrix

| Finding | Repair in v2 | Evidence |
|---|---|---|
| **R1 — invalid concurrency limit** | `Case.ps1` sets `AllowConcurrentGames = $false` and removes `MaxConcurrentOtherGames`. The private strict runner refuses an existing game and does not stop it. A future stage run uses only the private fixture profile. | `Case.ps1`; `SOURCE_PINS.json` pins `retry03/fixed/runtime/tools/tests/run_case.ps1` and `diagnostics/flow_run.ps1`. |
| **R2 — context aliases contain `=true`** | All context records now hold plain aliases and a separate Boolean `value`. The preflight and driver check every name against the 30 declared aliases before setters; `Commands-For` validates emergency restore keys against the same set. | `SCOPE.json`; `Preflight.ps1`; `Driver.ps1:Get-PhaseCommands`; `Driver.Helpers.ps1:Commands-For`. |
| **R3 — colliding numeric phase names** | Receipt names include family and alias, such as `scene_SC04_positive`, `shadow_SH03_negative`, and `director_E14_restore`. Preflight checks the complete phase, frame, and fixed-receipt path namespace before launch. | `Driver.ps1:Get-PhaseName`; `Preflight.ps1:unique_phase_namespace` and `complete_command_frame_receipt_namespace`. |
| **R4 — no HarnessPhaseDone producer** | `Invoke-PrivateCase.ps1` binds the owned retry03 private helper pair. Its `flow_run.ps1` creates `Local\BurnoutPC_HarnessPhaseDone_<pid>_<slot>_<startTicks>` under strict ownership and polls it with retained PID/image/start-time checks. The exact `_checks.ps1` and `_box_lock.ps1` dependencies are pinned. The case requires a matching phase-request receipt and successful flow terminal receipt. | `SOURCE_PINS.json` runner hashes and event contract; pinned `flow_run.ps1:2212-2215`, `2848-2854`, `3304-3324`; `Case.ps1` event receipt gate. The a6 main helper pair is recorded only as the historical rejected binding. |
| **R5 — stale Case.ps1 hash** | `SOURCE_PINS.json` pins the v2 runner files; `ALL_FILE_HASHES.sha256` hashes every v2 artifact file except itself, including the packet. | `SOURCE_PINS.json`; `ALL_FILE_HASHES.sha256`; this packet's final hash is in the delivery note. |
| **R6 — rounded Scene float baselines** | Source defaults carry exact f32 bits. Scene floats can be written only when their natural display matches the pinned default and the complete private log has no same-path `[debug-ini] applied` or `rejected` row. The restore text is generated from the exact typed source default, never from the rounded display. Missing proof skips the site without a write. E43/E44/E45 use exact same-run 4-byte reads and bitwise restore checks. | Published B5 3f pins: Scene constructor stores at `CgsSceneManagerDebugComponent.cpp:92,95-98`; Debug.ini logs at `DebugIni.h:72-78` and typed application at `CgsVariableManager.cpp:52-78`; pointer-float display is `%.3f` at `CgsTypes.cpp:147`. Runtime proof is in `Driver.Helpers.ps1:Get-ExactSceneDefaultProof` and `Driver.ps1` baseline capture. |
| **R7 — NaN/infinity readbacks pass comparison** | All f32 metadata and probes are statically checked as finite. Every raw f32 readback, requested value, and expected comparison uses invariant-culture finite-single parsing; non-finite values fail before baseline acceptance or comparison. | `Preflight.ps1:typed_f32_values`; `Driver.Helpers.ps1:ConvertTo-FiniteF32`, `Read-Values`, and `Execute`; `Capture.ps1`. |
| **R8 — E14 jump path has a PC trap** | E14 remains in the target set with an explicit `known_pc_trap_source_defect` disposition and zero behavior credit. It may produce field-only evidence; no no-op or jump behavior verdict is allowed until the filming closure is implemented and a matching native scenario is witnessed. | Published B5 `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b`, blob `d45b01607594efa4dc67959f6ccf250e8f5fb674`, `BrnMomentPlayerJumping.cpp`: trap helper lines 81-88; trapped `BehaviourCollection::Prepare` lines 181-190; eligibility branch and caller assert lines 482-494. See `RUNTIME_GATES.md` and E14's `SCOPE.json` blocker. |

## Additional corrected gates

- **SC08 step:** negative probe is `0.05`, exactly one 0.25 step below the 0.3 source default.
- **SC02 anchor:** the natural frame seeds the camera anchor when SC02 is already false. If its captured baseline is true, the runner captures an explicit false seed before target phases.
- **Frame bounds:** worst case is 88 frames: natural baseline, optional SC02 seed, 28 × positive/negative/restore, terminal restore, and post-restore readback. The hard cap is 90 and counts terminal frames. Each capture must be 1280×720 and at most 3,686,454 BMP bytes.
- **Site gaps:** the original per-site producer/scene conditions remain in `SCOPE.json` and `RUNTIME_GATES.md`. Empty triangle caches, absent shadow passes/receivers, E43's unknown `0x10000` producer, missing camera-cycle/world-map/crash/moment windows, and any other absent producer stay pending rather than becoming no-op claims.

## Fixture and data boundaries

The reference fixture is `native_gui_batch_20261031_retry03/fixed/profile_snapshot.sav`, SHA-256 `4e4526ed40c8fa57f1100503351c68285f9eba69421e4bdab1bb8ce63ec3a23c`. It is referenced, not copied. `STAGING.TEMPLATE.json` points to a future Root-created private slot 62190 stage; no actual `STAGING.json` exists. The normal-game progress log is retained only as an archived read-only representation witness. Its hash is not compared to a live game log, and the live profile is never locked, moved, restored, or written by this preparation.

No asset tree or binary is present in v2. The 5,622-row asset identity roster remains a read-only external reference. All 28 target rows remain `pending`, with `site_credit = 0` and `behavior_credit = 0`.

## Static verification

- PowerShell AST parser: **pass**, 9 `.ps1` files, zero parse errors. Scripts were parsed, not executed as runners.
- `Preflight.ps1`: **pass**, read-only preparation mode. It checked the full v2 file-hash pin set, the 28-target roster, 30 unique aliases, plain context aliases, 8 finite f32 probes and exact bit pins, SC08 step, 89 unique phase names, 190 unique command/frame/fixed receipt paths, 88-frame upper bound, 90-frame cap, helper/dependency hashes, fixture hash, E14 blocker, zero credits, text-only package, absent `STAGING.json`, and the complete all-file manifest.
- Native run and frame review: **not performed**. No build or production-source write occurred.

`ALL_FILE_HASHES.sha256` contains the final SHA-256 for each v2 file except the manifest itself. The manifest's SHA-256 is included in the delivery note so the packet can remain covered without a recursive self-hash.
