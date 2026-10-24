# Fresh source review: RoadRule channel-40 publishers

Date: 2026-10-24
Proposal base: `ea5ce572baedd4ad8918f6d5bfcdfd756250d411` (parent `b9c0e692bc9d8f232b9986923acf07aff26c0639`).

## VERDICT: pass

This passes as a source-only recovery of the two original channel-40 producer records in one TU. It does not establish complete event-337 HUD delivery, and it earns no runtime or gameplay credit.

For event 337, ARTIST `RoadRuleComponent::UpdateCurrentTime` (`0x8243F540`, call at `0x8243F840`) reaches `OutputGuiEvent<GuiEventRoadRuleFail>` (`0x82436950`). That instantiation emits channel 40, 64 bytes, with `{48,337,16}+48`. The patch preserves the existing `lFail` fields and replaces the generic PC helper call with the same `GuiEventWrapper<GuiEventRoadRuleFail,40>` record; its assertions bind the payload fields, 8-byte alignment, payload offset 16, and 64-byte total. DecFIGS `0x5933D4` confirms the typed analyzer receiver signature, and the current analyzer case reads this payload to build the road-rule HUD message.

The source path after publication is incomplete for event 337. `DrainFlowOutputQueue` accepts the channel-40 wrapper, unpacks it, adds the raw 337 payload to `mGuiOutQueue`, and fans it to the four registered flow/observer queues. The active `HudMessageAnalyzer::Update` instead reads `mpGuiEventInputBuffer->GetGuiEvents()`. `BrnGameModule` fills that input buffer from world/controller/GameState/director/network/game producers before GUI update, while its GUI output is copied to the separate output buffer and consumed by the GUI-to-game/director/network bridges. I found no PC route from this outgoing 337 record back into the analyzer input. The analyzer’s case 337 therefore remains unreachable through this proposal alone. A future complete HUD recovery needs evidence for that delivery path; this review does not authorize or invent one.

For event 572, ARTIST `SetUpcomingRoadAnimation` (`0x82438598`) posts only when the existing state and animation predicates select `a2 == 1 && a4 == 1`; its inlined record is `{4,572,12,9}` on channel 40, size 16. The matching `OutputGuiEvent<GuiEventRequestTraining>` instantiation at `0x82436840` confirms the same record. The patch keeps those predicates and value unchanged and wraps the existing one-word payload. On this tree the active drain rekeys 572 into `mGuiOutQueue`; `BrnGameModule::DoUpdate_GameStatePostWorld` calls `BridgeGuiToGameState` after the GUI update, and its case 572 translates the word to GameState event 113. `PostWorldUpdate` carries that event to the next pre-world processing pass, where `E_EVENT_GAME_TRAINING_REQUEST` calls `TrainingManager::RequestTraining`. This is a source-path trace, not runtime validation.

The one-file diff matches its pinned preimage byte-for-byte against the base and preserves the existing event-22 wrapper and the original producer conditions/data. The new wrapper layout assertions are consistent with the ARTIST records and the existing `GuiEventWrapper` declaration. No compile, test, CI, or native execution was performed.

The README should be narrowed before publication: event 337’s analyzer endpoint is not reached by the current PC output path, and event 572 maps to **GameState event 113 (`E_EVENT_GAME_TRAINING_REQUEST`)**, not “game action 113.” These documentation corrections do not change the source-wire verdict above.

The previously sealed four-post PASS report and event-121 addendum are separate and were not modified.

See `BINDING.json` for source, pre/post, ARTIST, DecFIGS, and active PC-path hashes.
