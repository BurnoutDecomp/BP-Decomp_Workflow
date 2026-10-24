# Independent renderer and GUI source review

BATCH_VERDICT: pass

The four packets pass within their stated source scopes. No proposed definition or wire-record defect was found. This is approval of the renderer lifetime store and five GUI producer repairs against their exact targets. It is not whole-feature acceptance: event143 has no established module-input return route, and GUI172 reaches an original GameState90 assertion path. Neither invite sign-in restoration nor successful custom-race creation is approved.

| Packet | Source verdict | Remaining boundary |
| --- | --- | --- |
| renderer_construct_newmodule_seed | pass | WIP classification only; original Prepare activation and allocator ownership remain unresolved |
| gui_event466_completedgame_voiceover_channel40_20261024_ea5ce572 | pass | Sound/observer source routes exist; audible playback and branch reachability unverified |
| gui_bootlegal_events88_143_channel40_20261024_ea5ce572 | pass | Event88 has a sound consumer; event143 output-to-module-input return is unclosed |
| gui_channel40_game_state_translation_batch_20261024_edca934 | pass | Both translations are correct; GameState90 takes the original default assertion |

No packet is rejected within these bounded source scopes. The original-Prepare branch remains unactivated. No compilation, tests, link, hosted build, mount, allocation, initialization, native or gameplay credit is granted.

## Exact inputs and bindings

Entry: [REVIEW_REQUEST.md](REVIEW_REQUEST.md). The reviewed source contexts are distinct:

- Renderer target: `183ca9c9a23aa93fe9a1bdf1e47b02e84f395f1e`, whose parent is `702d242bd0e99a8510ef09bbc42b0a316956ac9b`. The frozen renderer preimage from702 is byte-identical at183.
- GUI target: `edca934dc502f71f64ad873cdd386afe5e3eeeb2`, whose parent is `ea5ce572baedd4ad8918f6d5bfcdfd756250d411`. Both ea5-based GUI files remain byte-identical at edca; the final two-file packet uses edca directly.

[BINDINGS.json](BINDINGS.json) records all five exact pre/post SHA-256 values, target Git blobs, all packet-file hashes, evidence checks and actual provider snapshots. All four full unified diffs reproduce their pre/post files. All five preimages match their requested target commit, not merely a related branch name. The three GUI packets change four disjoint files and compose over edca. The renderer overlay is separately bound over183; this review does not combine these two branches into a newly approved commit.

| Packet | Manifest/bindings SHA-256 | Patch SHA-256 |
| --- | --- | --- |
| renderer seed | `8e292f05f7d6f2b70faea3578be0655d6cf38473f73fd906f0c08fb08b035e5d` | `5c3422859426946ccc6b5e59b3bfb7ad2c1c81998d5f1b0eb04d0b8c08d792c2` |
| CompletedGame466 | `1c3ca3a15463dee22542f8958d9e5aeaac80dc517d0e389d55755285c0424499` | `220d26d782057d0fed9dbbafb10a809f064497f6989062dea6e493f8cc328c11` |
| BootLegal88/143 | `29978065fe542fd10c129d6c58ba627132513ffbe39f556a9ea08e0b272c77cf` | `38fab0535b169f8e5fcdd7f0e12d468b48d351141d703ee16ad456e695f999aa` |
| GameState326/172 | `08dc6c462a8fdda3cecc3965fa79561c2561395c51781b7d0d2dc03d4c8b9882` | `a2f9cd7c346762e48f5a4859d8c4b0fce8358891ffbc8bf31333323b13e1e4d9` |

The 73 packet files are archived under [inputs](inputs/). All author-bound source/evidence hashes match. All11 frozen ARTIST JSONs also match the workspace's original exports. Thirteen further external evidence files, including the five GameState-packet ARTIST exports, its two DecFIGS files and six independently inspected primary-chain exports, are frozen under [primary](primary/). Thirty-one actual source providers are frozen under [providers](providers/). The proposed full files are under [proposed](proposed/).

Source references below are relative to the indicated exact source/proposal context. ARTIST addresses refer to frozen assembly, not inferred prototypes from pseudocode.

## Renderer Construct lifetime store

PACKET_VERDICT renderer_construct_newmodule_seed: pass

`proposed/renderer183/src/GameSource/Graphics/BrnRendererModule.cpp:1458-1460` adds only the inherited `mbIsNewModule = true` store and its explanatory comments. Removing that exact insertion reproduces every preimage byte. Existing native early returns, allocation calls, capacities, sky-dome ownership and other bodies remain unchanged.

ARTIST Construct8240A778 uses this=r31. Its final store8240BF90 is `stb r29,4(r31)`. The value is positively1:8240BB9C executes `li r29,1`; all14 explicit references from that seed to the final store were independently extracted and equal the packet receipt. No later instruction redefines r29 before the final store. The original base Construct call at8240A800 and base Construct8286E768 clear the same inherited byte earlier in the lifetime. DecFIGS Module declaration identifies it as protected bool `mbIsNewModule`; the current owning Module header declares the same real member (`providers/renderer183/.../Module/CgsModule.h:65-66`). This is not a synthetic readiness flag or numeric-offset write.

The semantic effect is real even though no Prepare call is added. Current base Prepare (`.../CgsModuleSingleBuffered.cpp:19-79`) tests this member at each legacy input/output/factory/data-structure stage, matching8286E7A0. True skips those legacy operations; legacy lock/access/SetMultiThreaded methods retain their `!mbIsNewModule` assertions (`:164-208,253-310`). The new store therefore restores IO classification, not Prepare completion.

The existing GameData-list/renderer original Prepare call is visible in the separate WIP game Prepare path (`providers/renderer183/.../BrnGameModule.cpp:751-765`). This packet does not select it in the native path. The native Construct already owns and prepares immediate buffers and dispatch storage (`.../BrnRendererModule.cpp:1351-1390`). Re-running original Prepare over them still needs explicit owner/capacity reconciliation, as does sky-dome geometry. The native failure return at1387-1390 still bypasses the added normal-completion store. No allocation or activation approval follows.

Final renderer CPP SHA-256: `8c269aa8560fde1cef1b8033acf156f2087edd8acb615c0fe2561249b44d5693`.

## Shared GUI producer/queue contract

The actual StateInterface getter returns its real output queue (`providers/gui_edca/.../CgsGuiStateInterface.cpp:120-123`). The unchanged generic OutputGuiEvent posts the raw payload under its own type (`.../CgsGuiStateInterface.h:218-223`); the new sites instead use the existing canonical GuiEventWrapper (`.../CgsGuiEvent.h:170-200`). It contains the three signed32 words `{sizeof(T),T::GetEventType(),offsetof(mOutEvent)}` followed by T, with its real alignment. No extra GuiEvent base header is inserted.

The actual VariableEventQueue AddEvent owns/copies the record synchronously, writing the supplied outer key and byte size separately (`.../CgsVariableEventQueue.h:440-469`). Stack record destruction therefore does not leave a queued pointer to a local object. ARTIST82435188 supplies the corresponding real queue implementation.

GuiModule::DrainFlowOutputQueue walks the state's real queue (`.../BrnGuiModule.cpp:3191-3214`). Its channel40 arm reads payload size/type/offset, copies the unwrapped event into mGuiOutQueue and forwards it to registered observers (`:3416-3466`). ARTIST EventInterpreterModule::ProcessOutEvents8285E1D0 has that exact three-word unwrap at8285E568..57C. The old raw466/200/156/326/172 posts do not enter this arm; unmatched outer keys reach the default and are retired by the queue clear (`:3737-3746`).

The native game GUI leg publishes mGuiOutQueue into the actual shared GUI output under its write lock (`.../BrnGameModule.cpp:4893-4899`). Sound receives that shared output's real queue through BridgeGuiToSound (`.../GameBridgeGUIToX_Sound.cpp:27-39` and `.../GameBridgeGUIToX.h:20-24`); the owning OutputBuffer getter/append bodies are real and lock-checked (`.../CgsGuiModuleIO_OutputBuffer.cpp:70-84,116-121`). SoundLogicModule::Update reads the RootInput's actual GUI queue before ProcessGuiEvents (`.../BrnSoundLogicModule.cpp:1393-1399`). GetGuiPayload leaves these raw one/four-byte normalized payloads intact (`:44-59`). Scheduling remains conditional on the existing game/loading paths; no branch was exercised here.

## CompletedGame event466

PACKET_VERDICT gui_event466_completedgame_voiceover_channel40_20261024_ea5ce572: pass

The changed site is `proposed/gui_edca/src/GameSource/Gui/Flow/PostEvent/States/Offline/BrnCompletedGame.cpp:689-696`; record assertions are at69-76. It retains the four-byte MakeHash result for `Elite_Then_100_Percent` and the existing no-rank-up condition. ARTIST caller824D24F8 stores that word and calls the publisher at824D26AC. The publisher824C3178 copies exactly4 bytes, writes `{4,466,12}` and AddEvents channel40/16 bytes. The proposed wrapper has exactly that shape. Existing event356 repair and other file bytes are preserved outside the declared diff.

After the shared unwrap, the current sound consumer at `BrnSoundLogicModule.cpp:559-566` reads the same four-byte name and queues the genuine Playback::Name message36/state5. ARTIST ProcessGuiEvents826ED6C8 corroborates that mapping. The separate observer route exists through subscription-filtered RouteEventToFlow; CarSelectVehicle observes466/467 and sets/clears its actual voice-over-playing byte (`.../BrnCarSelectVehicle.cpp:158,368-374`). Whether that observer is active for a specific frame is not established by this source review. No audible playback, sound-bank availability or completion timing is approved.

Final CompletedGame CPP SHA-256: `54df5a1ef9e9306eb27daa3040ae680cc2c80fcb6a1a4c03fef17331fc781b26`.

## BootLegal events88 and143

PACKET_VERDICT gui_bootlegal_events88_143_channel40_20261024_ea5ce572: pass

The proposed payload-only local types and assertions are at `proposed/gui_edca/.../BrnBootLegal.cpp:183-193,210-223`. They remove the erroneous full-header carriers with raw IDs200/156 and use inner IDs88/143. They do not double-wrap a GuiEvent header.

At595-603, the retained soft-reboot-and-not-invite condition emits byte0 through `{1,88,12}+1`, channel40/16 bytes. ARTIST BootLegal Update82477270 initializes r15=0 at82477280, stores that byte and calls82476BB0 at82477888; the publisher independently proves byte width, inner88, offset12, channel40 and size16. The existing sound logic case88 starts the real playback DAC for byte0 and stops it for nonzero (`BrnSoundLogicModule.cpp:633-640`), matching826ED6C8. The separate already-correct PostCommand16<88> site is unchanged and is not counted as a repaired site.

At726-735, the retained invite-reboot branch takes the saved first controller-port word, emits `{4,143,12}+4` on channel40/16 bytes, then clears the input queue and returns. ARTIST82476D88 proves the publisher; the caller at82477CC0..CD0 supplies the unchanged word. Current GuiModule inbound case143 stores the user index and refreshes sign-in (`BrnGuiModule.cpp:2533-2536`), matching original82528AE8..AF8.

The outgoing channel40 post is normalized into the GUI output/observer paths. The inspected drain does not feed143 back to mpGuiEventInputBuffer or directly execute its module-level case. Therefore the producer is faithful, but controller selection/sign-in behavior remains unclosed. No loopback restoration is approved.

Minor evidence annotation correction: the packet README calls82477CCC the publisher call; that address is the argument word store. The call is82477CD0. This does not alter the source or wire verdict.

Final BootLegal CPP SHA-256: `921d9b9227532362890c78a4602083e19d9bc560b7856c923b9d45da215c733a`.

## GameState translation events326 and172

PACKET_VERDICT gui_channel40_game_state_translation_batch_20261024_edca934: pass

RoadRule at `proposed/gui_edca/.../BrnRaceMainHudState.cpp:2006-2022` preserves its controller/Skillz/friends-list condition, sibling command543 and eight zero payload bytes. ARTIST UpdateRunning8247E898 initializes r18=0 at8247E8C8 and stores its word/byte before the8247EEE0 publisher call. Publisher82436B90 copies8 bytes, writes `{8,326,12}`, and queues channel40/20 bytes. The existing payload type (`BrnGuiDemangledEventTypes.h:1166`) and canonical wrapper give exactly that layout.

After normalization, BridgeGuiToGameState case326 reads payload byte4 and word0 and emits GameState103/4 bytes (`GameBridgeGUIToX_GameState.cpp:251-257`). Primary823DDB78 at823DE4A4..D8 confirms the conversion to0 or1/2 and event103. This caller's zeroed payload requests OFF. The current carry queue is consumed by PreWorldUpdate (`BrnGameStateModule.cpp:502-515`); dispatcher case103 reaches the real road-rule handler (`GameStateModule_ProcessGameEvents.cpp:144,172`, `..._wBT_04.cpp:487-525`).

Custom-create at `proposed/gui_edca/.../BrnCrashNavMapEvent.cpp:745-764` preserves the valid-name condition, actual mCreatedRace copy and subsequent state stores. Primary824DDB90 copies120 bytes and calls its publisher at824DDD94. Publisher824C2FF0 copies120 bytes, writes `{120,172,16}`, and queues channel40/136 bytes. The current align8 payload owns the real120-byte Race (`BrnGuiDemangledEventTypes.h:933-936,958`; `SharedClasses/Progression/BrnRace.h:29-55,86`). DecFIGS corroborates the Race member/type shape; its older event IDs170/324 are not substituted for the X360 IDs172/326. The new assertions and canonical wrapper preserve the correct16-byte payload offset.

The existing translator copies all120 payload bytes and emits GameState90/120 bytes (`GameBridgeGUIToX_GameState.cpp:155-158`), matching primary823DE064..80. It posts through the genuine current PostWorldInput adapter into mGameEventCarryQueue (`GameStateModule_gUI_00.cpp:131-134`), and the GameState pre-world merge consumes that queue on the following pass. The post-world caller and final GUI retirement are at `BrnGameModule.cpp:1934-1936,4994-5003,5117-5120`; these require the full cascade.

**Custom-create feature remains unclosed.** Current GameState ProcessGameEvents has no90 arm and asserts in its default (`GameStateModule_ProcessGameEvents.cpp:9-13,235-239`). This matches ARTIST823A0A18: the jumptable at823A1064 expressly assigns90–92 to default, whose assertion begins823A4E80. This is original behavior, not a missing new reconstruction. Repairing the producer exposes that existing error path if the named branch is reached and the carry queue is processed. The source packet is faithful to its stated producer/translator scope, but successful custom-race creation and safe execution of that branch are not approved. Do not add an invented consumer under this review.

Final RoadRule caller SHA-256: `24ef3ae81a351d754f79d77b63bf8bd193e3fd3749b47e37962b7738e0142a69`.

Final custom-create caller SHA-256: `3d224c7b0b3e30bd1029ae8af57e190da5f74631e5562fdc8774f3cba81d89f3`.

## Review boundary and preservation

All four earlier review folders were rechecked against their seals, including the initial five-packet FAIL, the quote delta, sixth-packet FAIL and exact183 continuation batch. Every listed file remains unchanged. This report does not revise those verdicts or consume any later packet.

Only packet/source/assembly/DWARF reading, read-only Git queries, static byte/hash comparisons and creation of this new review folder were performed. No production, index, ref, build/config/profile/log or earlier report was edited. No C++ compilation, test, CI, game/input, IDB opening or additional agent was used. Root remains the integration, publication and native-validation owner.

VERDICT: pass
