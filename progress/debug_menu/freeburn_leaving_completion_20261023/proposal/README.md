# Leaving overlay: original showing-190 producer repair

The source defect is a dropped **showing notification 190**, after successful network departure. Repair one producer in `src/GameSource/Gui/Flow/Overlay/States/BrnBaseOverlayState.cpp`: replace its raw generic `OutputGuiEvent(lShowing)` with the existing `GuiEventWrapper<GuiOverlayShowingNotification,40>` and queue that wrapper on channel 40. This restores the original wire, with no new hide, timeout, completion or destination-state behavior.

Base: B5 `af18caf8a9e02428cfaa4705599e2b1ca9ea7377`. The target file and all other completion bodies inspected are identical in predecessor 9af; only GuiModule.cpp differs between those candidates. [Before](BrnBaseOverlayState.cpp.before.cpp), [after](BrnBaseOverlayState.cpp.after.cpp), [exact patch](BrnBaseOverlayState.patch), [bindings](bindings.json). Before blob `d818da350a3f95bbd8e265b8275d4299a50fd6b4`; proposed after blob `81868c1b39fa7322f267d6d9111add899b91d0d3` (computed, not written to Git).

The full original path supports this correction:

1. GUI273 reaches `OnlineGameRoomPlayerInfo::HandleLeftGameEvent` and sends GO_BACK (`0x824985D4`). `State::SendStateEvent` (`0x82848550`) records it; `PostUpdate` (`0x8285BA00`) calls the owning `ScriptedFsm::SendEvent` (`0x82836790`), which runs Lua NextState and SetState (`0x82835E90`), including the destination's OnEnter. The observed INGAME destination is not evidence that PauseScreen was required: **InGame::OnEnter already posts finish188 for CNOnlLvgGame**, both in ARTIST `0x824D0624..0658` and candidate BrnInGame.cpp408. PauseScreen is another producer, not the sole one.
2. The existing channel-40 drain unwraps that finish188, forwards it to subscribed overlay input, and retains it in the overlay director loopback. Director `HandleWaitFinishRequest` (`0x824F39E0`) stores an early matching request. The wait state's queue can clear it while the popup is still initializing or transitioning in.
3. After transin completion, `BaseOverlayState::Update` emits showing190 at original `0x824B2C78`. Original publisher **`0x824B2938` boxes `{size=8,type=190,offset=16,payload=CgsID}` as 24 bytes on channel40**. Candidate BaseOverlayState.cpp202-204 instead uses the generic template, which queues bare `(190,8)` (`CgsGuiStateInterface.h219-222`). DrainFlowOutputQueue has no raw190 arm: default drops it and clears the observer output queue (9af GuiModule.cpp3691-3700). No specialization repairs this type; the only header specialization is network suspension.
4. Original director Update `0x82520B3C..B6C` and candidate header58-67 replay stored finish188 when matching showing190 arrives. Its model output is bridged and subscription-routed before overlay Update. BaseWaitOverlayState::UpdateRunning (`0x824B26D0`) accepts the matching id, causing transout; after its callback the base sends DONE and OnLeave posts complete189 (`0x824B2DC8`). The proposal makes the existing 190 replay leg reachable through the correct channel.

Original wire proof: [complete ARTIST publisher export](../../../../.ida-exports/BURNOUT_X360_ARTIST.XEX/0x824B2938.json), including:

```asm
0x824B2944  ld        r11, 0(r4)
0x824B2948  li        r6, 0x18
0x824B294C  li        r5, 0x28
0x824B2958  std       r11, 0x70+var_10(r1)
0x824B295C  li        r11, 0x10
0x824B2960  stw       r11, 0x70+var_18(r1)
0x824B2964  li        r11, 8
0x824B2968  stw       r11, 0x70+var_20(r1)
0x824B296C  li        r11, 0xBE
0x824B2970  stw       r11, 0x70+var_1C(r1)
0x824B2974  bl        CgsModule__VariableEventQueue_65536_16___AddEvent
```

Declaration/layout proof: [candidate event declarations](../candidate9af/BrnGuiEventTypeDefs.h)1197-1205 define the showing payload as a bare CgsID and assert size8. [existing wrapper](../candidate9af/CgsGuiEvent.h) stores three s32 header fields followed by the naturally eight-aligned payload, recording its offset and size: offset16/size24 for this type. The proposal reuses that wrapper, already used by OutputViewState/InternalState; it introduces no new wire struct or layout accommodation. Layout is established from declarations and original assembly; no local compiler was run.

Native baseline: I viewed [bb_007920.bmp](../../freeburn_leave_execution_20261023/run_after_leave_pixels/frames/bb_007920.bmp): Leaving remains visible over the offline world/HUD. The repeat log has request52 at23426, start CNONLLVGGAME at23437, GUI273 at23467 and INGAME at23468, with no matching complete before clean owned close. These are the new post-completion pixels, not the earlier exhausted capture set. Exe SHA-256 is `31de06d9d57a3580091f51eec33acd3d900b815a8b318ad777271a0165206b7f`; log `5dd088cc9c811eefa300f4dd7ede94ace6b04a91010181cb675415edaee8eaa6`; frame `5de72abb40ba151da5276ab5a0e3eb28b687fb4342f9a36502b35d753bd497a9`. Full bindings include provenance and owned terminal status. Automated baseline PASS measured endpoints; the image establishes failure of the reported GUI behavior.

The raw190 drop is proven in source. The baseline has no internal showing190/finish188 state witness, so this does not establish it is the only stall. Root's fixed-build acceptance should retain GUI273, observe `[overlay] complete CNONLLVGGAME 1`, overlay flow returning from IGO_WAIT to INVISIBLE, and post-completion pixels without Leaving. If incomplete, the next specific witness is the overlay's internal state and transin/transout callback flag, together with producer190, director replay188 and UpdateRunning's id match. Host and join share this producer; the supplied visual reproduction is host-only.

Only isolated scratch artifacts were written. No shared source/index/Git-state change, CI/build/compiler/test/game/Stage/Run/input action was performed. This proposal has no compile, native-fixed or hosted credit and is ready for Root's fresh review.
