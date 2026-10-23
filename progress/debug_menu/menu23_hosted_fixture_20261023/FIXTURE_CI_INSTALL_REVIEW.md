# Fresh review: Menu23 delta04 and CompletedGame event 356

Date: 2026-10-24
Review mode: static source and packet review. No C++ compilation, fixture execution, hosted CI, game, or runtime check was performed.

## FINAL_DELTA04_VERDICT: pass

The delta04 fixture and paired hosted-CI proposal are internally consistent for the requested source-level wire contract, once the exact source-install tree is applied before CI dispatch. The source-install tree is a proposed Git tree, not yet installed in the working checkout.

The runner extracts the selected revision's actual `ProcessGuiEvents` case 23, wire helpers, queue/message helpers, and BootLegal type-155 declaration. The candidate covers raw 8-byte type-23 bodies, complete 20-byte type-23 records, and complete type-155 records translated to queue key 23, each with all four bool pairs. The unchanged B595 control uses the old case and requires all four raw-body pairs to mismatch while the two complete-record compatibility forms pass. Its negative fixture passes a real 20-byte `GuiEventPlayMusicOnMenuStream` object with declared event size 8; the old reads at +12/+16/+17 remain inside that object and its bool fields contain valid representations. This is a deterministic witness of the old numeric reads, with no out-of-bounds access or invalid `bool` value.

The check arithmetic matches the fixture: candidate 3 shapes × 4 flag pairs × 18 checks + one final assertion check = 217; control 8 full-record cases × 18 + 4 raw negative cases × 11 + one final assertion check = 189. The CI checks exact numeric receipts, both process exit codes, the single summary line, zero failures, 12 field observations per variant, executable hashes, and the four expected B595 mismatches. Delta04 makes compile/execution failure return 2 and numeric failure return 1; it also verifies that `fxgs_common`'s parsed numeric result matches the helper's return tuple and requires retained process exit code 0 before reporting pass. The hosted group is optional, preserves the existing workflow groups and Jobs=4, pins the harness and current production/header inputs, fetches exact B595 `b595d61d2440ca94d61aa8fa610ab0bf6048cc66`, and retains fixture artifacts/failure state.

Historical outcomes remain distinct: `luna02` fails review because it could pass a zero-failure summary while ignoring a nonzero process exit. `delta03` fixes that false-pass but has a compile/execution exit-code contract mismatch. Delta04 repairs the latter; its final verdict above is pass. The fixture and CI only cover the extracted Menu23 consumer. They do not execute the channel-40 GUI drain, measure playback timing, establish audible playback, or earn runtime/verified-site credit.

The supplied installation tree `2826d79ed9e557e73913293ae7d77cfd1c0b2b29` differs from source base `b9c0e692bc9d8f232b9986923acf07aff26c0639` in exactly three paths: it adds `tests/run_gui_menu_music_wire.py`, adds `tests/GuiMenuMusicWire.cpp`, and updates `BrnCompletedGame.cpp` with the separately reviewed event-356 producer delta. Recomputed LF hashes of all three tree entries match the supplied packets byte-for-byte after newline normalization. The fixture additions therefore exist in the proposed source tree before CI dispatch as required; no claim is made that this tree has been committed or installed.

## EVENT356_VERDICT: pass

ARTIST `0x824937E0` is decisive: it copies one payload byte from the caller, writes record header `{1,356,12}`, and invokes `VariableEventQueue<65536,16>::AddEvent` on channel 40 with size 16. ARTIST callers `0x824D2078` and `0x824D2978` both set that byte to 1 before publication. The second caller then separately posts event 469 with payload byte 0. The proposal wraps only the event-356 payload at the two corresponding sites, asserts payload size 1, offset 12, total record size 16, and leaves the 469 sibling block unchanged. DecFIGS corroborates the typed one-byte event shape without overriding ARTIST's X360 id or wire contract.

The receive path is active in exact b9c. `BrnScreenFlow.cpp` constructs `CompletedGame`, maps it to `PE_COMPLETED`, and its flow update is called from `GuiModule::Update`. The active typed Update calls `mScreenFlow.Update()` at `BrnGuiModule.cpp:4377`, runs the autosave tail at `4007`, clears the per-update force member at `4119`, and drains `E_GUIFLOW_SCREEN` at `4414`. `DrainFlowOutputQueue` maps that flow to `mScreenFlow.GetOutputEventQueue()` at `3196`, unwraps channel-40 records, and for event 356 reads the payload byte and sets both the force and pending latch at `3426–3430`. Since the drain follows the tail and its force reset, those flags are consumed by the next Update's autosave tail. This confirms a real producer-to-existing-latch integration route and avoids conflating it with the separate inactive output-buffer hook. It does not prove that the profile save completes in a running game.

The proposed source hunk is limited to `BrnCompletedGame.cpp`; exact preimage, patch, and postimage bindings match the packet and base. `git diff --check` returned clean for the proposed source delta and combined source-install tree. This remains a source review only; no compilation or runtime validation was performed.

## Binding

See `BINDING.json` for exact packet, evidence, pre/post-image, workflow, and tree hashes.
