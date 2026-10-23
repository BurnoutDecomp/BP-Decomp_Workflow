# Completion-audio event 468 channel-40 producer repair

Status: source-only proposal against B5 commit 7e455d8854a32df1ca1934a54cc279c1e268a103. No production/shared source, refs, or index were changed; no build, compile, or runtime validation was run.

Two active calls in BrnCompletedGame.cpp create GuiEventAudioGenericSequence from the existing GoldAward and PlatinumAward name hashes, then use the current generic OutputGuiEvent. At this base the template queues the four-byte event under raw channel 468. GuiModule::DrainFlowOutputQueue has no case468 arm, so it falls through the default and drops the post before the existing SoundLogicModule::ProcessGuiEvents case468.

ARTIST 0x824C2DA8 is authoritative: it copies one DWORD and emits {4,468,12}+4 on channel40 with a 16-byte record. The proposal wraps the existing four-byte event payload with GuiEventWrapper<GuiEventAudioGenericSequence,40> at the two caller sites. Function-local static assertions pin payload size 4, payload offset 12, and total record size 16. The existing hashes and their order remain unchanged.

DecFIGS gives the event a Name member and the same channel-40 wrapper form, but labels the type id 463. That id differs from ARTIST's emitted 468, so the proposal uses ARTIST for the id and the PC type's existing GetEventType() result.

## Site mapping

- CompletedGame::UpdateEliteLicensePresentation (ARTIST 0x824D2078): posts MakeHash("GoldAward").
- CompletedGame::UpdateOneHundredPercentPartTwoPresentation (ARTIST 0x824D2978): posts MakeHash("PlatinumAward").

The related event468 calls in OfflineInstantResults.cpp and OfflineRivalShutdown.cpp already explicitly wrap their payloads on channel40 and are not changed. This packet shares BrnCompletedGame.cpp with a separate event469 packet but contains independent callsite/function-local hunks and preserves its exact 7e455d preimage for composition.

## Evidence

- evidence/ARTIST/ contains exact template and caller exports; artist_full_function_bindings.json includes full pseudocode, full assembly, and xrefs.
- evidence/DecFIGS/type_wrapper_and_instantiation_excerpt.txt records the payload member and wrapper along with the id discrepancy.
- evidence/current_source/event468_path.txt records the generic direct publisher, channel-40 re-key, absent raw channel468 dispatch arm, and existing sound consumer.
- preimage/ and postimage/ contain the exact base file and proposal; patch.diff and site_map.tsv show the source-only edits; bindings.json records blob and evidence hashes.

Validation performed: confirmed both current generic callsites and their hash sources, ARTIST {4,468,12}+4 bytes/size/channel, current drain default, and existing sound receiver. Compilation and runtime validation remain for the integrating root.
