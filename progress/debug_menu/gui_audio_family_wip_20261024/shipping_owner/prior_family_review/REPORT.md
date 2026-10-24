VERDICT: fail

The exact canonical GUI audio-family composition closes the earlier G1 payload/identity collision, but introduces one shipping-source blocker, A1: mounted state publishers require an explicit specialization whose only definition is in an unmounted TU. The payload, producer conversions, raw module-output path, sound-message body and retained-inbox ordering otherwise pass this bounded source review. This is a source verdict, with no compilation, link, fixture, activation or native-readiness credit.

Exact binding:

| Item | Bound value |
|---|---|
| Source | `a761bf9fc3b1bc960bc77d3f0f36c0a0c34e5f7c` |
| Source tree | `66b59edf09830ee376b2cddc5f5f2397b817d5aa` |
| Parent/base | `4c7c6ba2f97533315d5663d22499042cb007df31` |
| Paired workflow | `2bd1b23bc6e97eb528c166f6f06d40513d4625ce` |
| Workflow gitlink | Exactly the source above |
| Root INPUT_SEAL SHA-256 | `81e35403f33b557111652b263dabaf970d350e9bf0cbb1a26a59b3409913dadf` |
| Author bindings SHA-256 | `0da7f67c979d1e375116b7b4024a5dc22ce12ce2d52c4041ae1ed6e38ef09c04` |
| Author source patch SHA-256 | `36fe3f909483a6b8f0df2da71185854429691290efeb4f07abda7fd73f6e4a2a` |

All 197 author-packet files match Root's seal, every one of the 54 pre/post snapshots matches its declared hash and the exact base/source Git blobs, and the complete source diff is exactly the 35 declared paths. The author patch reproduces byte for byte from those snapshots in binding order. It omits Git's index metadata and uses binding order, so it is not byte-identical to a default `git diff`; its source hunks are fully accounted for. All 20 ARTIST and nine DecFIGS evidence files match the frozen manifest and the original exported files. Additional ARTIST `0x82469C68` was read and retained for the two CodeTicker raw publishers. Full per-file hashes and Git blob IDs are in BINDINGS.json.

**A1 — the audio publisher specialization is absent from the shipping source set.**

`src/GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h:296–298` declares the explicit specialization of `StateInterface::OutputGuiEvent<BrnGui::GuiAudioTriggerEvent>`. Its sole definition is `CgsGuiStateInterface_OutputGuiEvent_Inst.cpp:23–30`. Declaring that specialization prevents these calls from using an implicit instantiation of the primary generic body. The source-wide definition/reference inventory is retained under inventory/.

The bound shipping `tools/build/build_game_exe.bat` mounts the ordinary `CgsGuiStateInterface.cpp` at line 4902, but never mounts `CgsGuiStateInterface_OutputGuiEvent_Inst.cpp`. No source includes the latter TU. The mounted ordinary CPP includes only the header, language manager and assert provider at lines 1–3; it does not define this specialization. `compile_exe.py:643,668,683–690,728–739` derives and links its object set from the response-file sources and excludes unmounted objects. The link tail contains system, FFmpeg and Lua libraries, with no separate GUI engine library supplying this new definition.

There are concrete mounted consumers: `BrnBootLegal.cpp:749–751` constructs and calls the specialization, and the build mounts it at line 4839; `BrnCarSelectLivery.cpp:438–441` is mounted at line 4682; `BrnOnlineGameRoomPlayerInfo_wH_06.cpp:146–164` is mounted at line 5224. In fact all 45 identified state audio post expressions across 34 TUs directly include this specialization declaration and all 34 TUs are mounted. These include the 39 explicit calls documented in the packet and six deduced-template calls. This is a static missing-provider defect, not an observed compiler or linker diagnostic. A concrete correction must make the audio specialization available in the actual shipping source set while retaining the reviewed contract; the present exact source is not approved by an unseen correction.

The changed `VariableEventQueue_8192_16.cpp` is also unmounted. Its delta is only a size assertion and adds no new out-of-line dependency: the actual `VariableEventQueue` implementation is in the selected header. Its assertion therefore supplies no shipping compilation evidence. A1 is specifically the newly required specialization definition.

The following source contracts were checked directly:

| Contract | Source evidence and primary/declaration check | Result |
|---|---|---|
| Payload and base | `BrnGuiEventTypeDefs.h:113–148`; `CgsGuiEvent.h:58–67`; selected `CgsVariableEventQueue.h:38` supplies empty, nonvirtual Event. DecFIGS BrnGuiAudioEvent.h:43/80–83 and CgsGuiEvent.h:58 name the empty `GuiEvent<452>` ancestry. ARTIST `824F6350` uses this/action/component/label/movie in r3/r4/r5/r6/r7 and stores fields at 0/32/36/68, terminating names at 31/67/99. | Pass: 100-byte, four-aligned pointer-free payload; runtime GetEventType is 457. No other actual `GuiEvent<452>` use was found. |
| State publication body | `_OutputGuiEvent_Inst.cpp:23–30`; selected `GuiEventWrapper` in CgsGuiEvent.h:180–210 stores sizeof(T), derived GetEventType and aligned payload offset. ARTIST `82436890` memcpy is 100 bytes, words are 100/457/12, AddEvent channel is 40 and record size 112. QAAX mangling and DWARF say void despite the decompiler's int prototype. | Body passes; availability fails A1. The stack wrapper is copied synchronously by selected CgsVariableEventQueue.h:460–466. |
| Other explicit instantiations | All 65 non-audio lines in `_OutputGuiEvent_Inst.cpp` compare exactly after int-to-void replacement. The primary template in CgsGuiStateInterface.h:287–292 is byte-identical to base. | Return-contract correction passes; no approval of all other generic payload semantics or their activation. |
| Changed state producers | Every changed producer preserves the complete Construct call expressions, arguments and ordering; manual wrappers/header mutations are replaced by the canonical typed publisher. | Payload deltas pass; shipped calls are blocked by A1. |
| Raw module publication | `BrnGuiModule.cpp:2363–2416`: unchanged callback maps 14 action strings and sends this payload directly with derived id and sizeof. ARTIST callback `825112B0` calls `8250BE70`, which passes r5=457/r6=100 to AddEvent at `8250BF0C–1C`. `CgsGuiModuleIO.h:123–131` is the selected generic raw publisher, with no extra wrapper. | Pass: callback emits raw 457/100. |
| Existing raw CodeTicker output | `BrnInGameMessageRenderer.cpp:1534–1537,1600–1603`; additional primary `82469FCC–FE0` and `8246A108–11C` construct and post raw 457/100. | Pass: repaired payload starts at byte zero, so existing explicit 100-byte posts now carry the correct fields. |
| Sound message | `BrnSoundLogicModule.cpp:529–564` copies exactly sizeof(payload)=100 into Message data and queues event 6. Selected CgsMessage.h:52–168 provides a 16-byte header and the same typed mData used by the sink. ARTIST `826EE13C–170` copies 0x64 into message 6; typed publisher `826DEEAC` supplies 0x74 bytes. | Pass for the changed payload/copy/size contract: 116-byte message. No full sound-engine/header ABI audit credit. |
| Sink and other direct messages | `BrnPresentationEffect.cpp:265–297` reads the same canonical mData fields. ARTIST Notify `826FF924,968,9BC,9FC` addresses message+16/+48/+84/+52; helper `8269E3A8–400` reads payload+68/+32/+36/+0 for hashes/action. CameraFlash and OnlineRaceStart at SoundLogic CPP:1199–1202/1245–1248 construct the same corrected type directly. | Field/copy composition passes; unchanged Resolve/Play/voice behavior is not newly certified. |
| Genuine event 201 | `BrnGuiDemangledEventTypes.h:239` remains eight bytes. Game bridge `GameBridgeGameStateToX_EventFlowGuiEvents_wZ_00.cpp:111–117` publishes the CgsID; cache CPP:2608–2633 compares that doubleword and hides its matching row. Primary cache `8250E418–478` (switch rebased by four) performs the same eight-byte compare/store. | Pass: no rename or filtering of HideDriveThru. |
| Old 201 compatibility | SoundLogic CPP:539–549 requires exactly size112 and words 0/201/12 before copying body+12. The size check short-circuits before header access for event201/8. The canonical type no longer produces 201 audio. | Pass for this explicitly PC legacy-only compatibility. It is not console behavior credit. |

The sound 457 arm accepts the exact 112-byte 100/457/12 wrapper, or a raw prefix of at least 100 bytes. It is not a general malformed-record validator. All actual canonical producers checked here produce raw100 or the exact wrapper112; no extra producer relies on another retained audio layout. No ID-only change, GUI cache filter or dropped-input workaround was introduced.

The independent count check found nine explicit state audio calls across six TUs in the base and 39 across 29 in the postimage: 30 conversions. Six additional calls deduce the same template type in CrashNavPanel, FriendsList, MainMap, PreRaceFlyBy and ShowtimeInstantResults (two calls in the last TU). Those six calls are included in the actual 45-call/34-TU dependency check. The 51 ARTIST constructor xrefs remain a separate function-xref count. None of these counts certifies registration sites, behavior, controls or runtime execution.

Every changed source path was reviewed. Mount lines below refer to the exact paired workflow's build_game_exe.bat. Header rows are canonical src providers selected before vendor include roots; the scoped widths come from src/types.hpp (`s32=int32_t`), with Event, wrapper, queues and Message providers captured under providers/. No alternative vendor header was substituted for these fully qualified includes.

| Changed path basename | Shipping mount | Delta disposition |
|---|---:|---|
| BrnCarSelectLivery.cpp | 4682 | Publisher conversion passes; A1 dependency |
| BrnCarSelectVehicle_Input.cpp | 4681 | Publisher conversion passes; A1 dependency |
| BrnChallengeListComponent.cpp | 4773 | Publisher conversion passes; A1 dependency |
| BrnCrashNavAccountManagement.cpp | 4723 | Publisher conversion passes; A1 dependency |
| BrnCrashNavColourCalibrate.cpp | 4751 | Publisher conversion passes; A1 dependency |
| BrnCrashNavMap.cpp | 4735 | All six conversions preserve cue args/order; A1 dependency |
| BrnCrashNavMapMain.cpp | 4736 | Zoom-out conversion preserves payload; existing zoom-in also checked; A1 dependency |
| BrnCrashNavOptions.cpp | 4722 | Publisher conversion passes; existing flagged missing row-preview behavior remains outside delta |
| BrnCrashNavPanel.cpp | 4739 | Comment-only delta; deduced audio post checked; A1 dependency |
| BrnEATraxMenuComponent.cpp | 4743 | Publisher conversion passes; A1 dependency |
| BrnGameModule.cpp | 268 | Comment-only delta |
| BrnGuiDemangledEventTypes.h | included | Comment-only delta; actual HideDriveThru201 unchanged |
| BrnGuiEventTypeDefs.h | included | Canonical payload/base/runtime identity passes |
| BrnGuiModule.cpp | 4334 | Two comment changes; callback/inbox composition checked below |
| BrnImageGallery.cpp | 4770 | Publisher conversion and wrapper-size assertion target pass; A1 dependency |
| BrnOnlineGameOptions_wI_02.cpp | 5310 | Publisher conversion passes; A1 dependency |
| BrnOnlineGameOptionsSummary.cpp | 5333 | Publisher conversion passes; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wH_06.cpp | 5224 | Comment-only delta; all four existing explicit posts checked; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wH_08.cpp | 5226 | Both publisher conversions preserve cues/order; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wH_09.cpp | 5227 | Publisher conversion passes; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wH_10.cpp | 5228 | Publisher conversion passes; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wH_13.cpp | 5231 | Publisher conversion passes; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wN3_02.cpp | 5239 | Publisher conversion passes; other wrapper helper unchanged; A1 dependency |
| BrnOnlineGameRoomPlayerInfo_wN3_03.cpp | 5240 | Publisher conversion passes; A1 dependency |
| BrnOnlineInstantResults.cpp | 5244 | Publisher conversion passes; A1 dependency |
| BrnOnlineLoading.cpp | 5306 | Publisher conversion passes; A1 dependency |
| BrnOnlineScoreboards_wI_00.cpp | 5320 | Publisher conversion passes; A1 dependency |
| BrnOnlineSelectRoute.cpp | 5276 | Publisher conversion passes; A1 dependency |
| BrnOnlineTeamSelection.cpp | 5277 | Publisher conversion passes; final braces unchanged apart from line endings; A1 dependency |
| BrnSelectRoutes.cpp | 4704 | Publisher conversion passes; A1 dependency |
| BrnSoundLogicModule.cpp | 2992 | Bounded decoder/copy delta passes |
| CgsGuiEvent.h | included | Narrow empty tag452 specialization passes |
| CgsGuiStateInterface.h | included | Audio specialization declaration is well formed; A1 composed dependency |
| CgsGuiStateInterface_OutputGuiEvent_Inst.cpp | absent | Audio body and 65 return contracts pass; A1 definition unavailable |
| VariableEventQueue_8192_16.cpp | absent | Assertion-only delta; no shipping assertion/compilation credit |

**Earlier G1 and retained inbox:** the old exact4c7 report remains FAIL and unchanged (REPORT SHA-256 `ace7a51a09406e1b2f2414de3d5b1c1960d6cf9baa2c6289f43524e539846119`; SEAL `8238d54ea831bf44664f7886a61c390b89edae1c1fe20b9b736c2c77ff458d70`). This composition closes its specific G1 collision: input22 calls the repaired callback at BrnGuiModule.cpp:2538–2546; raw457/100 reaches current module output, while state wrappers are unwrapped by the existing channel40 arm at 3371–3382. Output is copied to the inherited stored queue at 4539; next Update appends and clears it at 3695–3696; common cache delivery remains at 2841–2842. The complete ViewIO trigger queue is copied then retired at 4524–4532. ARTIST base Update `8286050C–578` independently pins ViewIO flush/clear, bridge, then complete module-output retention. The repaired audio record therefore reaches the common cache/observer tail as 457 rather than the former 201/112. Genuine201/8 still reaches its own cache arm. There is no new per-ID cache bypass.

The retained queue's earlier lifetime/constructor review is not replaced, and no other earlier FAIL report is amended. The complete ModelIO path and cold route-load work remain excluded. Existing flagged or partial GUI/render/route/sound behavior is not approved merely because the family type now fits. The exact composition still receives FAIL because A1 prevents the canonical state publisher from being supplied by the shipping source set. Build/link availability must be corrected and separately bound; no fixture, CI, native execution, sound playback, individual control, module activation, original full Module/Prepare/Release, mount success or raw-BE PC schema approval is conferred by this report.

BATCH_VERDICT: fail
