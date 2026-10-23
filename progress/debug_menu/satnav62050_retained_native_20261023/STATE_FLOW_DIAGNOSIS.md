# SatNav 62050 state-flow diagnosis

Status: sealed, source-only diagnosis of the retained native 62050 capture. This packet records the cause of the broad HUD loss visible in the positive-override phase; it does not repair or reclassify the override, viewport, or alpha sites.

The positive-override phase containing selected frame bb_008040.bmp coincides with a world-to-GUI engine-off transition in the retained log. Raw log lines 26215–26217 show GUI event 379 with engineOn=0 (raw state 2→3), then manager event 213 disabling SatNav while its render flag was enabled before the event, then EventHud_Animator entering transout. Line 26228 reports ignition state 3 with carInGameMode=0 and no accelerator or brake input. The code explains the displayed loss: event 379 makes the in-game HUD flow play transout; the follow-on event 213 disables the SatNav renderer and mirrors that state back into its debug control. The reason the world entered raw state 3 is unresolved. This is not evidence that the override itself removed the whole HUD.

The earlier negative-override phase is a different observation. Debug-component construction seeds SatNav Render and Main Map Render false, Enable Custom Renderer true, and Override false. When the test turns Override on while those per-renderer controls are false, the manager disables the SatNav and MainMap slots. Turning Override off does not restore previous flags: both the PC body and ARTIST 0x82450908 only write those slots inside the override branch. That behavior is present in the original assembly. It is not a PC divergence finding, and this packet does not classify the override site as pass, fail, or a no-op.

For the intended-visible r004 phase, the capture does not establish positive override behavior. After r004 sets Override true, the real engine-off transition and event 213 occur before selected frame bb_008040; event 213 changes the cached SatNav control back to false. The screenshot therefore cannot witness the intended positive branch. Viewport-coordinate and alpha sites also remain unverified because their selected images lack the map texture.

## Retained evidence

The exact executable source is commit 8b2940d40e76fd6a88a37615f6163a99c2d5e3b8; executable SHA-256 is 95c120dc8b2f20123ec28d86873ba5e5bb5a4c2d3fdb7d922d51d927ea9e1cbd. The raw log is bound by SHA-256 2647508e41297c9a79fa45e7cddb7f2b3aa520659809025bce47b27371bd7710. The line excerpts below are copied from that retained log.

| Raw log line | Exact retained excerpt |
|---|---|
| 1376 | `[satnav-diag] LoadResources: map(199)nn=1 mask(201)nn=1` |
| 14774 | `[hud-reveal] posting GUI 379 GuiPlayerEngineEvent engineOn=1 (raw state 1 -> 2)` |
| 14775 | `[satnav-diag] mgr 213: submode=1 flag=1 fade=0.000000 satnavEnabledBefore=0` |
| 14780 | `[satnav-diag] RenderComponent DRAW: origin=(996.000000,479.000000) rightup=(195.999985,145.000000) uv0=(0.719653,0.361362) uv3=(0.796666,0.438308) colour=3858759679` |
| 25780–25782 | `r004: /Gui/Gui Custom Renderer/Override what game is telling to render`; `TRUE`; `r004: /Gui/Gui Custom Renderer/Override what game is telling to render` |
| 26215 | `[hud-reveal] posting GUI 379 GuiPlayerEngineEvent engineOn=0 (raw state 2 -> 3)` |
| 26216 | `[satnav-diag] mgr 213: submode=1 flag=0 fade=0.000000 satnavEnabledBefore=1` |
| 26217 | `[AptComm] GetComponentData comp=2 ('EventHud_Animator') key='apt_Transition' -> 'transout'` |
| 26228 | `[ignition] tick state=3 active=1 enableSwitchOff=1 carInGameMode=0 inCarSelect=0 crashing=0 accel=0.000000 brake=0.000000` |

The PHASE_FRAMES review binds a phase-adjacent image and helper note, not a same-frame image/log pair; this diagnosis is phase-level and makes no frame-exact ordering claim.
The bridge source posts GUI 379 only when the player engine’s running/non-running boolean changes (GameBridgeWorldToGui.cpp:245–276). FBurnMainHudState::UpdateRunning handles 379 by selecting transout for engine-off and posting event 213 with show=0 (BrnFBurnMainHudState.cpp:1154–1181). The run log directly records this consumer response.

CustomRendererManager::RecvEvent_Event213 applies the event flag to the SatNav renderer and mirrors its actual enabled state into mbSatNavRenderEnabled (BrnCustomRenderer.cpp:610–620). CustomRendererManager::Update then applies the override, master, and per-renderer gates only to SatNav, MainMap, and AboveCar (same file:667–692). Its render loop calls a component only while that component is enabled (same file:698–715). ARTIST export 0x82450908 has the same conditional writes and no restore branch; export 0x82450848 likewise gates rendering by component enable and layer.

The texture path was live before the transition: raw line 1376 records map resource 199 and mask resource 201 as non-null, and line 14780 records a SatNav draw. SatNavRenderer::RenderComponent checks the payload texture pointers and binds lazy texture states from those pointers (BrnSatNavRenderer.cpp:1233–1252, 1357–1383). Once the manager/event disables the component, the manager skips it before RenderComponent. The retained evidence supports an enable-state transition, not texture loss.

Ownership is named and typed: GuiModule owns CustomRendererManager by value (BrnGuiModule.h:473), and CustomRendererManager owns SatNavRenderer by value (BrnCustomRendererManager.h:176). The current private descendant 17ab0a96e27bed5e60ffc55cb81dcf0a653b1e4e has no changes to the GUI/event/renderer paths bound here.

The test’s F2 inputs invoke the debug script binding: behavior-004 binds F2 to the next script; DebugController maps VK_F2 to E_KEY_F2, DebugUI passes it to ScriptInterface, and ScriptInterface executes the bound command. The game-input path suppresses the host keyboard while the debug UI owns it (CgsDebugController.cpp:239–246, CgsDebugUI.cpp:362, CgsScriptInterface.cpp:83–89, CgsInputPadsPC.cpp:874–879). This supports the script route; it does not establish why the world engine state changed.

## Preserved status

The original case remains PASS with 12 checks and zero asserts. Its wrapper/archive remains INCOMPLETE_EVIDENCE_RETAINED, exit code 1, because the original archiver rejected frames.csv as an unexpected frame file. Neither status is changed here.

The prior independent review’s site dispositions remain one pass (outline only), six insufficient (override, four rectangle edges, alpha), and zero fail. This diagnosis awards no new behavior credit. The final aliases being restored do not prove visual restoration, and the engine-off transition prevents the selected frame from assessing the positive override branch.
