# Runtime gates and unresolved producers

This is a source-derived gate map, not native behavior evidence. Every listed gap remains pending until the Root-run frames/logs show the producer and the target consumer together.

## Scene Manager

SceneManagerDebugComponent::RenderWorld at ARTIST 0x828D04E8 checks the stored flags before calling DrawPrimitives, DrawTriangleTest, DrawCachedObjectTriangles and DrawCachedObjectSpheres. The flags only select the draw path.

- SC01 Draw Collision Volumes: the active scene must contain live collision-volume instances in the visible camera frustum. Witness the emitted wire geometry. Zero pixels without a live volume is an unusable scene.
- SC02 Draw Triangle Test: `RenderWorld` stores the current camera anchor only on the triangle-test-off branch. Use the natural frame when SC02 starts false; when it starts true, the runner captures an explicit temporary false seed before the first positive frame. Compare the swept sphere and fixed triangle/contact geometry with the flag enabled at a stable pose.
- SC03 Draw Padding: DrawTriangleTest must be active; the byte at the original field selects the additional cyan sphere. The positive/negative pair uses SC02=true and restores SC02's captured baseline.
- SC04 TriX, SC05 TriY, SC06 TriZ, SC07 TriScale: DrawTriangleTest must be active. Witness the generated triangle coordinates/scale move in the same camera anchored scene. SC02 is a temporary true context.
- SC08 Padding: both SC02 and SC03 must be true for the cyan padding sphere radius to use the value. Both are restored after the row.
- SC09 Draw cached triangles: the camera scene must have a used TriangleCacheManager slot and a valid visible Triangle4 batch mask. The reader walks those records; empty cache data cannot prove a no-op.
- SC10 Draw cache spheres: the camera scene must have a used cache slot with a populated sphere record in view. Empty cache data is a producer gap, not a target failure.

The current exact Source41 component has no explicit SetRange on the selected fields. It sets steps to 0.025 for TriX/TriY/TriZ and 0.25 for TriScale/Padding. The values in SCOPE.json follow those increments. Source defaults are false, 0/0/0, scale 1 and padding 0.3.

## ShadowMap

The exact 3f WorldModule source shows GenerateFrustumQueries is selected by update-set bit 0x80. It calls CalculateShadowMapCameras only when ShadowMap::IsEnabled is true. GenerateShadowMapDispatchLists selects 3 cascades when the CSM flag is true and gates world/car/traffic/prop legs with the corresponding ShadowMap bool AND the separate render-switch byte. These game-wide render switches remain at baseline.

- SH02 Render Shadow map: require update bit 0x80, a key-light direction, the renderer shadow pass, and a visible receiver. If the pass or receiver is absent, record the upstream scene/render gate and keep pending.
- SH03 Cast shadows from world: require the world render switch and visible world caster/receiver in the shadow frustum.
- SH04 Cast shadows from cars: require the race-car render switch, an active car caster and a receiver.
- SH06 Cast shadows from props: require the prop render switch, a live prop caster and receiver.
- SH08 Render multiple shadow maps (CSM): the source chooses 3 dispatch cascades versus 1. A visual claim needs near and distant casters/receivers whose captured shadow result differs with the same camera/light.

The source defaults for these five booleans are true. The renderer's opaque/transparent world-list gates are separate producers. Do not change those upstream flags to make a target appear.

## Director

The old 15-row Director cohort was rebound to the current inventory and trimmed to 13 pending controls. Current verified #0021 and #0027 remain outside this batch.

E14 source trace: published B5 `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b`, `BrnMomentPlayerJumping.cpp` blob `d45b01607594efa4dc67959f6ccf250e8f5fb674`. `PlayerJumpingTrap` logs/asserts at lines 81-88; `BehaviourCollection::Prepare` invokes it and returns false at lines 181-190; `MomentPlayerJumping::Update` checks jump action, can-use-slomo and `mbAllowJumpMoment`, then calls `PrepareCameras` and asserts `lbPrepared` at lines 482-494. This is a known PC source blocker, not a no-op verdict. E14 stays pending; only field mutation may be recorded until its filming closure is implemented and a matching native scenario is witnessed.

- D0008 Draw follow-cam pivot: needs an allocated active GameplayExternal camera behavior; witness the pivot box/lines in camera-world pixels.
- E14 Allow Jump Moment: this is not merely an unobserved scene gate. Published B5 `3f4f9c06e1a694d491effd1cbe28407ce9df1d4b` `BrnMomentPlayerJumping.cpp` (blob `d45b01607594efa4dc67959f6ccf250e8f5fb674`) shows `Update` requires jump-action, can-use-slomo and `mbAllowJumpMoment`; `PrepareCameras` then reaches `BehaviourCollection::Prepare`, whose PC body logs a trap, asserts and returns false, followed by the caller's `CGS_ASSERT(lbPrepared)`. Keep E14 pending with a known implementation blocker; this batch may record field-only mutation but awards no jump-moment behavior credit and must not call it a no-op.
- E15/E16 Allow Stunt/Hard Stop Moment: require the matching live event attempt and its director moment selection window. Writes without a named attempt prove only field mutation.
- E18 Enable Behaviour Debug Output: require an actual behavior-printer message while the byte is enabled.
- E19 Enable Moment Debug Output: require an active moment/crash debug message during the P/N interval.
- E22 Show debug camera names: only consumed while the normal camera selector is cycling. E21 is a temporary false context so the already-verified all-camera-name flag does not mask this row; restore E21 exactly.
- E23 Show World Map debug: needs an available world map and at least two live vehicle-position journal entries from driving.
- E26 Show Crash Info: requires the crashing-state update window. E17 is temporarily true because the original crash printer uses the default debug printer; restore its captured value. No crash-state window means raw mutation only.
- E43 Small Near Clip: consumer requires no custom near distance and camera state bit 0x10000. The source consumer is known, but no producer/scene that sets this bit is pinned yet; this is an explicit unresolved producer gap.
- E44 Default Near Clip: use a standard external camera with custom near absent and the small-near bit clear; capture the same close object.
- E45 Default Far Clip: use the same stable camera pose with a distant landmark. Prior moving-road frames did not isolate the far-clip consumer.
- E54 Enable Boost Effects: needs nonzero speed, active GameplayExternal camera behavior and ordinary Boost input. Compare the same pose with byte true/false.

The debug text/immediate-render subsystem and its visible font/buffer path must also be present when a text/axis witness is required. All source gates remain hypotheses for the live run until captured in the exact installed executable.
