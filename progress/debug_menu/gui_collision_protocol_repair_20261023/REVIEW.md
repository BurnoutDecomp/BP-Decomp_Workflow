# Independent combined review — GUI collision protocol composition delta 02

VERDICT: pass

Cast/colour increment — VERDICT: pass

Collision completion plus prior F1 repair — VERDICT: pass

Fresh dormant output-handler increment — VERDICT: pass

No remaining source defect was found in the exact six-file composition against B5 `840d83b3c3390d1786ed571b3bf87e3947b89a9e`. This approves the source increment only. No compilation, link, active wiring, native or runtime behaviour credit is given.

## Prior F1 and exact composition

The former F1 is resolved at `postimage/src/GameSource/Game/GameBridgeWorldToGui.cpp:773` by `mGuiModule.AddGuiEvent(&lEvent, lpGuiInputBuffer)`. The existing inherited pointer overload in the supplied exact-base `CgsGuiModule_AddGuiEvent_Inst.cpp:38–46` asserts the input pointer before accessing its write queue and posts the complete `sizeof(T)` payload. Its line 147 explicitly instantiates event 493. This reproduces ARTIST `823DA230`, including the formerly dropped assertion. The address expression is a temporary pointer, so the unrelated mutable-reference overload is not selected; the pointer overload supplies the complete four-byte event without header subtraction. Public base inheritance and the absence of an `AddGuiEvent` hiding declaration were checked. No new helper or duplicate instantiation is needed.

That comment/call replacement is the only difference from the complete previously failed world-bridge postimage. The sub-bridge order, repeated status getters, invalidating → VALIDATED branch, the two completion values (2/3), early-out and event identity are retained. The SatNav colour file and both event-owner header postimages are byte-identical to their previously accepted proposals. The composed GuiModule.cpp equals the complete handler author's postimage plus exactly the two previously reviewed payload-cast substitutions. Its header equals the author's complete postimage.

The entire earlier failed review is retained byte-for-byte: REPORT.md, INPUTS.json, CHECKS.json, INTEGRITY.sha256 and SEAL.sha256. Its original report hash is `c22528bff555278b04368692ff157d81b4b97e26c2e2f3e9cbc4021adf8b1287`; its integrity-manifest hash remains `d54d58df585267288989e192a314f14594374f72a1464926a52508fc31773afb`. This new PASS closes F1 for the new exact postimage; it does not rewrite the prior FAIL.

## Fresh review of HandleEventsPostBaseModuleUpdate

The new body at GuiModule.cpp:3093–3169 matches ARTIST `82507800`:

- r3 is the module and r4 the supplied OutputBuffer. The body locks that buffer for reading, obtains its `VariableEventQueue<18432,16>` output queue, gets the first record and loops on the returned event pointer. Empty output reaches the unlock. It reacquires the same output queue for every GetNextEvent, preserving each accessor's read-lock assertion; it neither clears nor consumes the queue.
- Output event 493 reads the plain four-byte enum at payload offset zero. Value 0 asserts validation state IDLE (0), preserving the exact expression, original file string and line 1729, then writes the networking-invalidate latch true even if an assertion is ignored. Value 1 likewise checks INVALID_FOR_NETWORKING (11), original line 1737, then writes the networking-validate latch true. Every other value asserts the original misspelled message **"Invalid collsion world request output event type"**, line 1745, writes neither latch and continues iteration. The original stores `8250795C` and `82507988` target +0x18D83C and +0x18D83B; the proposal uses the already declared named bools. It introduces no guessed host offsets, new latch or state transition.
- Event ids 508/509 call the existing MovieManager with the same payload and current event id. Event ids 514/515 call the existing ColourCalibrationScreen with the same two arguments. The latter is a load-bearing assembly check: ARTIST's handler pseudocode omits the id argument, but r5 still carries it, and callee `824471E4` saves r5 before testing 514/515. The proposed two-explicit-argument member call is correct. Other event ids are ignored exactly as in the original switch.
- The current record pointer is supplied to GetNextEvent, its returned pointer/id replace the cursor, and UnlockForRead runs only after the loop ends. No event-size guard, extra null assertion, queue reset or early return has been invented. Receiver and lock/assert side effects remain in the original order.

The `void` declaration is supported. DecFIGS DWARF explicitly declares a non-virtual `void HandleEventsPostBaseModuleUpdate(OutputBuffer*)`. ARTIST `825079D8–9E0` calls UnlockForRead and restores the frame without assigning a semantic result; its only recorded caller overwrites r3 immediately after `8252A330` and does not inspect a returned value. The current IOBuffer API also declares UnlockForRead void. The author's statement that UnlockForRead leaves the output pointer in r3 should be read narrowly: normal assertion-free execution leaves incoming r3 residue, while assertion calls may clobber it. No reliable returned pointer is established or used, so this does not invalidate the proposed void signature.

DecFIGS confirms the existing latch names, declaration shape and setter/consume roles. Its PS3 helper calls, shifted offsets and historical event ids do not override ARTIST's direct byte stores and X360 event 493. Implementing these stores directly through the existing named members is appropriate. The exact-base validation lambdas already read-and-clear these latches; this delta does not add or alter them.

There is exactly one new declaration and one body. No duplicate declaration/body exists in exact base source. The added method is non-virtual and adds no member data or vtable slot. Its OutputBuffer, event, enum, state, queue, assertion and receiver types are already available through the bound headers. The event-owner relocation still has one definition and a four-byte size assertion; it does not add a CgsGui event header or change the existing wire representation. No new include/type conflict was identified by inspection; compilation remains for the hosted compiler.

## Dormant boundary — no completed active protocol

ARTIST Update calls the base `CgsGui::GuiModule::Update` at `8252A314`, unlocks the same output buffer for writing at `8252A324`, invokes this handler at `8252A330`, then performs the next virtual dispatch. That call window and its argument registers were read from the full bound caller export, rather than inferred from its inaccurate decompiler signature.

The selected PC Update has no OutputBuffer argument and no equivalent base-Update call. Its existing per-flow drain queues already route 508/509 to the movie receiver queue and handle 514/515 directly; the movie queue is later serviced within the selected Update. Exact-base BrnGameModule.cpp:4893–4899 calls the selected Update first and copies its produced queue into the frame OutputBuffer afterwards. Adding a call at that later copy would use a different execution point and duplicate already handled movie/calibration work. Calling on the per-flow queues would not be this OutputBuffer contract. The proposed method therefore deliberately remains uncalled. No late duplicate caller was introduced.

Inbound event 493 completion (2/3) in DispatchInboundGuiEvents remains separate from output event 493 request (0/1) in this handler. The new world producer supplies the inbound completion record; the dormant handler latches output networking requests. These source pieces do not demonstrate a working validation round trip or activation of GUI PreWorld/late-update/replay scheduling, resource policy or removal of PC profile stand-ins.

The existing type-owner, typed-payload cast and `0xFFFF0000u` SatNav repairs retain the prior source findings and limits. The original hosted compile FAIL and original white-outline native review remain valid historical results. SatNav site 0006 is still withheld from final parity/campaign credit pending checking the repaired colour and outstanding visual parity. No native capture or behaviour check was performed here.

## Exact accepted postimages and integrity

| B5 source path | Postimage bytes | Full raw SHA-256 | Source verdict |
| --- | ---: | --- | --- |
| src/GameSource/Gui/BrnGuiModule.cpp | 288141 | `e22865108f339e0bb3aa5af167e986981c19af011f2a084ebad151cdb6eed618` | pass |
| src/GameSource/Gui/BrnGuiModule.h | 49006 | `8c642127bbbf87731d87d1b0f70b63cbd083ecffd8c35016b228f3d31742a255` | pass |
| src/GameSource/Gui/BrnGuiSatNavDebugComponent.cpp | 15708 | `b40b11913e4c8b214aab61ea9648a21721a665a2d7d8b3a50c3231ac89d8ab8a` | pass |
| src/GameSource/Gui/BrnGuiDemangledEventTypes.h | 97636 | `ff1cf6023db573b5cb63ed47753c490240755ff70f42c373f3312dbec7ccb7c3` | pass |
| src/GameSource/Gui/BrnGuiEventTypeDefs.h | 189964 | `597605770de1b809644be80dd3018024e7ff8ffbb2d45d585162c270a81c7e49` | pass |
| src/GameSource/Game/GameBridgeWorldToGui.cpp | 63089 | `2afc4bcb4a306bff599ba34f6df2404ff7881e2eb0778b8e7843a88b315f5e57` | pass |

The composition's integrity-manifest SHA-256 is `05b10e480d59dcf7bc6d5bb9c5504b6a286379c1be30f047af7e63db5d1496b8`. All 26 covered files, six complete preimage/base Git blob bindings, six full unified diffs, all three source-input seals and the full retained failed review were verified. The handler author's patch matches both complete author pre/post diffs at its original four-line context. Every supplied pinned source/excerpt/export was checked against the exact base or original ARTIST/DecFIGS file; excerpt line contents were verified too.

`INPUTS.json` records every frozen packet file and its full raw hash/size, the retained failed review, all consulted original evidence and exact-base dependency blobs, including inherited prior dependency inputs. `CHECKS.json` records per-increment verdicts, all six source bindings, composition checks and the explicit absence of execution/active-wiring credit. `INTEGRITY.sha256` seals REPORT.md, INPUTS.json and CHECKS.json; `SEAL.sha256` holds the detached integrity-manifest hash.

Only this new sibling review directory was written. No compilation, preprocessor, fixture, Stage/Run/game/harness/watchdog, CI, IDA, production/source/index mutation, commit or subagent was used. All frozen inputs and prior reports remain unchanged. Unchanged large-file legacy code is not newly certified as complete original behaviour by this bounded source-increment approval.
