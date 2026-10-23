# 100-percent completion event channel-40 producer repair

Status: source-only proposal against B5 commit 7e455d8854a32df1ca1934a54cc279c1e268a103. No production source, ref, or index was changed; no C++ compile or runtime test was run.

The two active GuiEvent100PerCentComplete posts in BrnCompletedGame.cpp currently call the generic OutputGuiEvent template. At this base it queues the one-byte payload under its type id, 469. GuiModule::DrainFlowOutputQueue has no channel-469 arm, so the event hits the default and is discarded before the existing sound and game consumers.

ARTIST 0x824C31C8 is authoritative: it copies one byte and builds {1,469,12}+1, channel 40, total size 16. The caller assembly sets the first value to 1 to start the completion sequence and the second to 0 to finish it. The proposal uses the existing GuiEventWrapper<GuiEvent100PerCentComplete,40> for the one-byte current source type, with static assertions for payload size 1, payload offset 12, and total record size 16. It does not add a second wrapper around an event that already contains its own header; the source type in BrnGuiDemangledEventTypes.h is the raw one-byte payload.

Consumer audit: BrnGuiModule's existing channel-40 arm unwraps and re-keys a wrapper; SoundLogicModule::ProcessGuiEvents case469 handles the completion flag/menu stream; BrnGameModule case469 sets the start/finish sequence input. Those consumers already exist. The producer's current raw id469 route is what makes them unreachable for these two calls.

DecFIGS names GuiEvent100PerCentComplete with a one-byte bool member and a GuiEventOut wrapper, but assigns the type id 464. This differs from ARTIST's emitted id 469 and is not imported: ARTIST controls the event id and record bytes; DecFIGS is used only for the one-byte declaration shape and wrapper form.

## Exact source impact

Two call sites in one TU:
- CompletedGame::Update, ARTIST 0x824DAAD8, payload byte 1 (start).
- CompletedGame::UpdateOneHundredPercentPartTwoPresentation, ARTIST 0x824D2978, payload byte 0 (finish).

The names and values are preserved exactly. The patch changes only how those existing one-byte records are published. It does not change event values, dispatch code, output consumers, 508/509, menu event 23, scoreboard sources, or renderer/provider files.

## Evidence

- evidence/ARTIST/ contains exact exports for the publisher and both caller functions; artist_full_function_bindings.json carries full pseudocode, full assembly, and xrefs.
- evidence/DecFIGS/type_and_wrapper_excerpt.txt records the one-byte member/wrapper shape and the conflicting 464 id.
- evidence/current_source/event469_path.txt records the base generic publisher, channel-40 re-key, no-channel-469 drain default, and existing sound/game receiver cases.
- preimage/ and postimage/ contain the exact base file and proposal; patch.diff is the frozen source-only delta, site_map.tsv maps both edits, and bindings.json records blob ids and hashes.

Validation performed: confirmed both current calls and their values, ARTIST assembly bytes/caller xrefs, DecFIGS shape and ID divergence, current drain fallthrough, and existing typed consumers. Compile/runtime validation remains for the integrating root.
