# Canonical GUI audio-trigger family recovery

**Status:** sealed source-only proposal for the exact `b5-decomp` source tree at `4c7c6ba2f97533315d5663d22499042cb007df31`. It is not applied to production files. The sibling callback-only packet `gui_sound_trigger_restore_20261024_4c7` remains unchanged; this packet independently contains that producer under the corrected family type.

## Recovered contract

ARTIST `BrnGuiAudioTriggerEvent::Construct @0x824F6350` writes a payload at offsets `0, 32, 36, 68`: `component[32]`, `action:s32`, `label[32]`, `movie[32]`. The total is 100 bytes, with four-byte alignment. Its 51 ARTIST `xrefs_to` are retained in `evidence/artist/0x824F6350.json`.

ARTIST `StateInterface::OutputGuiEvent<GuiAudioTriggerEvent> @0x82436890` emits `{100,457,12}` followed by the payload, then calls `AddEvent` on channel 40 with a 112-byte record. The raw assembly export is `evidence/artist/0x82436890.json`; its 32 `xrefs_to` are function xrefs, not a count of current C++ call statements. The proposal pins the payload layout and the 112-byte wrapper in C++ static assertions.

DecFIGS `BrnGuiAudioEvent.h:43` declares `GuiAudioTriggerEvent` on `GuiEvent<452>`. Its `CgsGuiEvent.h:58` declaration makes `GuiEvent<452>` an empty `Event` tag. The proposal adds that narrow empty-tag specialization in the PC `CgsGuiEvent.h`, then derives the 100-byte payload from it. ARTIST independently pins the runtime output id as 457, so the derived payload hides the tag's `GetEventType` with `GetEventType()==457`. The payload starts at offset zero; no 12-byte header is embedded in it.

The `StateInterface::OutputGuiEvent` primary template is left unchanged. An explicit specialization for this type constructs `GuiEventWrapper<GuiAudioTriggerEvent,40>`, which gives the exact `{100,457,12}+100` record. The 65 remaining generic explicit-instantiation declarations now spell their actual `void` return type; ARTIST's mangled `QAAX` signatures and the declared C++ method both say `void`.

The separate module-output path also matches ARTIST after the type repair. `CgsGuiModuleIO::OutputBuffer::AddGuiOutEvent @0x8250BE70` appends the event's type and `sizeof(T)` directly, so the canonical event becomes raw id457 / 100 bytes on that queue. ARTIST `GuiModule::FlaptSoundTriggerCallback @0x825112B0` and the CodeTicker producers use this raw module-output representation; they do not receive an extra channel-40 wrapper. The callback xrefs, action mapper, view callback registration, and sound bridge exports are retained under `evidence/artist/`.

## Producer and consumer changes

All 39 postimage `OutputGuiEvent<GuiAudioTriggerEvent>` call expressions across 29 current TUs use the type-specific specialization. The base had 9 such direct statements across 6 TUs; the proposal converts 30 existing hand-built state-output records to the same typed publisher. These are C++ producer statements, not debug-menu registration sites and not a claim of 39 original ARTIST function xrefs.

`SoundLogicModule::ProcessGuiEvents @0x826ED6C8` routes id457 into sound message 6 and copies exactly 100 payload bytes. With the canonical type, `Message<GuiAudioTriggerEvent>` is 116 bytes (16-byte sound header + 100-byte body); a static assertion pins that size. `PresentationEffect::Notify @0x826FF840` consumes that same message and reads the four fields. Its source and the original DecFIGS declarations are retained in `evidence/pc_4c7/` and `evidence/decfigs/`.

The proposal preserves event 201 as the distinct eight-byte `GuiEventHideDriveThru` consumed by `GuiCache::RecEvent`. The sound decoder keeps only a bounded compatibility case for the former full audio record `{0,201,12}+100` (112 bytes with those exact header words). An event201/8 HideDriveThru record is rejected by the sound audio arm. New canonical audio output uses457 and does not enter the GUI cache's event-201 path.

## Exact source package

- `pre/` and `post/` contain 54 source snapshots. Every preimage was byte-compared with `git show 4c7c6ba2f97533315d5663d22499042cb007df31:<path>`.
- `bindings.json` maps each snapshot to its source path, base blob, and exact pre/post SHA-256.
- `patch/source.patch` contains the 35 changed files, including the new `GuiEvent<452>` tag specialization. It contains source hunks only.
- `evidence/artist/` retains the raw ARTIST JSON exports used for producer, wrapper, callback, bridge, and sink anchors. `evidence/decfigs/` retains the DWARF declaration snapshots. `evidence/pc_4c7/` retains the exact source consumers and surrounding routes.

No local C++ compile, test, CI, native run, game input, or Git mutation was performed. Root owns all build and runtime gates. The physical `b5-decomp` checkout was not edited by this proposal.
