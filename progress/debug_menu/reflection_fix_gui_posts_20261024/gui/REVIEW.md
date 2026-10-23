# Fresh source review: GUI channel-40 publisher batch

Date: 2026-10-24
Base: `ea5ce572baedd4ad8918f6d5bfcdfd756250d411` (parent `b9c0e692bc9d8f232b9986923acf07aff26c0639`). This is a read-only source review; no local compile, test, CI, native run, game, or ref/index/source mutation was performed.

## VERDICT: pass

The three-file proposal restores the four ARTIST channel-40 publications without double-wrapping records that already contain their three-word header. The source preimages match the exact base blobs and packet SHA-256 values; the postimage hashes match the packet bindings.

ARTIST confirms each record:

- Event 246, publisher `0x82436CA0`, copies 8 bytes and writes `{8,246,12}` on channel 40, total 20 bytes. Caller `0x82498120` supplies the selected option and player ID. The proposed `GuiEventWrapper<Payload,40>` puts that payload at +12 and retains the inner id.
- Event 264, publisher `0x82436D40`, writes `{8,264,12}` on channel 40, total 20 bytes. Caller `0x824A4670` supplies `{0,-1}` within the existing pause-return branch. The proposed wrapper retains the two payload words and the branch.
- Event 323, publisher `0x824940E8`, copies a 20-byte telemetry payload and writes `{20,323,12}` on channel 40, total 32 bytes. The existing `GuiTelemetryEvent` already carries that header and payload at offsets 0–31; the proposal queues it directly on channel 40, so it does not add a second header.
- Event 266, publisher `0x82493E38`, writes `{4,266,12}` plus the selector on channel 40, total 16 bytes. The existing `GuiNetworkNewsAndTosWire266` already has that complete header. The proposal queues it directly on channel 40 and preserves the ARTIST caller's selector value 6.

The queue route supports the proposed changes and the README's drop claim. `BrnGuiModule::Update` drains the active Screen-flow output after flow updates. Its channel-40 arm unwraps the inner event and forwards it through `mGuiOutQueue`; the switch default explicitly drops other state-output ids (`BrnGuiModule.cpp:3737–3739`). Therefore the current raw 246, 264, 266, and 323 outputs are lost before downstream processing. In the same frame, `BrnGameModule::DoUpdate_NetworkPostSim` appends the GUI output queue to the network post-simulation GUI queue, calls `TranslateGuiEventsToNetworkEvents`, then invokes `ProcessAfterSimulation` (`BrnGameModule_wN1_02.cpp:134–143`). The network manager calls `StateManager::UpdateEvents`, whose GUI-event pump dispatches ids 246, 264, and 266; the GUI-to-network translator's case 323 copies the 20-byte payload into `NetworkInTelemetryEvent`. The new channel-40 records pass the GUI drain and reach those existing consumer paths with the expected payload start and sizes.

The patch changes only the intended producer sites. The existing `CrashNavSettings::OnLeave` event-266 channel-40 record remains unchanged. The scoreboard event-121 capability branch is in its separate `wI_07.cpp` translation unit and is untouched. The added assertions check payload lengths, full record sizes, header/payload offsets, and the telemetry member positions. The CrashNavSettings patch adds a duplicate `<cstddef>` include where one already exists; this is a non-blocking cleanup item.

## EVENT121_ADDENDUM_VERDICT: pass

The addendum correctly changes only the classification of the event-121 site. At the exact base, the C++ call is guarded by `mbEventLeaderboard` and a local `lbEvScoreTargetEnabled = false` placeholder. ARTIST caller `0x824A9B78` checks rights-mask and capability-byte conditions before reaching the event-121 call at `0x824A9D90`; publisher `0x82493F88` writes `{36,121,12}` plus 36 bytes on channel 40. The source constant-false placeholder does not prove an original no-op. `unresolved_gate` / uncertain conditional reachability is the supported disposition; no active-dropped-post count or no-op credit is warranted. The historical matrix remains unchanged.

The paired `bindings.json` records exact proposal, pre/post-image, ARTIST, DecFIGS, current-consumer, and addendum evidence hashes. No runtime or verified-site credit is claimed.
