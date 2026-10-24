# Provider closure audit

## Four-string GUI audio constructor

`BrnGui::GuiModule::FlaptSoundTriggerCallback` calls the candidate `GuiAudioTriggerEvent::Construct(const char*, const char*, const char*, const char*)`. The runner currently extracts the first overload by matching only `void GuiAudioTriggerEvent::Construct(`, which selects the `s32` overload earlier in `BrnGuiEventTypeDefs.cpp`. This is why the fixture links neither candidate nor ID-only even though production source has the required body.

The postimage adds a second, exact extraction anchored on `void GuiAudioTriggerEvent::Construct(const char* lpComponentName,`. Candidate and ID-only projections include it. The body uses `std::strcmp`, the existing enum overload, and existing `CgsCore::SPrintf`, assert-count hooks, logging globals, and action-name data. Those dependencies are already present in the current fixture. The baseline mode is unchanged because its older callback uses the enum overload.

## `MessageBufferPC` constructor

`CgsGuiModuleIO_OutputBuffer.cpp:89-109` defines the actual `OutputBuffer::AddGuiOutEvents(GuiEventQueueTiny*)` body. Its two original assertion-formatting branches instantiate `CgsDev::Assert::MessageBufferPC`; the current fixture compiles that provider TU but had no definition for the constructor.

`CgsAssert.cpp:122` defines the exact constructor. It directly reads only `gbDeferredAssertPC`, `gpcMessageBuffer`, and `giMessageBufferSize`, plus its own `macBuffer` and the `KI_MESSAGEBUFFERSIZE` constant from `CgsAssert.h`; it calls no function. `CgsAssert.cpp:33,35,60` owns the corresponding backing buffer, pointer, size and thread-local deferred flag. The candidate projection copies those exact source fragments and the exact method body into the generated fixture translation unit. This supplies the real missing symbol without linking the unrelated assert manager or replacing the pre-existing assertion-counting hooks. The hooks and the `gAssertionCount == 0` gate remain unchanged; any assertion still fails the candidate witness.

## Preserved controls and limits

`tests/GuiAudioTriggerWire.cpp` is byte-identical, including all 50 `Check(...)` expression lines, candidate pass criteria, baseline numeric failure marker, ID-only numeric failure marker, and the zero-assertion check. The CI proposal changes only the LF-normalized runner input pin. The full OutputBuffer and CgsIOBuffer providers remain the actual candidate sources.

This is a static source-extraction correction only. Link success and all three numeric outcomes remain for Root's hosted run; this packet claims neither audible playback nor broader GUI runtime closure.
