# Channel-40 calls consumed by the GameState bridge

Source-only proposal against exact B5 base `edca934dc502f71f64ad873cdd386afe5e3eeeb2` (parent `ea5ce572baedd4ad8918f6d5bfcdfd756250d411`). It proposes changes at two source-present `StateInterface::OutputGuiEvent` callsites only. No physical production file was edited, and the generic `StateInterface::OutputGuiEvent` template remains unchanged. No local compile, test, CI, native run, or game input was performed.

ARTIST proves that both original template instantiations construct a channel-40 `GuiEventWrapper`: event 326 is a 20-byte `{8,326,12}+8` record, and event 172 is a 136-byte `{120,172,16}+120` record. Current raw-key generic posts are discarded by `DrainFlowOutputQueue` before they can reach the existing `BridgeGuiToGameState` cases. The proposed callers emit those exact wrapper records, after which the existing channel-40 decoder exposes payload/type to the existing translator.

`event326` is translated by `BridgeGuiToGameState` case 326 to `E_EVENT_GUI_SWITCHES_ROAD_RULE_STATE` (GameState event 103, `BrnGameEvents.h:267`). `event172` copies its 120-byte `BrnProgression::Race` payload to `E_EVENT_ADD_CUSTOM_RACE` (GameState event 90, `BrnGameEvents.h:326`). The PC call site consumes `mGuiOutQueue` from `DoUpdate_GameStatePostWorld`; it runs only when the full GameState cascade is scheduled. This source proposal does not claim runtime reachability for every branch or mode.

See `evidence/producer_sink.md`, `bindings.json`, `source/batch.patch`, and the immutable per-file pre/post images.
