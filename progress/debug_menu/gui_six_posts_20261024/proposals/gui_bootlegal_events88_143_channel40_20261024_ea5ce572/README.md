# BootLegal sound and controller channel-40 publishers

Base: committed B5 source `ea5ce572baedd4ad8918f6d5bfcdfd756250d411` (parent `b9c0e692bc9d8f232b9986923acf07aff26c0639`). The packet changes two generic publisher call sites in `BrnBootLegal.cpp`, preserves the existing correct `PostCommand16<88>` channel-40 helper site, and includes exact preimage/postimage/diff, ARTIST caller/publisher exports, source consumer excerpts, and hash bindings.

## Event 88: DAC mute

The current `MuteDacEvent` is a full `GuiEvent<200>` header plus a byte, and its generic `OutputGuiEvent` therefore queues key 200 with a 16-byte object. ARTIST `OutputGuiEvent<GuiMuteDac>` at `0x82476BB0` copies one payload byte, writes `{1,88,12}`, and queues a 16-byte record on channel 40; the `BootLegal::Update` caller is `0x82477270` at `0x82477888` and stores zero as the byte. The proposal replaces the wrong local carrier with a payload-only one-byte view whose event id is 88, wraps it in `GuiEventWrapper<...,40>`, and asserts payload size, payload offset and total record size. The current sound logic has case 88, which reads that byte and updates the playback DAC. Its source path is concrete: channel40 is unwrapped into `mGuiOutQueue`, `BridgeGuiToSound` passes that queue to the sound root, and `BrnSoundLogicModule` consumes event88.

## Event 143: saved player-0 controller port

The current `SetPlayer0ControllerPortEvent` is a full `GuiEvent<156>` header plus the port word, so its generic post uses key 156 and a 16-byte object. ARTIST `OutputGuiEvent<GuiEventSetPlayer0ControllerPort>` at `0x82476D88` writes `{4,143,12}` plus the port word on channel40; the actual `BootLegal::Update` caller is `0x82477270` at `0x82477CCC`. The proposal replaces the local view with the exact four-byte payload and queues its channel40 wrapper with layout assertions. The current GUI module has an inbound case143 that sets the user index and refreshes sign-in state. Its input comes from `mpGuiEventInputBuffer`; the source evidence does not establish that this PC build's output-to-input loopback carries this flow post to that case. Treat this as a faithful producer wire repair with the module-loopback effect unresolved; do not claim invite-reboot sign-in behavior is restored.

Counts: two generic producer call sites change. A separate direct `PostCommand16<88>` site already posts a channel40 event88 record and remains outside the changed-site count. No production source, Git ref/index, build, tests, CI, native run, or input state was changed or tested.
