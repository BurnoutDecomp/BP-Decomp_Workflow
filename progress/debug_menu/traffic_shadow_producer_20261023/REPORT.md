# Traffic blobby-shadow `AddShadow` reachability

Status: isolated source-recovery proposal with exact pre/post files and diff. It grants no verified-site or runtime credit. No production source, inventory, Git state, or build output was changed.

The original `AddShadow` producer is reachable from the traffic main-view path. This corrects the earlier RaceCar-only scope: the two ARTIST `AddShadow` references are direct calls from RaceCar and traffic. RaceCar remains excluded in its ordinary main-view call (`r9 == 0`), and its shadow-map call is behind `mShadowMap.mbRenderingShadowMap == true`; traffic has a separate eligible main-view producer.

## Direct and virtual call coverage

The pinned ARTIST export for `BrnBlobbyShadowBuffer::AddShadow` at `0x823F7638` lists exactly two `xrefs_to`: `RaceCarEntityModule::GenerateDispatchLists` at `0x822E79F8` and `TrafficEntityModule::RenderTrafficCar` at `0x82728B08`. Their call instructions are direct `bl` sites at `0x822E8040` and `0x82729554`, respectively.

`TrafficEntityModule::RenderTrafficCar` has one ARTIST `xrefs_to`, `TrafficEntityModule::GenerateDispatchLists` at `0x8273B280`. Its assembly calls `RenderTrafficCar` directly at `0x8273B53C`. `GenerateDispatchLists` has two ARTIST `xrefs_to`: `WorldModule::GenerateDispatchLists` at `0x827D1CE8` and `WorldModule::GenerateShadowMapDispatchLists` at `0x827C96D8`; both are direct call sites. The DecFIGS declarations list `AddShadow`, `GenerateDispatchLists`, and `RenderTrafficCar` without `virtual`, so this recovered owner chain has no virtual dispatch edge that would hide another implementation. The scope claim is limited to ARTIST's exported xrefs and these declarations.

## Gate result

Traffic's `GenerateDispatchLists` feeds both the main and shadow-map world dispatches. It reads its blobby-buffer input and asserts it is nonnull at `0x8273B39C..0x8273B3BC`. `RenderTrafficCar` saves its `ShadowMap*` argument in `r24` at entry (`mr r24,r10` at `0x82728B34`). It reads byte zero of that object at `0x827292D8` and branches away from the AddShadow block when the byte is nonzero (`bne` at `0x827293B8`). Therefore the shadow-map invocation does not AddShadow, while a main-view invocation with the flag clear can reach it.

The second exact gate is the saved traffic latch and physics-info pointer. ARTIST initializes `r23` to one at `0x82728B9C`; the live physical-vehicle branch clears it at `0x82728C68`. At `0x8272948C`, a nonzero latch takes the first AddShadow argument path. When the latch is zero, `r20` is checked at `0x827294C0`; null branches past the call at `0x82729558`, while nonnull builds the second argument path and reaches the same direct call at `0x82729554`. For a live physical car, the normal path first obtains and asserts `PhysicsInfo`, so its nonnull pointer also reaches AddShadow. The replay branch derives the latch from the serialized vehicle-data bit and may acquire PhysicsInfo separately.

This makes the current `!lbIsPhysical` placeholder condition incomplete: it excludes the ARTIST physical path even when `PhysicsInfo` is present. The source proposal uses the live-source equivalent `!lbIsPhysical || lpPhysicsInfo != 0` after the shadow-map guard. The replay serialized latch remains unresolved behind G1.

## Buffer and consumer handoff

The path present in the 9cbefd integration snapshot is:

1. Renderer update publishes `mBlobbyShadowManager.GetExternalBuffer()` through `RendererIO::OutputBuffer::SetBlobbyShadowBuffer` (`BrnRendererModule.cpp:6861` in 9cbefd).
2. `BrnGameModule::BridgeRendererToWorld` copies the output pointer into `BrnWorldIO::DispatchInputBuffer` (`GameBridgeRendererToX.cpp:52`).
3. `WorldModule::BridgeWorldModuleToEntityModules_Render` copies it to the traffic dispatch input (`WorldBridgeToEntityModules.cpp:288`), whose getter supplies the pointer to `RenderTrafficCar` (`TrafficEntityModule_Render.cpp:483`).
4. `SwapBuffers` promotes external to internal and clears the next external bank (`BrnRendererModule.cpp:1662` in 9cbefd). The renderer call at line 4945 invokes `mBlobbyShadowManager.Render`; its recovered body reads `maBuffers[mu8Internal]`.

This is static source wiring only. It does not prove that traffic AddShadow records are produced or displayed in a running game.

## Recovered arguments and source proposal

DecFIGS pins `AddShadow`'s shape as `Matrix44Affine`, packed `Vector4` extents named `lvFwdLength_RearLength_BackAxle_FrontAxle`, `VecFloat` width, and `VecFloat` height off ground. Traffic's DecFIGS local hints name `lShadowTransform`, `lvWorldNormal`, and `lfHeightOffGround`. The typed `VehicleTypeRuntime` names `mBBoxOffset` at `+0`, `mBBoxHalfSize` at `+0x10`, and `mCabPivot_TrailerPivot_BackAxle_FwdAxle` at `+0x20`. ARTIST uses those fields to build the packed vector: X/Y are `BBoxOffset.z + BBoxHalfSize.z` and `BBoxOffset.z - BBoxHalfSize.z`; Z/W remain the back/forward axle offsets. Width is `BBoxHalfSize.x`. The nonphysical arm sets height to zero; the physical arm takes W from `TrafficPhysicsInfo::mvRoadTestNormal_HeightAboveRoad`, a DecFIGS field that the current typed owner places at `+0x520`.

The proposal recovers the physical matrix as `row0=Cross(F,N)`, `row1=N` including W height, `row2=Cross(N,row0)`, and `translation=P-worldUp*N.w`; `F` is the vehicle transform's Z row, `N` is the road normal/height field, and `P` is the vehicle transform's position. It preserves the unnormalized cross products and their signs. The nonphysical arm passes the vehicle transform directly. Both arms call `AddShadow` with the packed extents, half-width, and the arm's height. The PC source reuses its existing interpolated render transform and marks that presentation seam.

The old four-wheel-contact description was unsupported by the DecFIGS signature; those temporary contact calculations are removed from the postimage.

Exact files: `source/pre/BrnTrafficEntityModule_Render.cpp`, `source/post/BrnTrafficEntityModule_Render.cpp`, and `source/traffic_addshadow.patch`. The preimage is byte-identical to the Traffic render source in b330 and the 9cbefd integration snapshot. Only the scratch postimage was edited.

The RaceCar bool discrepancy is a separate source issue: DecFIGS names its final bool `lbFarShadowMapCullOptimisation`, while the PC parameter is called `lbEnvironmentMapPass` and currently drives reflection capture policy. The original main-view caller passes `r9=0`; the shadow-map caller sets the map's rendering byte before entering RaceCar. This packet leaves RaceCar's gate and the PC parameter untouched.

## Review boundary

Please verify the direct xref inventory, both gate branches, packed extent ordering, physical matrix axes/W lanes, nonphysical transform path, and external-to-internal handoff against the bindings below. Confirm the `Cross` argument order against ARTIST and DecFIGS. Do not assign compile, runtime, site, or inventory credit; no build or runtime check was run.
