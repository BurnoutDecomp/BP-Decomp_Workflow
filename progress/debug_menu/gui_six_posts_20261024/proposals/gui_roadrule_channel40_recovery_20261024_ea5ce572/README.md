# RoadRule channel-40 payload publisher proposal

Base: committed B5 source `ea5ce572baedd4ad8918f6d5bfcdfd756250d411` (parent `b9c0e692bc9d8f232b9986923acf07aff26c0639`). One owned source file, two active generic publisher sites. The exact preimage, postimage, diff, source line map, ARTIST exports, DecFIGS receiver signature, and blob/hash bindings are included.

## Recovered posts

Both calls in `BrnRoadRuleComponent.cpp` currently use raw `StateInterface::OutputGuiEvent`, which queues the type id as the outer queue key and passes the payload's `sizeof` unchanged. The existing flow-output drain recognizes channel 40, decodes the `{payload size, event id, payload offset}` header, rekeys the event, and forwards its payload. Raw keys 337 and 572 do not enter that channel-40 path, so both current posts are discarded before their present consumers. The proposal preserves the generic template and wraps the two existing payloads at the producer sites.

Event 337's `GuiEventRoadRuleFail` is a payload-only 48-byte record. Its first field is the 8-byte `CgsID`, so ARTIST's offset is 16; the total channel-40 record is 64 bytes: `{48,337,16}+48`. The proposal asserts the ARTIST/DWARF field offsets, 8-byte alignment, wrapper payload offset, and total size, then posts that wrapper to channel 40. The current HUD message analyzer has a concrete case 337; `HandleRoadRuleFailed` reads the road id, rule type, player/AI flags, and ruler name to construct the existing HUD message. DecFIGS `0x5933D4` corroborates the typed receiver signature `const GuiEventRoadRuleFail*`.

Event 572's `GuiEventRequestTraining` is a payload-only 4-byte training-type word. ARTIST's `SetUpcomingRoadAnimation` caller at `0x82438684` inlines the exact `{4,572,12,9}` AddEvent on channel 40; the matching template instantiation `0x82436840` also confirms a 16-byte channel-40 record. The proposal wraps the existing word into `{4,572,12}+4` and posts it on channel 40. Current `GameBridgeGUIToX_GameState` case 572 translates the word to game action 113.

The same RoadRule TU already contains a correct event-22 channel-40 wrapper at this base. It is preserved byte-for-byte in the proposal's preimage/postimage except for the two event 337/572 repairs and the explicit `CgsGuiEvent.h` include.

## Counts and limits

This patch changes two actual producer call sites in one source file. The two consumer paths are present in source; this proposal makes no runtime or gameplay claim. The event 337 payload type shape is consistent with its DecFIGS consumer signature and current DWARF-derived type home; ARTIST controls the X360 id, payload size, +16 aligned offset, and channel. Event 572's current type home carries the recovered training-type field; ARTIST controls id 572 and the original 4-byte wire record. No behavior, field values, or consumer logic is invented. No production source, Git ref/index, build, CI, native run, game, or input state was changed or tested.
