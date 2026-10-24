# Native GUI Update leaf providers

This five-path source proposal closes two real audio methods and the small cache owners needed by the original ten-argument Update. It is bound to b5 source `656890624d6a3492c3341340da24bbb4e51fb414` and workflow `2f3ee0b4b02daf53350631a3b97e99fe750eb010`. Full preimages, postimages, Git blob IDs and SHA-256 values are in `BINDINGS.json`. No physical checkout supplies a source input.

The complete ten-argument Update is **not** included or represented as ready. Its separate authoring directory remains incomplete. This packet changes no GuiModule entry, caller, callback registration, base-module call, queue ownership, Apt layout, allocation or preparation stage.

## Concrete recovery

`GuiAudioTriggerEvent::Construct(component, action, label, movie)` is ARTIST `824FB9A8`. Assembly saves r3/r4/r5/r6/r7 as this/component/action/label/movie, asserts the action pointer at original line49, scans fourteen case-sensitive action tokens, retains sentinel14 on a miss, calls the existing canonical enum overload, and emits the original gated invalid-action diagnostic. The tokens match the retained exact656 callback's fourteen-token table; the new method uses that same original vocabulary. It does not substitute the differently cased 27-entry diagnostic-label table.

`GuiAudioTriggerEvent::Construct(event, movie)` is ARTIST `824F64B0`. The assembly, rather than the malformed five-argument pseudocode, pins this/r4/r5. It calls SPrintf with capacities31/31/32, writes explicit terminators only to component31 and label31, sets action7, and emits the exact original gated state-change diagnostic using the existing diagnostic label at index7. The original format-string arguments are preserved. No normalization or extra null fallback was added.

`GuiCache::IsGamePaused`, `IsImageExportInProgress`, `IsConnectedToNetwork`, `SetConnectedToNetwork`, `IsInGame` and `SetInGame` use the DecFIGS public declarations at original header877/922/930/1444/1453/1458. Their fields are fixed by the ARTIST readers/writers. `SetInGame` writes the one update-set owner at cache4B54; the retained PC `SetGameplayHudReady` helper continues to write its existing three bytes.

The real pause byte replaces one byte of the existing cache padding. Construct `82505A00` stores false. RecEvent `82510500..8251053C` asserts `lpPausedEvent` at original line1554, then copies the event's byte4 to cache4B48. That case is recovered before the pre-existing broad PC null guard so the original assertion continuation is preserved. No other RecEvent case changes.

The existing eight-byte `GuiGamePausedEvent` is moved from its demangled blob home to `BrnGuiEventTypeDefs.h` with the DecFIGS names `mbpad` and `mbGamePaused`, preserving field positions0/4 and wire id505. It retains the target's field-only payload; no generic twelve-byte GuiEvent prefix is inserted. The enum audio overload and 100-byte audio payload are unchanged.

## Provider and mount closure

Both modified C++ owners are already literal shipping inputs: `BrnGuiCache.cpp` at build_game_exe.bat4128 and `BrnGuiEventTypeDefs.cpp` at4145 in exact workflow2f3. The committed compile_exe.py remains the shipping driver. No CMake change, extra TU or second mount is required.

The selected SPrintf provider is the existing CgsStringUtils.cpp implementation; its declaration and variadic definition are bound. The `gbLogGuiAudioTriggers` definition remains in the existing CgsAptCommunicator.cpp. `gxMessageFilterFlags` and `gpDebugPrint` retain their CgsLog.cpp owners, while the existing StrStream operator definitions provide the original diagnostics. The assertion front-end declaration and its existing shipping implementation remain unchanged. These provider snapshots are evidence, not substitute fixture implementations.

## Self-review and limits

The postmortem follows ARTIST assembly first, then DecFIGS declaration shape. The two audio overloads preserve argument order, every store, capacities, action sentinel, case-sensitive matching and diagnostic gates. The pause case preserves the null assertion and byte store. The cache padding still occupies six bytes in total before the next unchanged member: four padding, pause, HD. Connected and in-game accessors bind the already existing field owners and introduce no mirror.

Static checks verify exact preimage Git blobs/hashes, all postimage hashes, unique canonical definitions, the unchanged enum-audio method, retained PC entry/callback bytes, the two original compilation mounts, pause field/event shape and the one-byte native in-game setter. They do not compile C++, import or evaluate a fixture, or certify runtime behavior.

The new audio overloads currently have no selected caller in656; the unfinished original Update will select them. The cache pause case is a real common consumer and will record a genuine event505 when received through the current path. That is the only newly completed effect in a currently callable body. No independent debug-control disposition is claimed.

Original UI latches `82FB5924/25` remain unresolved dependencies of the full Update. Root's separate bounded database-open attempt returned `Failed to open database` and yielded no state-byte values or xrefs. This packet derives neither zero initialization nor readiness from that failure. Full caller/temp/callback reconciliation and one-base-call adoption remain separate work.

No production edits, Git mutations, C++ compilation, tests, CI, game/input or IDB work was performed by this author. Root owns review, publication and execution.
