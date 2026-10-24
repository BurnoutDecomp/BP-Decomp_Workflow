# GUI audio fixture provider closure

Status: **fixture-only source-extraction proposal** bound to the exact current candidate and workflow. No production source, event behavior, assertion expression, numeric control, or test harness was changed. No local fixture, import, compiler, test, CI, game, or native run was performed.

## Hosted failure

Hosted run `40139390036` used B5 `a27ac7b9f6fc6a5c201b035ea2a28964776098b4` and workflow `515b98ecfae52963229c2ee5605a117c64861530`. The candidate and ID-only modes stopped at link with two missing source providers:

- `GuiAudioTriggerEvent::Construct(const char*, const char*, const char*, const char*)`, called by the exact current `GuiModule::FlaptSoundTriggerCallback`. The runner’s `definition(..., "void GuiAudioTriggerEvent::Construct(")` extracts only the earlier `s32` overload. The four-string overload is defined in the mounted `BrnGuiEventTypeDefs.cpp`; the candidate callback uses it. The baseline callback uses the older enum overload, which is why its numeric negative control still runs.
- `CgsDev::Assert::MessageBufferPC::MessageBufferPC()`, referenced by the real `OutputBuffer::AddGuiOutEvents(GuiEventQueueTiny*)` provider in `CgsGuiModuleIO_OutputBuffer.cpp`. The constructor and its direct backing state (`gacMessageBuffer`, `gpcMessageBuffer`, `giMessageBufferSize`, and `gbDeferredAssertPC`) are owned by `CgsAssert.cpp`.

## Proposed correction

The new runner projection extracts and hashes the exact four-string constructor from candidate `BrnGuiEventTypeDefs.cpp` and emits it beside the existing enum overload. ID-only compiles the same candidate overload for its candidate callback while leaving its baseline-derived `LegacyGuiAudioTriggerEventIdOnly` constructor and callback unchanged. Baseline mode remains on the enum overload and receives no candidate-only constructor.

For candidate mode only, the runner also extracts the exact `MessageBufferPC` constructor and its exact backing declarations from `CgsAssert.cpp` into the generated fixture translation unit. This resolves the real `OutputBuffer.cpp` reference without compiling the broader assert system and without replacing the harness’s existing assertion-counting hooks. The positive candidate still requires zero assertions; all existing assertion expressions and all `Check(...)` calls in `GuiAudioTriggerWire.cpp` remain byte-identical.

The workflow file changes only the LF-normalized SHA-256 pin for `tests/run_gui_audio_trigger_wire.py`. The harness and its expected control markers remain unchanged. The actual OutputBuffer/CgsIOBuffer source providers remain included in candidate mode; no queue shim, stub constructor, altered payload type, or weakened predicate is added.

## Static boundary

This closes the two observed fixture link references at source level. It does not certify link success or the three numeric outcomes; Root owns hosted review and execution. No audible playback or full GUI lifecycle claim follows from this fixture.
