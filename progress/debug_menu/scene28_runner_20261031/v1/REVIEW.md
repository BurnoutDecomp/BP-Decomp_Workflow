# Combined native Scene / Shadow / Director preparation review

VERDICT: fail

All 28 entries and all seven draft PowerShell files were reviewed. The packet is **not ready for its private native run**. Native runs performed: **0**; frames reviewed: **0**; site credit: **0**. Every target remains pending. This verdict concerns preparation and runner correctness, not 28 failed gameplay behaviors.

The evidence basis is B5 `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b`, workflow `a6e4457a6d09c4d321dc0c9b066dfd70fd0e6c7b`, and executable SHA-256 `39b62961b59261ac8e1b9894d5a69c8ab365bf7ea39e89793d654fcf93ca47da`. The exact reviewed input hashes are retained in REVIEW.json. No builds, launches, source/Git/profile changes or publication were performed; only these two review files were written.

## Actionable findings

### [P1] R1 — The case sets an invalid concurrency limit and is rejected before launch

Run.MaxConcurrentOtherGames is 0. The pinned run_case rejects limits outside 1..100, and flow_run has ValidateRange(1,100). No reviewed command-line override is supplied.

The stated runner exits with code 2 before Setup or native evidence capture.

Fix: For the intended zero-other-game policy, disable AllowConcurrentGames and remove the invalid 0 override while retaining strict ownership. If a different concurrency policy is intended, supply a valid reviewed limit and state that policy explicitly.

Evidence: [Case.ps1:30](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Case.ps1:30); `a6e4457a6d09:tools/tests/run_case.ps1:80`; `a6e4457a6d09:tools/diagnostics/flow_run.ps1:380`.

### [P1] R2 — Ten controls have context aliases that cannot resolve

Eleven context records use SC02=true, SC03=true or SH02=true as override.alias. Captured baseline keys and native aliases are SC02, SC03 and SH02. Get-PhaseCommands requires override.alias in baseline.Keys and constructs set commands from it literally.

The first SC03 positive phase throws missing captured context baseline SC02=true. Fixing only the membership check would emit an invalid alias and still break captured-value restoration.

Fix: Store plain alias names in context_overrides and retain the Boolean in value. Validate every context alias against the 30 declared aliases before any native setter, including the emergency restore map.

Evidence: [SCOPE.json:131](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/SCOPE.json:131); [SCOPE.json:401](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/SCOPE.json:401); [SCOPE.json:624](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/SCOPE.json:624); [Driver.ps1:52](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:52); [Driver.ps1:101](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:101).

### [P1] R3 — Numeric-only phase names collide across the three families

Get-PhaseName discards the qualified ID prefix. Duplicate suffix groups are 0002 SC02/SH02, 0003 SC03/SH03, 0004 SC04/SH04, 0006 SC06/SH06, and 0008 SC08/SH08/E08. The 84 target phases produce only 66 unique receipt names.

After the context records are corrected, SH02 attempts phase_0002_positive.cfg, which already belongs to SC02, and Execute refuses the overwrite before its setter. The complete batch cannot finish.

Fix: Use the unique alias or a filesystem-safe full ID in phase names, and check uniqueness of the complete planned command/frame receipt namespace before launch.

Evidence: [Driver.ps1:87](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:87); [Driver.Helpers.ps1:142](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.Helpers.ps1:142).

### [P1] R4 — The completion-event requester has no producer in the pinned harness

The requester opens Local\BurnoutPC_HarnessPhaseDone_<pid>_<slot>_<startTicks>. No supplied draft creates this event. The exact pinned a6e4457 flow_run/run_case helpers and tools tree contain no PhaseDone or BurnoutPC_HarnessPhaseDone producer; the pinned B5 source has none either.

With the declared helper binding, OpenExisting fails even after successful capture. Driver catch then saves status=fail over the success result, and the harness lacks the claimed early completion request.

Fix: Bind the actual compatible harness or wrapper that creates and polls this PID/slot/start-time event, include it in the review and hash pins, and use its exact stop contract. Preserve ownership checks and avoid a global input or process-stop substitute.

Evidence: [Request-HarnessPhaseDone.ps1:59](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Request-HarnessPhaseDone.ps1:59); [Driver.ps1:238](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:238); [Driver.ps1:242](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:242); [SOURCE_PINS.json:113](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/SOURCE_PINS.json:113).

### [P2] R5 — The reviewed Case.ps1 is not the Case.ps1 recorded in SOURCE_PINS

SOURCE_PINS records 174361320e6e2e25cf6c881b16bde846c88789612b07009823f5fac8398353cc for Case.ps1. The actual reviewed bytes hash to ec696287037e99d2dd3f80a129895c98e630bad5add3553d523651fdb7557021. The other seven copied helper hashes match.

The package cannot identify its actual reviewed runner through its own manifest.

Fix: After deliberate fixes, refresh the hash of the actual final Case.ps1 and any other changed packet files; preserve a review manifest for the final bytes and reject mismatches before launch.

Evidence: [SOURCE_PINS.json:148](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/SOURCE_PINS.json:148); [Case.ps1:1](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Case.ps1:1).

### [P2] R6 — Rounded Scene readbacks do not prove an exact same-run float baseline

Variant::ConvertToString renders floats with %.3f. Test-RestorableBaseline compares that rounded display to the source default, then restores the same display string. For example TriX=0.0004 displays 0.000, passes the default-0 check, and is restored to 0.0; scale 1.0004 and padding 0.3004 have the same defect. Published source also supports typed INI overrides, so fresh process construction alone does not establish the assumed exact value.

The driver can report terminal_restore_verified while changing the natural f32 bits. Unlike the clipping controls, the Scene floats have no exact baseline read.

Fix: Capture and verify actual f32 bits for these five fields, or establish an independently checked exact fresh-default provenance before mutation. Otherwise skip those fields without writing. A rounded default comparison alone must not authorize a write.

Evidence: [Driver.ps1:41](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:41); [Driver.ps1:185](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:185); [Driver.ps1:107](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:107); `3f4f9c06e1a6:src/GameShared/GameClasses/Development/DebugSystem/Core/UI/CgsTypes.cpp:132`; `3f4f9c06e1a6:src/GameShared/GameClasses/Development/DebugSystem/Core/UI/Variables/CgsVariableManager.cpp:52`.

### [P2] R7 — A NaN float readback bypasses the mutation and restore comparison

Read-Values does not parse or validate f32 values; it assigns an unused NaN variable. Execute accepts a parsed actual NaN because Abs(want-NaN) > tolerance is false, so its compound mismatch condition is false. The clip baseline display comparison has the same NaN comparison shape.

A finite requested value can receive a successful phase/restore receipt despite a non-finite native value string.

Fix: Require invariant-culture numeric parsing and IsFinite-equivalent checks on every f32 raw readback before comparison or baseline acceptance. Reject NaN and infinities explicitly; retain the independent exact-bit restore checks.

Evidence: [Driver.Helpers.ps1:122](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.Helpers.ps1:122); [Driver.Helpers.ps1:148](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.Helpers.ps1:148); [Driver.ps1:193](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/Driver.ps1:193).

### [P2] R8 — E14 has a known downstream implementation gap, beyond an unobserved jump scene

Published 3f MomentPlayerJumping checks jump-action, can-use-slomo and mbAllowJumpMoment, then calls PrepareCameras and asserts success. BehaviourCollection::Prepare calls PlayerJumpingTrap and returns false. The packet pins the common UpdateMoments/UpdateAllMoments handoff, but omits this known terminal consumer gap.

A genuine eligible E14 jump attempt can reach an existing PC trap/assert. A field P/N run cannot establish working jump-moment behavior on this source.

Fix: Pin the terminal jump consumer and record E14 as pending with a known implementation blocker. Keep its mutation-only evidence separate; do not attempt to award behavior credit until the filming closure is implemented and the relevant native scenario is witnessed.

Evidence: [RUNTIME_GATES.md:37](D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/native_scene_batch_20261031/RUNTIME_GATES.md:37); `3f4f9c06e1a6:src/GameSource/Director/MomentController/Moments/BrnMomentPlayerJumping.cpp:178`; `3f4f9c06e1a6:src/GameSource/Director/MomentController/Moments/BrnMomentPlayerJumping.cpp:480`.

## Verified preparation facts

- All 28 inventory IDs, captions and derived full paths match the pinned 1,355-entry published snapshot, and none has a verdict row. All 28 target aliases/triplets are unique; there are 30 aliases/paths including E17/E21 context. Director #0021/#0027 and Scene #0011/#0012 are correctly excluded as targets.
- All 15 selected source pins and 10 path-attestation pins match the 3f tree (some files occur in both maps). All 17 listed ARTIST witness hashes and the three original registration hashes match. Path construction from GetPath/GetName, MakeFullPath, registration and menu lookup is supported; ShadowMap is the literal root World/ShadowMap route.
- Executable, linker map, receipt, profile snapshot and read-only asset-roster hashes match. The roster has 5,622 records. The build receipt correctly identifies older workflow `38a0ec8384e9fb96a2b6df2497fc0a2f3f5eb00f`; this is not an a6 rebuild. The clip RVAs match the exact map symbols at 0xAB7E18/1C/20.
- All seven PowerShell files parse without errors. This is syntax evidence only. No STAGING.json exists; the fixture template is for future private slot 62190 staging. The review made no profile or asset copies.
- The preserved older Director result hash matches and reports zero eligible controls and zero site credit. It cannot be promoted into new-slot evidence.

## Values, contexts and capture limits

- N1: All eight f32 probes are finite, and the selected Source41/ARTIST registrations have the listed steps with no explicit SetRange. SC08 negative=0.0 is -1.2 increments from its source default 0.3 at step 0.25, so the blanket claim that every probe follows default-relative increments is false. An explicit typed SET can still accept 0.0; either document that route or choose a default-relative step value such as 0.05.
- N2: RUNTIME_GATES lists source conditions but Driver eligibility checks only baseline restorability. Case throttle input ends at 10 seconds, while Driver waits 12 seconds after its speed witness before setup. There are no phase-local jump/stunt/hard-stop/crash/boost attempts or camera-cycle/close-object/landmark gates. E43 explicitly has no pinned producer for bit 0x10000. Treat every missing producer, empty cache, absent shadow receiver or unobserved consumer as pending; no no-op or behavior credit follows from this run plan.
- N3: SC02 requires a false interval to seed the camera anchor. The draft captures an arbitrary natural Boolean baseline and does not require SC02=false before its first positive capture. Require that baseline or account for an explicit seed/restore phase before interpreting the first SC02 positive image.
- N4: The nominal budget is valid: 1 natural + 28*3 target + 1 terminal + 1 post-restore = 87, below 90. Capture-PhaseRaw rejects a 91st requested frame; Assert-NativeBatchFrame and Complete-NativeBatchCaptureAudit reject recorded overrun and enforce BMP size/hash checks. These are static checks, not evidence of any produced frame.

Valid E17/E21 context records use plain aliases, Boolean values and same-run baseline restoration in ordinary and emergency paths. The intended SC02/SC03/SH02 restoration has the same structure but is blocked by R2. Clip restoration uses same-run exact bits and bitwise checks; Scene restoration does not yet satisfy that standard (R6).

## Per-entry disposition

Every row below has a matching registration/path/raw triplet, but no native consumer witness from this batch. The source observation establishes where to look; it does not certify the live scene or output. Common runner blockers R1/R3/R4/R5 affect the complete batch.

| Alias / entry suffix | Control | Static consumer observation | Required live witness / pending reason | Credit |
|---|---|---|---|---:|
| SC01 / #0001 | Draw Collision Volumes | RenderWorld 0x828D04E8 -> DrawPrimitives; published source walks live volume instances. | Visible live collision volumes and emitted wire geometry. | 0 |
| SC02 / #0002 | Draw Triangle Test | RenderWorld byte +0x11 -> DrawTriangleTest 0x828C2E70; false branch stores the camera anchor. | A false seed interval, then visible swept sphere/triangle/contact geometry with stable pose. | 0 |
| SC03 / #0003 | Draw Padding | DrawTriangleTest byte +0x12 selects the cyan padding sphere. | SC02=true and visible additional padding sphere; repair context alias. | 0 |
| SC04 / #0004 | TriX | DrawTriangleTest reads TriX +0x30. | SC02=true, stable camera anchor and visible opposite x offsets; exact baseline required. | 0 |
| SC05 / #0005 | TriY | DrawTriangleTest reads TriY +0x34. | SC02=true, stable camera anchor and visible opposite y offsets; exact baseline required. | 0 |
| SC06 / #0006 | TriZ | DrawTriangleTest reads TriZ +0x38. | SC02=true, stable camera anchor and visible opposite z offsets; exact baseline required. | 0 |
| SC07 / #0007 | TriScale | DrawTriangleTest reads TriScale +0x40. | SC02=true, stable camera anchor and visible scale difference; exact baseline required. | 0 |
| SC08 / #0008 | Padding | DrawTriangleTest reads Padding +0x3c under Draw Padding. | SC02=true and SC03=true; visible sphere radius difference; exact baseline required. | 0 |
| SC09 / #0009 | Draw cached triangles | RenderWorld byte +0x54 -> DrawCachedObjectTriangles 0x828C2560. | Used TriangleCacheManager slot with valid visible Triangle4 lanes. | 0 |
| SC10 / #0010 | Draw cache spheres | RenderWorld byte +0x55 -> DrawCachedObjectSpheres 0x828C2B80. | Used cache slot with visible cached and inner sphere records. | 0 |
| SH02 / #0002 | Render Shadow map | GenerateFrustumQueries 0x827DADF8 and dispatch gate read shadow enable. | Update bit 0x80, live light/camera/shadow pass, and visible receiver. | 0 |
| SH03 / #0003 | Cast shadows from world | GenerateShadowMapDispatchLists 0x827C96D8 ANDs world shadow flag and world render switch. | SH02=true plus visible world caster/receiver in the cascade frustum. | 0 |
| SH04 / #0004 | Cast shadows from cars | GenerateShadowMapDispatchLists ANDs car shadow/render flags and near-only policy. | SH02=true plus active car caster and receiver in view. | 0 |
| SH06 / #0006 | Cast shadows from props | GenerateShadowMapDispatchLists ANDs prop shadow/render flags and near-only policy. | SH02=true plus live prop caster and receiver in view. | 0 |
| SH08 / #0008 | Render multiple shadow maps (CSM) | GenerateShadowMapDispatchLists chooses three cascades versus one. | SH02=true, same pose/light, visible near and distant caster/receiver witnesses. | 0 |
| E08 / #0008 | Draw follow-cam pivot | GameplayExternal::Update 0x82240828 reads +0xB5E before DrawBox/DrawLine. | Allocated active GameplayExternal behavior and visible pivot geometry. | 0 |
| E14 / #0014 | Allow Jump Moment | UpdateMoments 0x82250268 publishes allow flag; common controller updates moments. Terminal 3f jump path has a known PC filming trap. | Named eligible jump attempt, slomo eligibility, uninhibited moment and implemented filming closure. | 0 |
| E15 / #0015 | Allow Stunt Moment | UpdateMoments publishes allow-stunt; terminal published Stunt path reads MomentSharedInfo_GetStuntEnableFlag1317. | Named live stunt attempt during its selection window; common controller handoff alone is insufficient. | 0 |
| E16 / #0016 | Allow Hard Stop Moment | UpdateMoments publishes allow-hard-stop; terminal published HardStop path reads MomentSharedInfo_GetFlag1318. | Named live hard-stop attempt during its selection window; common controller handoff alone is insufficient. | 0 |
| E18 / #0018 | Enable Behaviour Debug Output | DebugPrinter::ActualPrint 0x821F71D8 tests mbEnabled before Draw2DTextJustified. | Actual behavior-printer text submission while enabled, and corresponding negative interval. | 0 |
| E19 / #0019 | Enable Moment Debug Output | ActualPrint plus UpdateAllMoments/ArbStateCrashing readers select moment text. | Actual active moment/crash printer output in the paired phase. | 0 |
| E22 / #0022 | Show debug camera names | DebugDisplayCurrentCamera 0x821F6740 uses (cycleNormal && showDebug) \|\| showAll. | E21=false and witnessed normal camera selector cycling; restore E21 baseline. | 0 |
| E23 / #0023 | Show World Map debug | MainDirector::Update 0x82274070 reads world-map byte and position journal size >1. | Available world map, at least two journal entries and visible map geometry. | 0 |
| E26 / #0026 | Show Crash Info | ArbStateCrashing::Update 0x8226BFB0 reads debug-active byte and invokes MomentSelector text rendering. | Crashing state window, E17=true and visible selector/crash text; restore E17 baseline. | 0 |
| E43 / #0043 | Small Near Clip | GetNearClipDistance/CopyToCgsCamera select small near only without custom near and with bit 0x10000. | Unresolved producer for bit 0x10000; no scene or behavior credit currently. | 0 |
| E44 / #0044 | Default Near Clip | GetNearClipDistance/CopyToCgsCamera select default near when custom/small alternatives are absent. | Stable close object, standard active camera, custom near absent and small-near bit clear. | 0 |
| E45 / #0045 | Default Far Clip | CopyToCgsCamera 0x8220AC48 loads default far before projection update. | Same stable camera pose and suitable distant landmark; moving road is insufficient. | 0 |
| E54 / #0054 | Enable Boost Effects | GameplayExternal::Update reads +0xB5F for FOV offset and boost shake. | Active GameplayExternal behavior, nonzero speed and ordinary Boost input in paired comparable phases. | 0 |

The per-entry JSON also retains every full ID, original witness path/hash, probe value, source blob and applicable finding. Missing geometry, empty caches, missing caster/receiver data, inactive Director state or an unobserved consumer must stay pending. None is an original-no-op disposition.

Required before a future run: correct the runner contract and context/phase defects, establish exact restores, update final-byte pins, and explicitly scope any remaining field-only probes. A behavior verdict still requires actual native logs and inspected pixels under the listed producer/scene gates.
