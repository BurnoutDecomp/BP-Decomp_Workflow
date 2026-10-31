# Control matrix

All entries are pending in the published snapshot. Values are the source-cohort positive and negative probes. Restore always uses the captured same-run baseline. The driver credits no site; live effects stay pending until inspected.

## Scene Manager

| ID | Alias | Control | Lookup path | Default | P | N | UI step | Consumer gate |
|---|---|---|---|---:|---:|---:|---:|---|
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0001 | SC01 | Draw Collision Volumes | Scene manager/Draw Collision Volumes | False | True | False | bool | Require visible live collision volumes; no pixels without data is not a no-op. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0002 | SC02 | Draw Triangle Test | Scene manager/Draw Triangle Test | False | True | False | bool | Use a natural false frame as the camera-anchor seed; if the same-run baseline is true, add an explicit false seed frame before P/N. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0003 | SC03 | Draw Padding | Scene manager/Draw Padding | False | True | False | bool | Force SC02=true for P/N and restore SC02 baseline. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0004 | SC04 | TriX | Scene manager/TriX | 0.0 | 0.5 | -0.5 | 0.025 | Force SC02=true; compare opposite x offsets. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0005 | SC05 | TriY | Scene manager/TriY | 0.0 | 0.5 | -0.5 | 0.025 | Force SC02=true; compare opposite y offsets. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0006 | SC06 | TriZ | Scene manager/TriZ | 0.0 | 0.5 | -0.5 | 0.025 | Force SC02=true; compare opposite z offsets. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0007 | SC07 | TriScale | Scene manager/TriScale | 1.0 | 1.5 | 0.5 | 0.25 | Force SC02=true; compare 0.5 and 1.5 scales. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0008 | SC08 | Padding | Scene manager/Padding | 0.3 | 0.8 | 0.05 | 0.25 | Force SC02 and SC03 true for P/N; negative is one source step below 0.3; restore both baselines. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0009 | SC09 | Draw cached triangles | Scene manager/Draw cached triangles | False | True | False | bool | Require a used cache slot with a valid visible triangle batch; otherwise change scene, do not claim no-op. |
| CgsSceneManager::SceneManagerDebugComponent::OnActivate#0010 | SC10 | Draw cache spheres | Scene manager/Draw cache spheres | False | True | False | bool | Require a used slot with a visible populated sphere record; otherwise change scene, do not claim no-op. |

## ShadowMap

| ID | Alias | Control | Lookup path | Default | P | N | UI step | Consumer gate |
|---|---|---|---|---:|---:|---:|---:|---|
| BrnWorld::ShadowMap::Construct#0002 | SH02 | Render Shadow map | World/ShadowMap/Render Shadow map | True | True | False | bool | Require upstream shadow-map and world rendering gates plus a visible shadow receiver. |
| BrnWorld::ShadowMap::Construct#0003 | SH03 | Cast shadows from world | World/ShadowMap/Cast shadows from world | True | True | False | bool | Force SH02=true; require upstream Render world and visible world caster/receiver. |
| BrnWorld::ShadowMap::Construct#0004 | SH04 | Cast shadows from cars | World/ShadowMap/Cast shadows from cars | True | True | False | bool | Force SH02=true; require upstream Render race cars and a visible car caster/receiver. |
| BrnWorld::ShadowMap::Construct#0006 | SH06 | Cast shadows from props | World/ShadowMap/Cast shadows from props | True | True | False | bool | Force SH02=true; require upstream Render props and visible prop caster/receiver. |
| BrnWorld::ShadowMap::Construct#0008 | SH08 | Render multiple shadow maps (CSM) | World/ShadowMap/Render multiple shadow maps (CSM) | True | True | False | bool | Force SH02=true; require visible near and distant caster/receiver witnesses. |

## Director remaining pending

| ID | Alias | Control | Lookup path | Default | P | N | UI step | Consumer gate |
|---|---|---|---|---:|---:|---:|---:|---|
| BrnDirector::DebugComponent::OnActivate#0008 | E08 | Draw follow-cam pivot | Camera/Draw follow-cam pivot | False | True | False | bool | GameplayExternal camera behaviour must be allocated and active; capture the camera-world ROI while following the player. |
| BrnDirector::DebugComponent::OnActivate#0014 | E14 | Allow Jump Moment | Camera/Moment Options/Allow Jump Moment | False | True | False | bool | Field mutation only. Published B5 has a known PC trap in the eligible jump filming closure; behavior remains pending until that source defect is fixed and a named jump attempt is witnessed. |
| BrnDirector::DebugComponent::OnActivate#0015 | E15 | Allow Stunt Moment | Camera/Moment Options/Allow Stunt Moment | True | True | False | bool | Require a named stunt moment attempt under the same driving setup; raw writes alone prove only registration/readback. |
| BrnDirector::DebugComponent::OnActivate#0016 | E16 | Allow Hard Stop Moment | Camera/Moment Options/Allow Hard Stop Moment | True | True | False | bool | Require a named hard-stop moment attempt under the same driving setup; raw writes alone prove only registration/readback. |
| BrnDirector::DebugComponent::OnActivate#0018 | E18 | Enable Behaviour Debug Output | Camera/Debug Ouput/Enable Behaviour Debug Output | True | True | False | bool | Require at least one behavior-printer message in the phase; the V6 screenshots did not isolate this writer effect. |
| BrnDirector::DebugComponent::OnActivate#0019 | E19 | Enable Moment Debug Output | Camera/Debug Ouput/Enable Moment Debug Output | True | True | False | bool | Require an active moment/crash debug message; pair this site with the moment trigger context, then restore TRUE. |
| BrnDirector::DebugComponent::OnActivate#0022 | E22 | Show debug camera names | Camera/Debug Ouput/Show debug camera names | True | True | False | bool | The consumer is conditional on mbCycleNormalCamSelector; do not claim a visible effect unless the cycle state is witnessed. |
| BrnDirector::DebugComponent::OnActivate#0023 | E23 | Show World Map debug | Camera/Debug Ouput/Show World Map debug | False | True | False | bool | Use a moving DRIVING scene with at least two position-journal entries and an available world map. |
| BrnDirector::DebugComponent::OnActivate#0026 | E26 | Show Crash Info | Camera/Debug Ouput/Show Crash Info | False | True | False | bool | Require the crash state update window; if no crash state is active, raw value passes only and no visual-effect claim. |
| BrnDirector::DebugComponent::OnActivate#0043 | E43 | Small Near Clip | Camera/Clipping/Small Near Clip | 0.1 | 0.5 | 0.05 | 0.01 | Require a camera with state bit 0x10000 set and no custom near distance; otherwise this value is not the active near reader. |
| BrnDirector::DebugComponent::OnActivate#0044 | E44 | Default Near Clip | Camera/Clipping/Default Near Clip | 0.15 | 2.0 | 0.15 | 0.01 | Use the standard external camera with no custom near value and small-near state bit clear; include a stable close object for the clipping ROI. |
| BrnDirector::DebugComponent::OnActivate#0045 | E45 | Default Far Clip | Camera/Clipping/Default Far Clip | 10000.0 | 500.0 | 10000.0 | 100.0 | Use the same stable distant world landmark and camera pose; V6 moving-road frames did not isolate this far-clip consumer. |
| BrnDirector::DebugComponent::OnActivate#0054 | E54 | Enable Boost Effects | Camera/Enable Boost Effects | True | True | False | bool | Require non-zero speed and ordinary Boost input for a consumer witness; compare the same road/pose with the byte enabled and disabled. |

## Temporary context aliases

The SC02, SC03 and SH02 override records use plain aliases with the Boolean in `value` (for example `{ "alias": "SC02", "value": true }`). The driver validates every name against the captured 30-alias set before any setter and validates emergency restore keys through the same set.

## V2 float and runner policy

Source default, positive and negative f32 values carry exact IEEE-754 single bit patterns in `SCOPE.json`. Scene f32 targets may run only when the complete private log has no matching `[debug-ini] applied` or `rejected` row, the natural display equals the source default at the renderer's three decimal places, and the source constructor default bits match the pin. The typed source default string is then the restore baseline; a rounded value is never used as the baseline. E43/E44/E45 read and restore exact same-run bits from the retained owned-process handle. Missing proof means pending and no write.

All raw reads and requested f32 values must parse as finite invariant-culture singles. Phase receipts use family-qualified names such as `scene_SC04_positive`, `shadow_SH03_negative`, and `director_E14_restore`. The maximum plan is 88 frames including the optional SC02 false anchor seed, terminal restore and post-restore frame; the cap is 90 at 1280x720, with a 3,686,454-byte per-BMP ceiling.

E14 stays in the batch as a field test with zero behavior credit. The source blocker is pinned in `SOURCE_PINS.json` and described in `RUNTIME_GATES.md`; this runner does not classify the trap as an original no-op.

| Alias | Path | Why | Restore |
|---|---|---|---|
| E17 | /Camera/Debug Ouput/Enable Default Debug Output | temporary to isolate selected consumer | captured baseline |
| E21 | /Camera/Debug Ouput/Show all camera names | temporary to isolate selected consumer | captured baseline |

Temporary target contexts are listed on each SCOPE.json row. They are restored after that target and in terminal cleanup.
