# Active91a takedown output lifetime

VERDICT: fail

Scope: the installed91a GameModule -> GameState pre-world takedown-output lifetime, source-only. This is a confirmed source defect and a strong explanation for the user's normal offline Road Rage count/timer regression. The actual reported session has not been captured, so runtime attribution remains to be witnessed.

## Finding P1: the selected caller re-scores persistent takedown output

`GameStateModule::Construct` (`BrnGameStateModule.cpp:110`) allocates `mpOutputBuffer` once and calls its Construct once. `GetOutputBuffer` (`BrnGameStateModule.h:154`) returns that same pointer. In installed91a GameMain, `DoUpdate_GameStatePreWorld` receives this pointer (`BrnGameModule.cpp:4330`). Its only local IOHelper creates a **PreWorldInputBuffer** (`:1271`); its call at `:1372` passes the supplied output to the full `GameStateModule::PreWorldUpdate`.

The full PreWorldUpdate (`BrnGameStateModule.cpp:533`) clears the module's cached takedown queue. In its not-paused arm it runs TakedownManager.Update, obtains `lpOutput->GetTakedownEventOutputQueue()`, clears the **cache** again, copies the output records into that cache, then calls ProcessTakedownEvents (`:543..550`). It never clears the source output queue.

This source output is not fresh per step:

- `CreateStaticIOBuffers` (`BrnGameModule.cpp:5020`) creates GUI/view/director/world/effects/network buffers, and creates the network output in the in-game flow even during offline gameplay. It creates no GameState output. `DestroyStaticIOBuffers` (`:5068`) tears down those same buffers, not `mpOutputBuffer`.
- The end-of-step retirement (`BrnGameModule.cpp:4790..4835`) clears GameAction, trigger, timer-request, raw-GUI and GameStateToGui state. It omits `GetTakedownEventOutputQueue()->Clear()`.
- GameState output's takedown queue is Constructed at `BrnGameStateModuleIO.cpp:514` and Destructed with its owner at `:638`; those are not per-step operations in this selected host path.
- The examined World, Director, GUI and Network bridges read this queue through const source interfaces. Append copies the source; GetEvent returns a reference without consuming; neither resets the source length. The source-wide accessor/member search found no other active source-output clear.

The producer `TakedownManager::ProcessTakedownEvent` appends a genuine event to this output queue (`BrnTakedownManager_Detect.cpp:713..714`). On every later unpaused simulation step, the unchanged record is copied back into the now-empty cache. ProcessTakedownEvents iterates every cache entry (`GameStateModule_gRR_00.cpp:108`) and, for a player-aggressor record, calls OnPlayerDoesATakedown (`:189`). The thin forwarding method (`BrnScoringSystem_Finish.cpp:115..118`) reaches RoadRageModeScoring::IncrementPlayerNumTakedowns each time. There is no consumed marker in this path.

Consequently a retained qualifying record can increase the **actual integer scorer** each eligible simulation step, without another collision. This can look like a clock-driven number. Each qualifying callback also repeats the original deadline extension while the extension gates remain open: configured u16 seconds plus3 cover seconds. After GOLD has already been reached, the count still increments but the original method returns before extending. This precisely limits the inference; it does not predict unbounded extension after GOLD or after expiry.

The event queue has capacity8. Retaining distinct producer records across steps can also exhaust its lifetime capacity; its AddEvent asserts but then stores/increments. That is a further source risk, not an observed crash in this report.

## Active schedule and ownership

`BrnGameModule::GameMain` (`:4192`) loops over `miNumSimFramesRequired`; CreateStaticIOBuffers runs inside that loop (`:4257`). `lbRunFullModuleCascade` is based on the resulting network-output pointer (`:4281`). In normal in-game flow, the base update set is0x88 (`ConstructUpdateSetFromFsm`, `:5399`), with pause/stall/error flags added separately. The full pre-world call is in the cascade at `:4330`, once per simulation substep. It is not an online-only predicate and not a one-time event-start call.

The same-step readers run after production: World, Director, GUI, then NetworkPostSim (`:4751`) before UpdateTimers (`:4779`) and the persistent-output retirement (`:4790`). This establishes a concrete possible repair boundary: the existing final retirement can clear the canonical typed takedown output after all its same-step readers, before the next substep. A repair in another active owner boundary must retain that same lifetime. No patch was made here.

## Original behavior and regression transition

ARTIST DoUpdate `0x823F0BE4` creates a fresh GameState output. The native CreateIOBuffer instantiation `0x823AC6E8` calls OutputBuffer::Construct at `0x823AC7A0`; that Construct initializes the takedown queue at `0x823829A4`. Native DoUpdate destroys the GameState output at `0x823F2244`. Thus the full original pre-world body can correctly copy its source queue without clearing it: the containing output is already new for the update. The host retained that body but not its output lifetime.

The host previously supplied the missing reset in the extracted helper `GameStateModule::TakedownPreWorldLeg` (`GameStateModule_gTD_00.cpp:194`). Its explicit comment already explains that persistent output otherwise re-scores every past takedown each frame. This clear is unchanged since the Oct9 temporal baseline. Its sole C++ call is from `PreWorldUpdateStuntBringUp` (`GameStateModule_gUI_00.cpp:397`).

Commit `4bbefd59b53dc8dc3b86cb46a6e97801d311ece9`, 2026-10-19T21:22:12+02:00, removed GameMain's PreWorldUpdateStuntBringUp path and selected `DoUpdate_GameStatePreWorld -> full PreWorldUpdate` with `GetOutputBuffer()`. It did not move the legacy queue reset to the selected owner. `history/4bbefd_transition.diff` and its exact parent GameModule preimage pin this transition. A source-wide call search finds the old adapter declared/defined and its internal call, with no selected GameModule caller at91a. Editing only that dormant helper would leave this active failure unchanged.

This attribution is to a concrete source lifetime change in the installed lineage, not to later3966 route-save changes. There is no basis to describe the user's report as an online-mode error.

## Exact inputs and limits

Revision: `91a0ed564f9c9e3dec915bfb416c0467650084ef`.16 whole postimages and7 existing ARTIST exports are copied and pinned in SOURCE_BINDINGS/EXPORT_BINDINGS. All16 worktree files were LF-equal to91a at read time. Key source SHA-256 values:

| Input | SHA-256 |
|---|---|
| BrnGameModule.cpp | `4e62bcd0b771a4f630d887c01a9deb76c065a450491341dd7ab0085144874df5` |
| BrnGameStateModule.cpp | `c36cbb234514f2baadbc975c01582f64fe0ad36f6c2e17468dd37e6bf863e6a0` |
| GameStateModule_gTD_00.cpp | `201cb5bb0cff34917f145df83e1bcc417e1c4f404c68490d1e903a56741026a1` |
| GameStateModule_gRR_00.cpp | `15e404561c93fba8faa70e711b2a21426f3c182feb956ac105435f8606bfd7b2` |
| CgsBaseEventQueue.h | `97a5d2bb923303df831065d5328125b6605c78a7a585ede90b277efa771c15f8` |

The sibling timer packet remains untouched, with manifest seal `b0368ea43e3ebd5b9065217f6cdf1ee9e048351b2da7b7234f7f1279af4764a6`. It records the independently rehashed installed executable `6fa903ebd3200ec46104b47bda8eb0e81d835d0ce6e003da370c11deb14c203a` and the bounded timer-arithmetic/event/text exclusions. Its unresolved runtime-cause status is historical to that sealed pass; this supplement adds the positive lifetime finding.

No production source, index, Git state, earlier packet, CI, compiler/test, game, or IDA database/worker was changed or executed. Only static reads, git object/history reads, hashing, and this new sibling packet were performed. This report does not authorize implementation or execution and does not certify a repaired playable build.
