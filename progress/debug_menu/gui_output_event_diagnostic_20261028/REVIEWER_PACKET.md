# Channel40 output contract: diagnostic-only proposal

Binding revision01: see [BINDING_CORRECTIONS.md](BINDING_CORRECTIONS.md) and provenance/ for the retained original receipt, byte-exact CRLF/LF relationship and unchanged compiled source/object. This revision changes packet metadata only; source proposal and patch are identical.


This packet proposes one narrow diagnostic, not a speculative route fix. Actual62166 outer event IDs remain unproven. The candidate records those IDs/sizes exactly at the existing postworld failed-contract boundary and retains the original assertion, loop progression and routing. One independent SOURCE review is required before Root chooses a private composition/native case.

Base b5 `99c668c13ed446691dd9b8dababdb676d4470b9e` / workflow `31f145bfa1a5a910bb86bca14c54771af59e3028`; public dev `d1585cfbb9a99db4ee6aa8c6b2848f399cc01ad2` is comparison context only. All writes/builds are in this task-owned private overlay. See SOURCE_DELTA.json for the exact one-path pre/post/patch hashes. No public dev, existing builder checkout, package, profile, refs, counts or canonical status was changed. Native62166 is immutable input and still has its original aggregate FAIL disposition.

## Recovered contract and current split

ARTIST OutputGuiEvent<GuiAudioEvent>824367D8 builds {size24,type456,offset16}+24 raw payload bytes, then calls AddEvent with **channel40,total40**. OutputGuiEvent<GuiEventPlayMusicOnMenuStream>82476C00 builds {size8,type23,offset12}+8 body bytes, then **channel40,total20**. Raw excerpts are in evidence/ARTIST. DecFIGS GuiEventWrapper<T,40> names size/type/offset/body and SetRawEvent/GetRawEvent; template OutputGuiEvent declarations/mangled QAAX spelling corroborate void return. No recovered prototype is changed by this diagnostic.

Original interpreter8285E1D0 gathers and clears observer output queues, switches on the outer queue channel34..42, and unboxes channel40 via the three wrapper words. Raw8285E568..57C reads offset+8,size+0,type+4 and queues the raw body. Its default branch8285E6E4..6EC tests preworld: true forwards the direct record unchanged; false reaches the original Begin/Fire/End assertion8285E770..784, then advances GetNextEvent. The current interpreter preserves that contract.

Current StateInterface::OutputGuiEvent instead copies T directly and uses T::GetEventType() as the outer channel. This can reach the postworld default assertion. A global wrapper substitution is not a safe bounded recovery: the current payload population contains both flat records and legacy GuiEvent<N>-derived carriers with embedded protocol words. Examples include the one-byte flat loading tag, canonical menu-music wrapper, BootLegal's local MusicOnMenuStreamEvent and GuiAudioTriggerEvent. Some legacy header size words are0, so treating every inherited carrier as an already valid wrapper would also be unsafe. The current source's population-count comments were not promoted as freshly audited counts.

## Bounded native/source trace

The immutable native62166 log has exactly three occurrences of the original failed-contract assertion. The first follows BootLegal stage0->1; the second follows stage7->8/controller acceptance; the third follows SaveLoadPC's bootup-read result. None of the retained assertion text/callstacks contains the event ID, record size or originating observer payload. See evidence/native/ASSERT_CONTEXTS.json and the copied failure receipt.

Static candidates were traced without declaring them actual IDs: BootLegal's start/stop menu-music calls invoke OutputGuiEvent on a local GuiEvent155-derived carrier; its audio calls and BootProfile::HandleControllerInput use GuiAudioTriggerEvent201, an existing112-byte legacy carrier. Their neighboring source is retained under evidence/source. The proper wire audio457 payload is a separate100-byte raw type in the same header. This demonstrates why a mere outer-channel or generic wrapper change can be incomplete or misroute a header. Temporal proximity does not prove which records were in the staging queue on the three actual assertions, and no live payload/ID capture was retained. The next exact failing IDs must be observed before selecting typed producer/body fixes.

## Exact proposed change

Only src/GameShared/GameClasses/Gui/Model/CgsEventInterpreterModule.cpp changes. Inside the existing default branch's `else` (preworldfalse), stack snprintf formats:

    [GUI_OUT_UNEXPECTED] outer_type=<actual signed queue type> bytes=<actual queue size> pre_world=0

The existing PC emergency log sink records that line immediately before the unchanged original CGS_ASSERT. It logs no payload bytes, inferred inner type, pointer dereference, guessed header or new route. A128-byte stack buffer exceeds the maximum formatted signed integer representation. The existing failed records are still rejected; no assertion is gated, cleared or suppressed. Both preworld direct forwarding and valid boxed channel40 behavior remain untouched. This is explicitly marked a PC-platform diagnostic leaf.

## Validation and boundaries

The actual whole changed TU compiles with pinned workflow canonical flags/includes and51 exact source/header inputs,0 diagnostics and0 shared physical source fallbacks. Exact patch application reproduces the raw postimage; PATCH_CHECK.log records it. No shipping link was run.

The focused source-coupled regression compiles the complete pre/post ProcessOutEvents source body (only its class qualifier is renamed for a field shell), actual unchanged StateInterface::OutputGuiEvent and constructors, real EventObserver, VariableEventQueue storage and actual interpreter OutputBuffer lifecycle. It creates two representative wrong outer channels through the existing production generic template: flat tag19/size1 and legacy canonical music23/size20, then one proper boxed channel40. These are controlled fixture inputs, not claimed actual62166 IDs.

Pre17/17 and post19/19 pass. Both preserve exactly two original failed-contract assertions, drain observer output identically, preserve preworld direct records and forward only the correct boxed record postworld. Only the postimage emits the exact two expected diagnostic lines. Thus the one-byte record is identified without any payload read, and valid channel40/preworld records produce no diagnostic. The unused registration APIs abort if reached; assertion/log frontends are capture infrastructure. Actual emergency-file durability, frontend coordination, full GUI scheduling and native IDs require Root's later owned run.

## Follow-on acceptance boundary

One fresh reviewer should approve or reject this diagnostic source proposal and its exact hashes. A later Root-owned diagnostic run can correlate each original assertion with the preceding GUI_OUT_UNEXPECTED outer ID/size. That run remains a diagnostic FAIL while the assertions persist; it must not be promoted as repaired behavior. Only then should a separate narrow source recovery reconcile the actual typed producers, flat payloads, channel40 wrapper and downstream consumers against ARTIST. No broad compatibility branch, new event routing or speculative payload conversion is proposed here.
