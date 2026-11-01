# GUI audio trigger route: original evidence and bounded repair

Initial proposal status: **confirmed source divergences; proposed patch supplied for parent application**. Subsequent focused regression results are recorded below; the parent applied the patch in its clean shipping worktree. The parent supplied b5 pin `ca80277748eb098822a035093cff9d306d079e2a`. No Git commands, production writes, builds, native launches, profile operations, or ledger/status changes were performed. Normal exe052 and save4e were not accessed. Source hashes are in `evidence/manifest.json`; evidence is local and directly inspected.

## Findings and concrete repair

`proposed.patch` changes only `src/GameSource/Gui/BrnGuiModule.cpp`, inside `GuiModule::FlaptSoundTriggerCallback`:

1. Correct authored strings `ON_LEFT_SWEEP` -> `ON_LEFTSWEEP` and `ON_RIGHT_SWEEP` -> `ON_RIGHTSWEEP`.
2. Project the already-constructed legacy carrier through existing `GuiAudioTriggerWirePayload457`, then call `mpOutputBuffer->AddGuiOutEvent(lPayload)`.

The current callback posts **201 / 112 bytes**; ARTIST posts **457 / 100 bytes**. Event201 is a PC accommodation in the current audio type, not this event's original identity. It also identifies the unrelated 8-byte HideDriveThru input record. Do not globally remap event201.

For twelve ordinary authored action names the compatibility sound consumer already delivers equivalent named fields to sound message6. Therefore the wrong producer ID/size alone does **not** establish that ordinary GUI sounds are inaudible. The concrete behavior error is that genuine original sweep names at indices11/13 currently fall through to action14, altering the action used by PresentationEffect and the trigger log label. Both corrections are in the attached patch.

The existing non-const queue accessor already checks the write lock (`CgsGuiModuleIO_OutputBuffer.cpp:77..80`). The replacement preserves that behavior through the canonical AddGuiOutEvent template. A missing lock assertion was an initial hypothesis and is **not** a finding.

## ARTIST behavior and ABI pins

All named function exports, including complete assembly, are retained under `evidence/ARTIST_*.json`.

| Original evidence | Exact observation |
| --- | --- |
| Callback `825112B0`, `825112BC..D0` | r3=user data, r4=component, r5=SWF/movie, r6=action text, r7=label. Five pointer parameters; no hidden member-this parameter. |
| Callback `825113BC..D0` | Calls string constructor `sub_824FB9A8` as `(event, component, actionText, label, movie)` in r3..r7. |
| Callback `825113D4..DC` | Calls `OutputBuffer::AddGuiOutEvent<GuiAudioTriggerEvent>` @`8250BE70`. |
| String constructor `824FB9A8`, `824FB9F0..BA50` | Searches fourteen pointers from `82F277A8` up to exclusive `82F277E0`; defaults action14, breaks at first exact string match. |
| String constructor `824FBA54..68` | Calls enum constructor `(event, action, component, label, movie)` in r3..r7. Hex-Rays incorrectly invents packed int64 parameters here; assembly arbitrates. |
| Enum constructor `824F6350`, `824F63A8..EC` | Three SPrintf calls of capacity32; component at+0, label at+36, movie at+68; terminators+31/+67/+99; s32 action store+32. Exactly100 pointer-free bytes. |
| AddGuiOutEvent `8250BE84..90` | Tests write-lock bit3. Failed assertion reports `Not locked for writing\n`; continues if assert handler returns. |
| AddGuiOutEvent `8250BF0C..1C` | r6=100, r5=457, r4=raw event pointer, r3=output+0x814; calls VariableEventQueue<18432,16>::AddEvent. No channel40 wrapper here. |
| StateInterface OutputGuiEvent `82436890` | Different publication boundary: copies raw100 and wraps `{100,457,12,payload}`; posts112 bytes with outer channel40. This is **not** the callback's module-output API. |
| Game bridge `823C0A58`, `823C0AA0..D8` | Reads output queue and stores the same queue pointer in RootInputBuffer::SetGuiEventQueue. No conversion to201. |
| Sound ProcessGuiEvents `826ED6C8`, `826EE114..170` | Case457 copies100 bytes and builds sound event6, manager0/instance0/effect0/object. No original case201 for audio. |
| Sound typed AddEvent `826DEE00`, `826DEE9C..B8` | Selects serialized queue size116 and console object-pointer adjustment+4. Keep the host queue/message representation's own pointer semantics; do not blindly apply the console bias to a host pointer. |
| PresentationEffect::Notify `826FF840`, `826FF880..884` | Reads message event id6; original payload body is passed at message+16, action is read at+48. This corroborates the100-byte body reaching the effect. |

Direct data read: `tools/re/x360rd.py`, backed by `D:/Reverse/IDA_Files/artist_i64.raw`. Calibration against independent exported instructions: bytes at8250BF0C are `38c00064 38a001c9` = `li r6,100; li r5,457`. The table pointer slots, string addresses, pointer bytes and NUL-terminated string bytes are retained in `evidence/ARTIST_action_tables.json`.

| Index | Original action string | Current callback |
| --- | --- | --- |
| 0 | ON_ENTER | same |
| 1 | ON_LEAVE | same |
| 2 | ON_FOCUS | same |
| 3 | ON_LOSE_FOCUS | same |
| 4 | ON_ACCEPT | same |
| 5 | ON_CANCEL | same |
| 6 | ON_TICK | same |
| 7 | ON_CHANGE | same |
| 8 | ON_UP | same |
| 9 | ON_DOWN | same |
| 10 | ON_LEFT | same |
| 11 | ON_LEFTSWEEP | ON_LEFT_SWEEP (wrong) |
| 12 | ON_RIGHT | same |
| 13 | ON_RIGHTSWEEP | ON_RIGHT_SWEEP (wrong) |

## DecFIGS declaration corroboration

`references/DecFIGS/dwarfdump/GameSource/Gui/Events/BrnGuiAudioEvent.h:1..28` declares `GuiAudioTriggerEvent : GuiEvent<452>`, component[32], int32 action, label[32], movie[32], and three Construct overloads: four string arguments; action+three strings; two strings. The matching GuiEvent<452> declaration at `.../CgsGuiEvent.h:4468..4473` has GetEventType and no stored12-byte header. DecFIGS's ID452 is build-specific; ARTIST457 wins for target identity. Neither build supports201 as audio identity.

`references/DecFIGS/dwarfdump/GameSource/Gui/BrnGuiModule.h:725` names the five-pointer callback shape. ARTIST register usage pins its order; C++ void matches DWARF (Hex-Rays's int return is residual r3 after the callee).

## Current full route and actual affected callers

1. `BrnGuiModule.cpp:541..542` registers this callback on the existing FLApt manager. This investigation does not modify Apt internals or its x64-authoritative runtime.
2. `DispatchInboundGuiEvents`, case22 at1930..1936, also calls this callback with type-name/action/label and ViewModule::GetMovieNameByLevel(layer). The proposed patch therefore covers both current entry paths.
3. The callback still calls the real `GuiAudioTriggerEvent::Construct` exactly once. It preserves constructor formatting, termination, action logging, invalid-action fallback14, and invalid-action diagnostic. It publishes through the existing module output queue.
4. BrnGameModule::BridgeGuiToSound (`GameBridgeGUIToX_Sound.cpp:27..40`) obtains the actual GUI output queue and calls RootInputBuffer::SetGuiEventQueue. That setter stores a pointer (`BrnRootSoundModuleIO.cpp:354..358`); its getter checks the read lock (`191..195`).
5. SoundLogicModule::Update (`BrnSoundLogicModule.cpp:1439..1448`) passes that queue to ProcessGuiEvents, then calls the sound base Module::Update.
6. Current ProcessGuiEvents case201/457 (`533..570`) converts the legacy112-byte201 carrier or copies a raw100-byte457 body into `Message<GuiAudioTriggerWirePayload457>`; sound id6, total116 bytes, destination0/0/0/object. The case201 size guard rejects unrelated8-byte HideDriveThru records. `GetGuiPayload` handles existing boxed records; the candidate callback directly supplies raw100.
7. CgsSound::Logic::Module::Update processes mMessageQueue (`CgsSoundLogicModule.cpp:186`). ProcessMessageQueue dispatches to Environment::Notify; the environment selects state manager0/instance0/effect0/object. PresentationEffect::Notify (`BrnPresentationEffect.cpp:265..298`) consumes id6, selects component when label is `uninitialised`, otherwise label, hashes that plus movie, then resolves action and calls Play on a valid entry.

Original AddGuiOutEvent has two caller functions in its xrefs: FlaptSoundTriggerCallback and GuiModule::Update. Update has two specific calls, at82528374 (input1, the navigation-derived constructor824F64B0) and82528468 (input22, the same string constructor824FB9A8). The current case22 funnels through this callback and is covered. Current BrnGuiModule.cpp has only this one GuiAudioTriggerEvent construction/publication site. No broader input1/navigation restoration is asserted by this patch.

The shared StateInterface specialization in BrnGuiEventTypeDefs.h:3257..3273 already projects the legacy carrier into raw457 and wraps it on channel40. It remains untouched. Numerous GUI states have established wrappers depending on the legacy112-byte type, including hard size assertions. Changing the global class base from201 to457 alone would leave the wrong112-byte body; removing its header would require a much larger caller migration. Neither belongs in this bounded callback repair.

ABI after the candidate:

| Representation | ID / outer ID | Size | component / action / label / movie offsets |
| --- | --- | --- | --- |
| Existing shared legacy carrier | 201 | 112 | 12 / 44 / 48 / 80 |
| Callback's new queue body | 457 | 100 | 0 / 32 / 36 / 68 |
| Existing StateInterface wrapper | 457 / channel40 | 112 | payload+12 |
| Current host sound message | 6 | 116 | 16 / 48 / 52 / 84 |

## Focused regression draft and existing runner

At the initial source snapshot, no existing test under b5-decomp/tests referenced GuiAudioTriggerEvent or GuiAudioTriggerWirePayload457. The nearest focused **existing runner** is `b5-decomp/tests/run_gui_menu_music_wire.py` with `GuiMenuMusicWire.cpp`. It extracts actual GUI-to-sound case23/helper bodies, shadows selected-source headers, retains receipts, and supports source-root/revision plus a negative control. Its existing functionality does **not** test this callback; running it unchanged cannot certify this fix.

Reuse `tests/fxgs_common.py::definition` and `compile_and_run` (actual production extraction + canonical MSVC flags + numeric receipts), following that runner's retained-output pattern. `run_gui_original_producer.py` is also an existing example for extracting a BrnGui::GuiModule member into a fixture with real typed IO, real IOBuffer bodies, and observed external subsystem boundaries. A small new callback fixture/runner is needed, using these helpers; no general framework is needed.

**Actual draft cases:** `evidence/regression_cases.json` contains19 scenarios,14 independently pinned original action names plus unknown-action fallback, unlocked-output assertion, raw457->sound6, legacy201 compatibility, and HideDriveThru201 rejection. Inputs use distinct exactly31-character component/label/movie names so all96 character bytes are deterministically written by the actual constructor. Tests compare offsets0/32/36/68, ID457, size100, one queue record, and sound destination/payload; they must not build the expected list from the implementation under test.

Extract these exact production bodies/declarations for the fixture:

- `GuiModule::FlaptSoundTriggerCallback` from selected BrnGuiModule.cpp; narrow fixture GuiModule only supplies the actual OutputBuffer pointer and static callback declaration.
- `GuiAudioTriggerEvent::Construct` plus actual KAPC_GUI_AUDIO_ACTION_NAMES table from selected BrnGuiEventTypeDefs.cpp. Use the actual event header and actual OutputBuffer template, not a mock AddGuiOutEvent or reconstructed copy of the callback.
- Real IOBuffer lock bodies and OutputBuffer::Construct/Clear/GetOutEventQueue/GetOutEventQueueNonConst, with the real VariableEventQueue header. Capture asserts with the established returning test handler. Keep valid calls write-locked; read the resulting queue under a read lock. The unlocked case must assert once and may still enqueue when the fixture assert handler returns (original behavior).
- For the sound continuation, extract actual case201/457 plus GetGuiPayload and QueueSoundMessage, using the real Message header/queue. The current compatibility carrier and HideDriveThru size guard must remain unchanged.

Run the **unchanged ca802 source** as the negative control: all14 queue ID/size checks must fail versus the original oracle, while action11 and13 must additionally fail with actual14. With the candidate, all14 must produce457/100 and their original0..13 values. The lock assertion passes on both old and candidate; explicitly report it as an invariant, not evidence that the old code lacked a lock check. Ordinary old-source named payloads already reaching sound6 are expected, not evidence against the publication discrepancy.

The data fixture is architecture-aware: ARTIST's table and instruction bytes are big-endian; the PC s32 action byte representation is host little-endian, while semantic field offsets and100-byte size are unchanged. Do not compare the entire big-endian console payload to host bytes without converting the scalar.

The initial proposal pass did not compile or execute cases. The subsequently authorized focused regression now executes the callback, real queues and downstream production consumer bodies as recorded below. Normal native UI triggers remain to validate after implementation. Debug flag collection/registration by itself is not behavior proof. Native follow-up must use the actual normal UI actions with executable identity/trace evidence; this report neither injects production events nor credits Sound debug#0105 as complete.


## Executed focused regression follow-up

On subsequent parent authorization, implemented `tests/run_gui_audio_trigger.py` and `tests/GuiAudioTrigger.cpp` under this scratch packet and compiled/executed them with existing fxgs_common/MSVC plumbing. Final candidate result: **323 checks,0 failures** in `tests/runs/candidate01`; final unchanged-ca802 counterfactual: **323 checks,112 expected failures** in `tests/runs/baseline04`. Both compile and execute successfully. The baseline is accepted only if its exact112 original-oracle failures and all14 observed201/112/action values match.

The candidate emits457/100 with all fourteen original0..13 actions. The baseline emits201/112 and maps original sweep names11/13 to14, including through actual PresentationEffect::Notify. Both retain lock assertions and201 compatibility/HideDriveThru rejection. Added actual string truncation/component-fallback cases and observed Resolve/Play guard cases. Only PresentationEffect Resolve/Play/log destinations are observed test boundaries; no asset-resolution or audible/native proof is claimed.

`tests/README.md` gives commands and final receipts. `tests/source_evidence_manifest.json` pins selected source/header closures, extracted bodies, tests, oracle and executables. Comparing all selected inputs between baseline and candidate finds exactly one text-changing production file: BrnGuiModule.cpp; five selected headers have line-ending-only byte differences, explicitly recorded. No production files were written by this child; all originally inspected shared source hashes remain unchanged.
