# Exact receiver and hosted failure evidence

## Candidate receiver at c18

`src/GameSource/Gui/BrnGuiModule.h:486` declares:

```cpp
CgsGui::CgsGuiModuleIO::OutputBuffer* mpOutputBuffer;
```

`src/GameSource/Gui/BrnGuiModule.cpp:2603-2652` extracts the callback; after constructing its `GuiAudioTriggerEvent`, the callback publishes with:

```cpp
lpThis->mpOutputBuffer->AddGuiOutEvent(lAudio);
```

`src/GameShared/GameClasses/Gui/CgsGuiModuleIO.h:123` declares the actual inline receiver method:

```cpp
template <class T>
int AddGuiOutEvent(T& lrEvent)
{
    CGS_ASSERT(IsBufferLockedForWriting(), "Not locked for writing\n");
    return mOutEvents.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lrEvent),
                               lrEvent.GetEventType(), static_cast<s32>(sizeof(T)))
               ? 1
               : 0;
}
```

The candidate output buffer lifecycle is implemented in `CgsGuiModuleIO_OutputBuffer.cpp` (`Construct`, `Clear`), and the inherited status lock operations are implemented in `CgsIOBuffer.cpp`. Their exact Git blobs and hashes are bound in `BINDINGS.json`.

## Baseline and ID-only receivers

At baseline `4c7c6ba2f97533315d5663d22499042cb007df31`, `BrnGuiModule.h:454` stores `VariableEventQueue<18432,16>* mpOutputBuffer`; its `FlaptSoundTriggerCallback` calls the queue’s raw `AddEvent(event, type, size)` path. That callback remains attached to the raw queue in baseline and as the ID-only legacy body. ID-only’s candidate callback body remains compiled separately against `OutputBuffer`.

## Hosted evidence

The retained log for run `40136323622` reports the `AddGuiOutEvent` member errors in candidate line 147 and ID-only line 198. Baseline executed and produced `EXPECTED_BASELINE_NEGATIVE id=201 size=112 cache201=1 message=128 assertions=0` with three numeric failures. The log’s exact size and SHA-256 are in `BINDINGS.json`; baseline is evidence for its existing expected failure only, not a candidate result.
